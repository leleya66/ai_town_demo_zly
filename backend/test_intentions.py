"""对照同一快照的有无需求记忆，验证选择差异、延期恢复、失效及真实交流来源。"""
import unittest
from copy import deepcopy
from backend.world import fresh_world, npc_by_id
from backend.intentions import update_intentions
from backend.conversations import converse
from backend.decisions import decide
from backend.simulation import advance_world
from backend.service import enrich
from backend.agenda import make_item


def demand_world():
    w=fresh_world('comparison', festival_version=1); w['bench_event']['discovered']=True
    npc_by_id(w,'calm')['bench_knowledge']=dict(turn=0,source='共同观察林间长椅')
    converse(w,deepcopy(w),'calm','stead','forest')
    return w


class IntentionTests(unittest.TestCase):
    def test_same_snapshot_memory_changes_action_and_destination(self):
        yes=demand_world(); no=deepcopy(yes)
        npc_by_id(no,'stead')['social_memories']=[]
        update_intentions(yes); update_intentions(no)
        self.assertEqual(decide(yes,npc_by_id(yes,'stead'))['activity'],'repair_bench')
        self.assertEqual(decide(yes,npc_by_id(yes,'stead'))['target_place_id'],'forest')
        self.assertEqual(decide(no,npc_by_id(no,'stead'))['activity'],'work')
        self.assertEqual(decide(no,npc_by_id(no,'stead'))['target_place_id'],'workshop')
        self.assertEqual(yes['bench_event']['progress'],0)

    def test_low_energy_same_now_different_after_recovery(self):
        yes=demand_world(); npc_by_id(yes,'stead')['energy']=20
        no=deepcopy(yes); npc_by_id(no,'stead')['social_memories']=[]
        for w in (yes,no):
            update_intentions(w)
            self.assertEqual(decide(w,npc_by_id(w,'stead'))['activity'],'rest')
            advance_world(w); enrich(w)
        self.assertEqual(npc_by_id(yes,'stead')['bench_intention']['status'],'deferred')
        self.assertEqual(decide(yes,npc_by_id(yes,'stead'))['activity'],'repair_bench')
        self.assertNotEqual(decide(no,npc_by_id(no,'stead'))['activity'],'repair_bench')
        advance_world(yes); enrich(yes)
        self.assertEqual(yes['bench_event']['progress'],1)
        advance_world(yes); enrich(yes)
        advance_world(yes); enrich(yes)  # 第一次劳动后再次疲惫，先恢复再继续。
        self.assertEqual(npc_by_id(yes,'stead')['bench_intention']['status'],'completed')

    def test_completed_event_invalidates_memory_intention(self):
        yes=demand_world(); yes['bench_event'].update(status='repaired',progress=2)
        no=deepcopy(yes); npc_by_id(no,'stead')['social_memories']=[]
        for w in (yes,no):
            update_intentions(w)
            self.assertNotEqual(decide(w,npc_by_id(w,'stead'))['activity'],'repair_bench')
            self.assertFalse(npc_by_id(w,'stead')['agenda'])
        self.assertEqual(npc_by_id(yes,'stead')['bench_intention']['status'],'invalid')

    def test_no_knowledge_no_demand_and_refusal_no_task(self):
        w=fresh_world('unknown', festival_version=1); w['bench_event']['discovered']=True
        converse(w,deepcopy(w),'calm','stead','forest'); update_intentions(w)
        self.assertNotIn('bench_intention',npc_by_id(w,'stead'))
        w=demand_world(); npc_by_id(w,'stead')['mood']=42
        update_intentions(w)
        self.assertEqual(npc_by_id(w,'stead')['bench_intention']['status'],'declined')
        self.assertFalse(npc_by_id(w,'stead')['agenda'])

    def test_capacity_and_existing_task_not_overwritten(self):
        w=demand_world(); n=npc_by_id(w,'stead')
        n['agenda']=[make_item('read','library',0),make_item('rest','forest',0),make_item('work','workshop',0)]
        update_intentions(w); self.assertEqual(len(n['agenda']),3)
        self.assertEqual(n['bench_intention']['status'],'deferred')
        n['agenda'].pop(); update_intentions(w)
        task=next(t for t in n['agenda'] if t['activity']=='repair_bench')
        update_intentions(w); self.assertEqual(len(n['agenda']),3)
        self.assertEqual(n['bench_intention']['agenda_item_id'],task['id'])

class IntentionPersistenceTests(unittest.TestCase):
    def test_repeat_request_save_restore_and_existing_commitment(self):
        from backend import test_api
        helper=test_api.SuggestionTests(); helper.setUp(); self.addCleanup(helper.doCleanups)
        # 测试夹具只写独立测试世界；不向生产接口开放状态注入。
        w=demand_world(); w['world_id']=helper.world['world_id']
        task=make_item('repair_bench','forest',0,source_id='player-commitment')
        npc_by_id(w,'stead')['agenda']=[task]
        test_api.worlds[w['world_id']]['world']=w
        body=dict(request_id='intention-once',expected_revision=0)
        first=helper.client.post(helper.url+'/turns',json=body).json()
        self.assertEqual(first,helper.client.post(helper.url+'/turns',json=body).json())
        helper.world=first['world']; intent=npc_by_id(helper.world,'stead')['bench_intention']
        self.assertEqual(intent['agenda_item_id'],task['id'])
        self.assertEqual(npc_by_id(helper.world,'stead')['agenda'][0]['source_action_id'],'player-commitment')
        helper.post('/commands',type='save'); helper.post('/commands',type='reset')
        self.assertNotIn('bench_intention',npc_by_id(helper.world,'stead'))
        helper.post('/commands',type='load')
        self.assertEqual(npc_by_id(helper.world,'stead')['bench_intention'],intent)
