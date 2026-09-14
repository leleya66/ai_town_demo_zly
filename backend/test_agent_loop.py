"""验证语义对话、属性边界、待办撤回、AI候选、真实分享积分和对照分支的完整链路。"""
import unittest
from copy import deepcopy
from unittest.mock import patch
from backend.world import fresh_world,npc_by_id
from backend.service import enrich
from backend.dialogue import Dialogue,apply_dialogue
from backend.agent_decisions import select,Selection
from backend.perception import options
from backend.agenda import make_item
from backend.simulation import advance_world
from backend.festival import settle


def answer(**changes):
    values = dict(intent='request',accepted=True,reply='我愿意准备分享。',thought='受到邀请很高兴。',
                  activity='prepare_talk',place='library',cancel_id=None,mood_delta=3,social_delta=2,memory_ids=[])
    return Dialogue(**{**values,**changes})


class AgentLoopTests(unittest.TestCase):
    def world(self):
        w = fresh_world('test-loop', festival_version=1); enrich(w); return w

    def test_dialogue_changes_mood_but_execution_waits(self):
        w=self.world(); n=npc_by_id(w,'wise'); before=deepcopy(n)
        apply_dialogue(w,n,'不用休息，请准备分享',answer())
        self.assertEqual(n['mood'],before['mood']+3)
        self.assertEqual(n['energy'],before['energy'])
        self.assertFalse(w['festival']['prepared_by'])
        self.assertEqual(n['agenda'][0]['activity'],'prepare_talk')
        self.assertEqual(w['interventions_remaining'],1)
        self.assertEqual(n['dialogue_memories'][0]['result'],n['last_dialogue']['effect_summary'])
        advance_world(w)
        self.assertIn('wise',w['festival']['prepared_by'])
        self.assertFalse(n['agenda'])
        self.assertEqual(n['action_memories'][0]['activity'],'prepare_talk')

    def test_cancel_only_target_and_capacity_guard(self):
        w=self.world(); n=npc_by_id(w,'stead')
        n['agenda']=[make_item('read','library',0),make_item('rest','forest',0),make_item('work','workshop',0)]
        apply_dialogue(w,n,'准备分享',answer())
        self.assertEqual(len(n['agenda']),3)
        self.assertTrue(n['last_dialogue']['validation'])
        self.assertEqual(n['last_dialogue']['thought'],'')
        remove=n['agenda'][0]['id']; retain=n['agenda'][1]['id']
        apply_dialogue(w,n,'撤回阅读',answer(intent='cancel',activity=None,place=None,cancel_id=remove))
        self.assertEqual(len(n['agenda']),2)
        self.assertIn(retain,[t['id'] for t in n['agenda']])

    def test_no_energy_or_large_numeric_changes_from_chat(self):
        for delta in (-9,9):
            with self.assertRaises(ValueError): answer(mood_delta=delta)
        w=self.world(); n=npc_by_id(w,'wise'); n['mood']=99
        apply_dialogue(w,n,'谢谢',answer(intent='emotion',activity=None,place=None,mood_delta=8))
        self.assertEqual(n['mood'],100)
        self.assertEqual(n['last_dialogue']['effects']['mood'],1)
        self.assertEqual(n['last_dialogue']['effects']['energy'],0)

    def test_ai_selects_real_option_and_invalid_reference_falls_back(self):
        w=self.world(); w['ai_enabled']=True; n=npc_by_id(w,'wise')
        opt=next(c for c in options(w,n) if c['activity']=='prepare_talk')
        config=dict(DASHSCOPE_API_KEY='test',LLM_ENABLED='true')
        with patch('backend.agent_decisions.settings',return_value=config):
            with patch('backend.agent_decisions.request_json',return_value=Selection(option_id=opt['id'],reason='准备开放日分享',thought='愿意分享知识',memory_ids=[])):
                d=select(w,n); self.assertEqual(d['source'],'ai'); self.assertEqual(d['activity'],'prepare_talk')
            with patch('backend.agent_decisions.request_json',return_value=Selection(option_id=opt['id'],reason='x',thought='x',memory_ids=['fake'])):
                d=select(w,n); self.assertEqual(d['source'],'rules'); self.assertTrue(d['fallback_reason'])
        n['energy']=10
        self.assertTrue(all(c['activity']=='rest' for c in options(w,n)))

    def test_sharing_requires_preparation_and_actual_listener(self):
        w=self.world(); wise=npc_by_id(w,'wise'); joe=npc_by_id(w,'joe')
        wise['agenda']=[make_item('prepare_talk','library',0)]
        advance_world(w)
        wise['agenda']=[make_item('host_talk','library',1)]
        advance_world(w)
        self.assertFalse(w['festival']['talk_completed'])
        self.assertTrue(wise['agenda'])
        joe['agenda']=[make_item('attend_talk','library',2)]
        before=deepcopy(w); advance_world(w)
        self.assertTrue(w['festival']['talk_completed'])
        entries=[e for e in w['festival']['ledger'] if e['kind']=='talk']
        self.assertEqual(sum(e['points'] for e in entries if e['npc_id']=='wise'),4)
        ledger=deepcopy(w['festival']['ledger']); settle(w,before,w['last_decisions'])
        self.assertEqual(w['festival']['ledger'],ledger)

    def test_api_dialogue_idempotency_quota_restore_and_fork(self):
        from backend.test_api import SuggestionTests
        from backend.service import worlds
        h=SuggestionTests(); h.setUp(); self.addCleanup(h.doCleanups)
        worlds[h.world['world_id']]['world']['ai_enabled']=True
        config=dict(DASHSCOPE_API_KEY='test',LLM_ENABLED='true')
        body=dict(type='message',npc_id='wise',text='不用休息，请准备分享',request_id='once',expected_revision=0)
        with patch('backend.dialogue.settings',return_value=config),patch('backend.dialogue.request_json',return_value=answer()) as call:
            response=h.client.post(h.url+'/commands',json=body)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json(),h.client.post(h.url+'/commands',json=body).json())
            self.assertEqual(call.call_count,1)
            h.world=response.json()['world']
            self.assertEqual(h.client.post(h.url+'/commands',json={**body,'request_id':'old'}).status_code,409)
            self.assertEqual(call.call_count,1)
            h.post('/commands',type='message',npc_id='wise',text='谢谢')
            self.assertEqual(h.post('/commands',type='message',npc_id='wise',text='再说一句').status_code,409)
        fork=h.post('/comparisons').json()['result']['comparison']
        a=worlds[fork['ai']]['world']; b=worlds[fork['mock']]['world']
        for key in ('npcs','turn','festival','bench_event'):
            self.assertEqual(a[key],b[key])
        self.assertTrue(a['ai_enabled']); self.assertFalse(b['ai_enabled'])
        self.assertEqual(h.post('/commands',type='save').status_code,200)
        remembered=deepcopy(h.world['npcs'])
        h.post('/commands',type='reset'); h.post('/commands',type='load')
        self.assertEqual(h.world['npcs'],remembered)

    def test_dialogue_timeout_uses_rules_once(self):
        from backend.commands import execute_command
        from backend.models import LegacyCommand
        w=self.world(); w['ai_enabled']=True
        with (patch('backend.dialogue.settings',return_value=dict(DASHSCOPE_API_KEY='test',LLM_ENABLED='true')),
              patch('backend.dialogue.request_json',side_effect=TimeoutError)):
            result=execute_command(w,LegacyCommand(type='message',npc_id='wise',text='你好',request_id='x',expected_revision=0))
        self.assertEqual(result['dialogue']['source'],'rules')
        self.assertTrue(result['dialogue']['fallback_reason'])
        self.assertEqual(w['interventions_remaining'],1)
