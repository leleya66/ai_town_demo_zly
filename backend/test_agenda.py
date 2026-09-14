"""验证跨回合待办、硬约束与偏好分离、容量去重，以及旧快照的单次兼容迁移。"""
import unittest
from copy import deepcopy
from backend import test_api, storage
from backend.service import worlds
from backend.world import npc_by_id
from backend.eligibility import blocked
from backend.preferences import preference_refusal


class AgendaTests(unittest.TestCase):
    setUp = test_api.SuggestionTests.setUp
    post = test_api.SuggestionTests.post
    suggest = test_api.SuggestionTests.suggest
    npc = test_api.SuggestionTests.npc

    def discover(self):
        self.post('/commands', type='observe', place_id='forest')

    def test_repair_precedes_chat_and_chat_survives_two_labor_turns(self):
        self.discover()
        self.suggest('stead', 'repair_bench', 'forest')
        self.suggest('stead', 'chat', 'plaza')
        self.assertEqual(len(self.npc('stead')['agenda']), 2)
        self.assertIn('先处理修好林间长椅', self.npc('stead')['messages'][-1]['text'])
        self.post('/turns')
        self.assertEqual(self.npc('stead')['last_decision']['activity'], 'repair_bench')
        result = next(r for r in self.world['last_results'] if r['npc_id'] == 'stead')
        self.assertEqual(result['agenda_item_id'], self.npc('stead')['last_decision']['agenda_item_id'])
        self.assertEqual(self.world['bench_event']['progress'], 1)
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['status'], 'repaired')
        self.assertEqual([t['activity'] for t in self.npc('stead')['agenda']], ['chat'])
        self.suggest('joe', 'chat', 'plaza')
        self.post('/turns')
        self.assertEqual(self.npc('stead')['last_decision']['activity'], 'chat')
        self.assertEqual(self.npc('stead')['agenda'], [])

    def test_unstarted_repair_survives_fatigue_and_completes(self):
        self.discover()
        self.suggest('stead', 'repair_bench', 'forest')
        npc_by_id(worlds[self.world['world_id']]['world'], 'stead')['energy'] = 20
        self.post('/turns')
        self.assertEqual(self.npc('stead')['agenda'][0]['status'], 'deferred')
        self.assertIn('20/100', self.npc('stead')['agenda'][0]['defer_reason'])
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['progress'], 1)
        self.post('/turns')
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['status'], 'repaired')
        self.assertEqual(self.npc('stead')['agenda'], [])

    def test_duplicate_is_free_even_when_budget_exhausted(self):
        self.discover()
        self.suggest('stead', 'repair_bench', 'forest')
        self.suggest('stead', 'chat', 'plaza')
        before = deepcopy(self.npc('stead')['agenda'])
        response = self.suggest('stead', 'repair_bench', 'forest')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['result']['merged'])
        self.assertEqual(self.npc('stead')['agenda'], before)
        self.assertEqual(self.world['interventions_remaining'], 0)

    def test_capacity_preserves_all_three_items(self):
        self.discover()
        self.suggest('stead', 'repair_bench', 'forest')
        self.suggest('stead', 'read', 'library')
        self.post('/turns')
        self.suggest('stead', 'chat', 'plaza')
        before = deepcopy(self.npc('stead')['agenda'])
        reply = self.suggest('stead', 'work', 'workshop').json()['result']
        self.assertEqual(reply['outcome'], 'declined')
        self.assertIn('3项', reply['reason'])
        self.assertEqual(self.npc('stead')['agenda'], before)

    def test_expired_chat_closes_and_never_counts_as_executed(self):
        self.suggest('stead', 'chat', 'plaza')
        npc_by_id(worlds[self.world['world_id']]['world'], 'stead')['energy'] = 0
        for _ in range(4):
            self.post('/turns')
        self.assertEqual(self.npc('stead')['agenda'], [])
        self.assertTrue(any('已过期' in e['text'] for e in self.world['events']))
        self.assertNotEqual(self.npc('stead')['last_decision']['activity'], 'chat')

    def test_pairing_failure_preserves_invitation(self):
        self.suggest('stead', 'chat', 'plaza')
        self.suggest('joe', 'rest', 'forest')
        self.post('/turns')
        self.assertEqual(self.npc('stead')['last_decision']['activity'], 'seek_company')
        self.assertIsNone(self.npc('stead')['last_decision']['agenda_item_id'])
        self.assertEqual(self.npc('stead')['agenda'][0]['activity'], 'chat')
        self.assertIn('未与我的邀请匹配', self.npc('stead')['reason'])

    def test_hard_constraints_are_separate_from_personal_preference(self):
        wise = self.npc()
        self.assertIsNone(blocked(self.world, wise, 'work', 'workshop'))
        self.assertIsNotNone(preference_refusal(wise, 'work'))
        self.assertIsNotNone(blocked(self.world, wise, 'read', 'forest'))
        wise['energy'] = 5
        self.assertIsNotNone(blocked(self.world, wise, 'read', 'library'))

    def test_legacy_pending_and_started_bench_migrate_once(self):
        legacy = deepcopy(self.world)
        legacy['turn'] = 4
        legacy['bench_event'].update(discovered=True, status='repairing', progress=1, assigned_npc_id='stead')
        for npc in legacy['npcs']:
            npc.pop('agenda')
            npc.pop('agenda_preview')
            npc['pending_suggestion'] = None
        npc_by_id(legacy, 'stead')['pending_suggestion'] = dict(activity='read', target_place_id='library', expires_after_turn=5, source_action_id='old', memory_id='old-memory')
        storage.save(legacy)
        worlds.pop(self.world['world_id'])
        restored = self.client.get(self.url).json()
        resident = npc_by_id(restored, 'stead')
        self.assertNotIn('pending_suggestion', resident)
        self.assertEqual(len(resident['agenda']), 2)
        self.assertEqual(resident['agenda_preview']['activity'], 'repair_bench')
        self.assertIn('旧存档记录', resident['agenda_preview']['reason'])
        self.assertEqual(self.client.get(self.url).json(), restored)
        self.assertEqual(storage.read(legacy['world_id']), legacy, '读取迁移不能重写原快照')

    def test_oldest_commitment_wins_over_newer_preference(self):
        self.suggest('stead', 'read', 'library')
        state = worlds[self.world['world_id']]['world']
        npc_by_id(state, 'stead')['energy'] = 20
        self.post('/turns')
        self.suggest('stead', 'work', 'workshop')
        self.post('/turns')
        self.assertEqual(self.npc('stead')['last_decision']['activity'], 'read')
        self.assertEqual(self.npc('stead')['agenda'][0]['activity'], 'work')
