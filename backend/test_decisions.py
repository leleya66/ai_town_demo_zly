"""验证具体决策理由与实际状态一致，并覆盖从旧前端迁移来的正式规则行为。"""
import unittest
from backend import test_api
from backend.world import npc_by_id
from backend.service import worlds


class DecisionTests(unittest.TestCase):
    setUp = test_api.SuggestionTests.setUp
    post = test_api.SuggestionTests.post
    suggest = test_api.SuggestionTests.suggest
    npc = test_api.SuggestionTests.npc

    def test_accepted_plan_explains_place_activity_turn_and_energy(self):
        self.suggest('wise', 'read', 'library')
        energy = self.npc()['energy']
        self.post('/turns')
        reason = self.npc()['reason']
        for fact in ('第0回合', '图书馆', '阅读', f'{energy}/100'):
            self.assertIn(fact, reason)
        self.assertEqual(self.npc()['last_decision']['activity'], 'read')

    def test_default_choice_names_real_preference_and_state(self):
        self.post('/turns')
        reason = self.npc('stead')['reason']
        self.assertIn('工坊', reason)
        self.assertIn('修缮', reason)
        self.assertIn('91/100', reason)
        self.assertNotIn('根据当前状态与自己的偏好安排活动', reason)

    def test_fatigue_explains_deferred_advice(self):
        self.suggest('stead', 'read', 'library')
        npc_by_id(worlds[self.world['world_id']]['world'], 'stead')['energy'] = 24
        self.post('/turns')
        resident = self.npc('stead')
        self.assertEqual(resident['last_decision']['activity'], 'rest')
        for fact in ('24/100', '低于30', '保留'):
            self.assertIn(fact, resident['reason'])
        self.assertEqual(resident['agenda'][0]['status'], 'deferred')

    def test_decline_preserves_existing_commitment(self):
        self.post('/commands', type='observe', place_id='forest')
        self.suggest('stead', 'repair_bench', 'forest')
        reply = self.suggest('stead', 'rest', 'forest').json()['result']
        self.assertEqual(reply['outcome'], 'declined')
        self.assertIn('保留', reply['reason'])
        self.assertEqual(self.npc('stead')['agenda'][0]['activity'], 'repair_bench')

    def test_chat_without_partner_names_the_unmet_condition(self):
        for n in worlds[self.world['world_id']]['world']['npcs']:
            if n['id'] != 'joe': n['social'] = 0
        self.post('/turns')
        self.assertEqual(self.npc('joe')['last_decision']['activity'], 'seek_company')
        self.assertIn('没有匹配到', self.npc('joe')['reason'])

    def test_message_and_observation_use_real_backend_state(self):
        before = self.npc('joe')['mood']
        self.post('/commands', type='message', npc_id='wise', text='你好')
        self.assertTrue(self.world['tasks'][0])
        self.assertEqual(self.npc('joe')['mood'], before)
        self.post('/commands', type='observe', place_id='forest')
        self.assertFalse(self.world['tasks'][2])
        self.post('/commands', type='observe', place_id='plaza')
        self.assertTrue(self.world['tasks'][2])

    def test_long_play_clamps_real_backend_metrics_and_history(self):
        # 旧版自由回合继续验证长时间边界，新局终止边界由结局测试覆盖。
        state = worlds[self.world['world_id']]['world']
        state.update(rules_version=1, max_turns=None)
        for _ in range(100):
            self.post('/commands', type='message', npc_id='joe', text='你好')
            self.assertEqual(self.post('/turns').status_code, 200)
        for resident in self.world['npcs']:
            for metric in ('energy', 'mood', 'social'):
                self.assertTrue(0 <= resident[metric] <= 100)
            self.assertLessEqual(len(resident['memory']), 12)
            self.assertLessEqual(len(resident['messages']), 30)
        self.assertLessEqual(len(self.world['events']), 80)
