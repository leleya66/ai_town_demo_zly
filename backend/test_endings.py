"""验证六回合边界、真实结局、数值取舍、重复事件过滤以及旧存档兼容。"""
import unittest
from copy import deepcopy
from unittest.mock import patch
from backend import test_api, storage
from backend.service import worlds
from backend.world import npc_by_id
from backend.endings import finish_if_due


class EndingTests(unittest.TestCase):
    setUp = test_api.SuggestionTests.setUp
    post = test_api.SuggestionTests.post
    suggest = test_api.SuggestionTests.suggest
    npc = test_api.SuggestionTests.npc

    def finish(self):
        for _ in range(6-self.world['turn']):
            self.assertEqual(self.post('/turns').status_code, 200)

    def test_six_turn_boundary_freezes_world_and_rejects_mutations(self):
        for _ in range(5):
            self.post('/turns')
            self.assertEqual(self.world['phase'], 'playing')
        body = dict(request_id='final-turn', expected_revision=self.world['revision'])
        first = self.client.post(self.url+'/turns', json=body)
        self.assertEqual(first.status_code, 200)
        self.world = first.json()['world']
        self.assertEqual(self.client.post(self.url+'/turns', json=body).json(), first.json())
        self.assertEqual(self.world['turn'], 6)
        self.assertEqual(self.world['phase'], 'ended')
        self.assertEqual(len(self.world['ending']['residents']), 4)
        before = deepcopy(self.world)
        self.assertEqual(self.post('/turns').status_code, 409)
        self.assertEqual(self.suggest().status_code, 409)
        for kind in ('message', 'observe', 'interact'):
            self.assertEqual(self.post('/commands', type=kind, npc_id='wise', place_id='forest', text='你好').status_code, 409)
        self.assertEqual(self.client.get(self.url).json(), before)

    def test_final_turn_event_is_included_in_ending(self):
        for _ in range(4):
            self.post('/turns')
        self.post('/commands', type='observe', place_id='forest')
        self.suggest('stead', 'repair_bench', 'forest')
        self.finish()
        self.assertTrue(self.world['ending']['bench_repaired'])
        self.assertEqual(self.world['bench_event']['completed_turn'], 6)
        self.assertIn('亲手修好', next(n['text'] for n in self.world['ending']['residents'] if n['npc_id']=='stead'))

    def test_save_restart_failure_keeps_ending_then_retry_succeeds_once(self):
        self.finish()
        before = deepcopy(self.world)
        body = dict(type='save_restart', request_id='end-save', expected_revision=before['revision'])
        with patch('backend.storage.save', side_effect=storage.SaveLimitReached):
            self.assertEqual(self.client.post(self.url+'/commands', json=body).status_code, 409)
        self.assertEqual(self.client.get(self.url).json(), before)
        with patch('backend.storage.save', side_effect=OSError('disk full')):
            self.assertEqual(self.client.post(self.url+'/commands', json=body).status_code, 503)
        self.assertEqual(self.client.get(self.url).json(), before)
        first = self.client.post(self.url+'/commands', json=body)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.client.post(self.url+'/commands', json=body).json(), first.json())
        self.world = first.json()['world']
        self.assertEqual(self.world['turn'], 0)
        self.assertIsNone(self.world['ending'])
        self.assertEqual(len(storage.listing()), 1)
        self.post('/commands', type='load', save_id=storage.listing()[0]['id'])
        self.assertEqual(self.world['ending'], before['ending'])
        self.assertEqual(self.world['phase'], 'ended')
        self.assertEqual(self.post('/turns').status_code, 409)

    def test_old_unlimited_save_keeps_turn_metrics_and_old_rules(self):
        legacy = deepcopy(self.world)
        for key in ('rules_version', 'max_turns', 'phase', 'ending'):
            legacy.pop(key)
        legacy['turn'] = 10
        storage.save(legacy)
        worlds.pop(self.world['world_id'])
        self.world = self.client.get(self.url).json()
        self.assertEqual(self.world['turn'], 10)
        self.assertIsNone(self.world['max_turns'])
        self.assertEqual(self.world['rules_version'], 1)
        self.assertEqual(self.npc()['energy'], npc_by_id(legacy, 'wise')['energy'])
        self.post('/turns')
        self.assertEqual(self.world['turn'], 11)
        self.assertEqual(self.npc()['energy'], npc_by_id(legacy, 'wise')['energy']+4)
        self.post('/commands', type='reset')
        self.assertEqual((self.world['turn'], self.world['max_turns'], self.world['rules_version']), (0,6,2))

    def test_repeated_activity_keeps_results_but_does_not_flood_events(self):
        self.post('/turns')
        before = [e for e in self.world['events'] if e['npc']=='stead']
        self.post('/turns')
        self.assertEqual([e for e in self.world['events'] if e['npc']=='stead'], before)
        self.assertEqual(len(self.world['last_results']), 4)
        self.assertIsNone(next(r for r in self.world['last_results'] if r['npc_id']=='stead')['event_id'])
        self.assertTrue(any('第 2 回合' in m for m in self.npc('stead')['memory']))
        self.suggest('stead', 'read', 'library')
        self.post('/turns')
        self.assertTrue(any(e['turn']==3 and 'Stead 在图书馆阅读' in e['text'] for e in self.world['events']))

    def test_repetition_costs_and_one_time_completion_reward(self):
        self.post('/commands', type='observe', place_id='forest')
        self.suggest('stead', 'repair_bench', 'forest')
        self.post('/turns')
        first = next(r for r in self.world['last_results'] if r['npc_id']=='stead')
        self.assertEqual(first['effects']['mood'], 1)
        self.post('/turns')
        second = next(r for r in self.world['last_results'] if r['npc_id']=='stead')
        self.assertEqual(second['effects']['mood'], 5)  # 连续第二次1-2，加完成奖励6。
        self.assertTrue(any('一次性' in note for note in second['notes']))
        self.assertEqual(self.npc()['energy'], 62-6+12)
        self.assertEqual(self.npc()['social'], 28+4+5)
        self.post('/turns')
        self.assertFalse(any('一次性' in note for r in self.world['last_results'] for note in r['notes']))

    def test_ending_does_not_hide_individual_fatigue_with_averages(self):
        state = deepcopy(self.world)
        state['turn'] = 6
        for n in state['npcs']:
            n.update(energy=100, mood=100)
        state['npcs'][0]['energy'] = 20
        finish_if_due(state)
        self.assertEqual(state['ending']['title'], '有人需要歇歇')
        self.assertIn('Joe', state['ending']['reason'])

    def test_autonomous_social_life_and_building_are_recorded(self):
        titles = []
        for style in ('passive', 'care', 'build', 'social'):
            self.post('/commands', type='reset')
            if style == 'build':
                self.post('/commands', type='observe', place_id='forest')
                self.suggest('stead', 'repair_bench', 'forest')
            if style == 'social':
                self.suggest('stead', 'chat', 'plaza')
                self.suggest('joe', 'chat', 'plaza')
            for turn in range(6):
                if style != 'passive' and turn == 4:
                    self.suggest('wise', 'rest', 'forest')
                if style != 'passive' and turn == 5:
                    self.suggest('stead', 'rest', 'forest')
                self.post('/turns')
            titles.append(self.world['ending']['title'])
        self.assertEqual(titles, ['烟火共生', '烟火共生', '守望相助', '烟火共生'])
