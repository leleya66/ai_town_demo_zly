"""隔离模型网络，验证承诺选择、引用校验、降级和既有执行链路的幂等及版本保护。"""
import unittest
from unittest.mock import patch
import httpx
from backend.commitments import Commitment, choose_commitment, request_choice
from backend.test_intentions import demand_world as rule_demand_world
from backend.intentions import update_intentions
from backend.world import npc_by_id
from backend.simulation import advance_world

CONFIG = dict(DASHSCOPE_API_KEY='test-only', LLM_ENABLED='true', LLM_MODEL='qwen3.8-flash',
              LLM_BASE_URL='https://example.invalid/v1')


def demand_world():
    world = rule_demand_world()
    world['ai_enabled'] = True
    return world


@patch('backend.commitments.settings', return_value=CONFIG)
class CommitmentTests(unittest.TestCase):
    def decision(self, world, choice='accept'):
        n = npc_by_id(world, 'stead')
        return Commitment(choice=choice, reason='根据收到的长椅需求与现有安排作出判断。',
                          memory_ids=[n['social_memories'][0]['id']])

    def test_ai_choice_drives_existing_chain_once(self, config):
        for choice in ('accept', 'decline'):
            w = demand_world(); n = npc_by_id(w, 'stead')
            with patch('backend.commitments.request_choice', return_value=self.decision(w, choice)) as call:
                update_intentions(w); update_intentions(w)
                self.assertEqual(call.call_count, 1)
                self.assertEqual(n['bench_intention']['commitment_decision']['source'], 'ai')
                self.assertEqual(len(n['agenda']), int(choice == 'accept'))
                self.assertEqual(w['bench_event']['progress'], 0)
                advance_world(w)
                self.assertEqual(w['bench_event']['progress'], int(choice == 'accept'))
                sent = call.call_args.args[1]
                self.assertEqual(sent['demand_memory_id'], n['social_memories'][0]['id'])
                self.assertIn('agenda', sent['resident'])

    def test_no_memory_or_completed_need_never_calls(self, config):
        for completed in (False, True):
            w = demand_world()
            if completed:
                w['bench_event'].update(status='repaired', progress=2)
            else:
                npc_by_id(w, 'stead')['social_memories'] = []
            with patch('backend.commitments.request_choice') as call:
                update_intentions(w)
                call.assert_not_called()

    def test_invalid_reference_timeout_and_http_fall_back(self, config):
        w = demand_world(); n = npc_by_id(w, 'stead'); memory = n['social_memories'][0]
        invalid = Commitment(choice='accept', reason='引用错误', memory_ids=['invented'])
        with patch('backend.commitments.request_choice', return_value=invalid):
            self.assertEqual(choose_commitment(w,n,memory)['source'], 'rules')
        for error in (httpx.ReadTimeout('test'), ValueError('bad JSON'),
                      httpx.HTTPStatusError('test', request=httpx.Request('POST','https://example.invalid'),
                                            response=httpx.Response(401))):
            with patch('backend.commitments.request_choice', side_effect=error):
                answer = choose_commitment(w,n,memory)
                self.assertEqual(answer['source'], 'rules')
                self.assertTrue(answer['fallback_reason'])

    def test_retry_stale_revision_and_restore_retain_ai_choice(self, config):
        from backend.test_api import SuggestionTests
        from backend.service import worlds
        helper = SuggestionTests(); helper.setUp(); self.addCleanup(helper.doCleanups)
        w = demand_world(); w['world_id'] = helper.world['world_id']
        worlds[w['world_id']]['world'] = w
        from backend.agent_decisions import Selection
        def choose(config,prompt,data,schema):
            option=next(o for o in data['options'] if o['activity']=='rest')
            return Selection(option_id=option['id'],reason='先照顾精力，再兑现长椅承诺',thought='愿意帮助',memory_ids=[],bench_choice='accept' if 'bench_need' in data else None)
        with patch('backend.agent_decisions.settings',return_value=CONFIG),patch('backend.agent_decisions.request_json',side_effect=choose) as call:
            body = dict(request_id='ai-once', expected_revision=0)
            first = helper.client.post(helper.url+'/turns', json=body)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json(), helper.client.post(helper.url+'/turns', json=body).json())
            self.assertEqual(helper.client.post(helper.url+'/turns', json={**body,'request_id':'stale'}).status_code,409)
            self.assertEqual(call.call_count,4)
            helper.world = first.json()['world']
            saved = npc_by_id(helper.world,'stead')['bench_intention']['commitment_decision']
            helper.post('/commands',type='save'); helper.post('/commands',type='reset'); helper.post('/commands',type='load')
            self.assertEqual(npc_by_id(helper.world,'stead')['bench_intention']['commitment_decision'],saved)

    def test_stream_final_content_and_strict_schema(self, config):
        import json
        content = json.dumps(dict(choice='accept', reason='需求已收到',memory_ids=['m']))
        response = httpx.Response(200, text='data: '+json.dumps({'choices':[{'delta':{'content':content}}]})+'\n\ndata: [DONE]\n')
        def handle(request):
            body=json.loads(request.content)
            self.assertEqual(body['model'],'qwen3.8-flash')
            self.assertIs(body['enable_thinking'],False)
            self.assertEqual(body['max_tokens'],800)
            return response
        transport = httpx.MockTransport(handle)
        client = httpx.Client(transport=transport)
        with patch('backend.commitments.httpx.Client', return_value=client):
            self.assertEqual(request_choice(CONFIG,{}).choice,'accept')
        with self.assertRaises(ValueError):
            Commitment.model_validate(dict(choice='accept',reason='x',memory_ids=['m'],energy=100))
