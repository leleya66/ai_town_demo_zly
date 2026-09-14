"""验证真实SSE契约、草稿解析、最终提交幂等、Qwen非思考参数和合并承诺的一次模型调用。"""
import json
import unittest
from unittest.mock import patch
from backend.streaming import reply_prefix, emit
from backend.test_agent_loop import answer
from backend.agent_decisions import Selection
from backend.test_intentions import demand_world
from backend.simulation import advance_world
from backend.world import npc_by_id
from backend.perception import options


class StreamingTests(unittest.TestCase):
    def test_pending_memory_survives_context_compaction(self):
        from backend.perception import memories
        n={'agenda':[{'memory_id':'old'}], 'dialogue_memories':[{'id':'old','turn':0}],
           'action_memories':[{'id':str(i),'turn':i} for i in range(1,15)]}
        selected=memories(n,15)
        self.assertEqual(len(selected),6)
        self.assertEqual(selected[0]['id'],'old')

    def test_reply_prefix_never_exposes_json_or_reasoning(self):
        self.assertEqual(reply_prefix('{"thought":"secret"}'),'')
        self.assertEqual(reply_prefix('{"reply":"你好'), '你好')
        self.assertEqual(reply_prefix('{"reply":"你好\\u4'), '你好')
        self.assertEqual(reply_prefix('{"reply":"你好\\ud83d'), '你好')
        self.assertEqual(reply_prefix('{"reply":"你好\\ud83d\\ude00"}'), '你好😀')
        self.assertEqual(reply_prefix('{"reply":"你好\\n世界","mood_delta":8}'),'你好\n世界')

    def test_sse_draft_result_replay_and_stale(self):
        from backend.test_api import SuggestionTests
        from backend.service import worlds
        h=SuggestionTests();h.setUp();self.addCleanup(h.doCleanups)
        worlds[h.world['world_id']]['world']['ai_enabled']=True
        def model(*args):
            emit('draft',text='我愿意准备分享。')
            return answer()
        body=dict(type='message',npc_id='wise',text='准备分享',request_id='stream-once',expected_revision=0)
        def events(response):
            return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        with patch('backend.dialogue.settings',return_value=dict(DASHSCOPE_API_KEY='x',LLM_ENABLED='true')),patch('backend.dialogue.request_json',side_effect=model) as call:
            response=h.client.post(h.url+'/commands/stream',json=body)
            self.assertIn('text/event-stream',response.headers['content-type'])
            first=events(response)
            self.assertEqual([e['type'] for e in first],['progress','draft','result'])
            second=events(h.client.post(h.url+'/commands/stream',json=body))
            self.assertEqual(first[-1],second[-1]);self.assertEqual(call.call_count,1)
            stale=events(h.client.post(h.url+'/commands/stream',json={**body,'request_id':'stale'}))
            self.assertEqual(stale[-1]['status'],409)

    def test_bench_accept_decline_defer_share_turn_call(self):
        for choice in ('accept','decline','defer'):
            w=demand_world();w['ai_enabled']=True
            def model(config,prompt,data,schema):
                candidates=data['options']
                activity='repair_bench' if data['resident']['id']=='stead' and choice=='accept' else 'rest'
                option=next(o for o in candidates if o['activity']==activity)
                return Selection(option_id=option['id'],reason='依据真实需求和状态安排',thought='认真考虑',memory_ids=[],bench_choice=choice if 'bench_need' in data else None)
            with patch('backend.agent_decisions.settings',return_value=dict(DASHSCOPE_API_KEY='x',LLM_ENABLED='true',LLM_MODEL='qwen3.8-flash')),patch('backend.agent_decisions.request_json',side_effect=model) as call,patch('backend.commitments.request_choice') as serial:
                advance_world(w)
                self.assertEqual(call.call_count,4);serial.assert_not_called()
            intent=npc_by_id(w,'stead')['bench_intention']
            self.assertEqual(intent['commitment_decision']['choice'],choice)
            self.assertEqual(w['bench_event']['progress'],1 if choice=='accept' else 0)
            self.assertEqual(intent.get('awaiting_ai',False),choice=='defer')
