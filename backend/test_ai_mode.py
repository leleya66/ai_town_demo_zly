"""验证真实模式开关、请求去重、配置失败、存档恢复和模式对模型调用的实际控制。"""
import unittest
from copy import deepcopy
from unittest.mock import patch
from backend.test_api import SuggestionTests
from backend.test_commitments import CONFIG
from backend.test_intentions import demand_world
from backend.commitments import Commitment
from backend.intentions import update_intentions
from backend.ai_mode import describe, set_mode
from backend.world import npc_by_id


class AiModeTests(unittest.TestCase):
    def setUp(self):
        self.helper = SuggestionTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        for name in ('backend.ai_mode.settings', 'backend.commitments.settings'):
            patcher = patch(name, return_value=CONFIG)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_mode_api_is_idempotent_and_persisted_without_game_effects(self):
        h = self.helper
        before = deepcopy(h.world)
        self.assertFalse(before['ai']['enabled'])
        body = dict(request_id='toggle', expected_revision=before['revision'], enabled=True)
        first = h.client.post(h.url+'/ai-mode', json=body)
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.json(), h.client.post(h.url+'/ai-mode',json=body).json())
        h.world = first.json()['world']
        self.assertTrue(h.world['ai']['enabled'])
        self.assertEqual(h.world['ai']['status'],'ready')
        self.assertIsNone(h.world['ai']['last_decision'])
        self.assertEqual(h.world['turn'], before['turn'])
        self.assertEqual(h.world['npcs'], before['npcs'])
        self.assertEqual(h.client.post(h.url+'/ai-mode',json={**body,'request_id':'stale','enabled':False}).status_code,409)
        self.assertEqual(h.client.post(h.url+'/ai-mode',json={**body,'enabled':'true'}).status_code,422)
        self.assertEqual(h.post('/commands',type='save').status_code,200)
        self.assertEqual(h.post('/ai-mode',enabled=False).status_code,200)
        self.assertEqual(h.post('/commands',type='load').status_code,200)
        self.assertTrue(h.world['ai']['enabled'])
        self.assertNotIn('test-only',str(h.world['ai']))

    def test_missing_key_rejects_enabling_and_retains_mode(self):
        h = self.helper
        with patch('backend.ai_mode.settings',return_value={**CONFIG,'DASHSCOPE_API_KEY':''}):
            response = h.post('/ai-mode',enabled=True)
            self.assertEqual(response.status_code,409)
            self.assertFalse(h.world['ai']['enabled'])

    def test_switch_controls_call_and_preserves_processed_commitment(self):
        mock_world = demand_world()
        n = npc_by_id(mock_world,'stead')
        with patch('backend.commitments.request_choice') as call:
            update_intentions(mock_world)
            call.assert_not_called()
        self.assertEqual(describe(mock_world)['last_decision']['source'],'rules')
        old = deepcopy(n['bench_intention'])
        set_mode(mock_world,True)
        with patch('backend.commitments.request_choice') as call:
            update_intentions(mock_world)
            call.assert_not_called()
        self.assertEqual(n['bench_intention'],old)
        ai_world = demand_world(); set_mode(ai_world,True)
        memory = npc_by_id(ai_world,'stead')['social_memories'][0]
        answer = Commitment(choice='decline',reason='当前已有安排，暂不承诺。',memory_ids=[memory['id']])
        with patch('backend.commitments.request_choice',return_value=answer) as call:
            update_intentions(ai_world)
            self.assertEqual(call.call_count,1)
        self.assertEqual(describe(ai_world)['last_decision']['source'],'ai')
        self.assertFalse(npc_by_id(ai_world,'stead')['agenda'])

    def test_degraded_result_is_not_reported_as_ai_success(self):
        w = demand_world(); set_mode(w,True)
        with patch('backend.commitments.request_choice',side_effect=TimeoutError):
            update_intentions(w)
        status = describe(w)
        self.assertTrue(status['enabled'])
        self.assertEqual(status['last_decision']['source'],'rules')
        self.assertIn('超时',status['last_decision']['fallback_reason'])
