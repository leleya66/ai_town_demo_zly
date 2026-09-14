"""新版四条路线独立验收：邀请回应、真实配对、去重封顶、取消、期限、角色边界与存档隔离。"""
import unittest
from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.world import fresh_world,npc_by_id
from backend.service import enrich
from backend.simulation import advance_world
from backend import invitations,festival
from backend.event_rules import EVENTS
from backend.models import NpcDecision
from backend.main import app
from backend.dialogue import apply_dialogue
from backend.test_agent_loop import answer


class EventRouteTests(unittest.TestCase):
    def world(self):
        w=fresh_world('routes');enrich(w);return w

    def plan(self,npc,activity,place,invitation_id=None):
        return {**NpcDecision(npc_id=npc,activity=activity,target_place_id=place,reason='测试真实活动').model_dump(),'invitation_id':invitation_id}

    def invite(self,w,owner,target=None):
        invitations.issue(w,dict(npc_id=owner,target_npc_id=target))
        return w['invitations'][-1]

    def execute_pair(self,w,i):
        a,b=invitations.actions(i['event'])
        ds=[self.plan(n['id'],'rest',n['place']) for n in w['npcs']]
        for d in ds:
            if d['npc_id']==i['sender']:d.update(activity=a,target_place_id=i['place'],invitation_id=next(x['id'] for x in w['invitations'] if x['group']==i['group']))
            if d['npc_id']==i['recipient']:d.update(activity=b,target_place_id=i['place'],invitation_id=i['id'])
        before=deepcopy(w);completed=invitations.resolve(w,ds)
        w['turn']+=1;invitations.finish(w,ds,completed);festival.settle(w,before,ds,completed)
        return completed

    def test_new_world_has_four_routes_and_old_save_is_unchanged(self):
        w=self.world();self.assertEqual(len(w['festival']['cards']),4)
        old=fresh_world('old',festival_version=1);old.pop('festival_version');enrich(old)
        self.assertNotIn('cards',old['festival'])
        festival.credit(old,'wise','talk','old',4,'旧计分');enrich(old)
        self.assertEqual(old['festival']['ledger'][0]['points'],4)

    def test_only_wise_prepares_and_only_stead_repairs(self):
        from backend.eligibility import blocked
        w=self.world()
        for who in ('joe','calm','stead'):
            self.assertTrue(blocked(w,npc_by_id(w,who),'prepare_talk','library')[0])
        self.assertIsNone(blocked(w,npc_by_id(w,'wise'),'prepare_talk','library'))

    def test_broadcast_does_not_force_acceptance_or_score(self):
        w=self.world();w['festival']['prepared_by']=['wise'];self.invite(w,'wise')
        self.assertEqual(len(w['invitations']),3)
        self.assertTrue(all(i['status']=='pending' for i in w['invitations']))
        self.assertEqual(w['festival']['ledger'],[])
        self.assertTrue(all(not npc_by_id(w,i['recipient'])['agenda'] for i in w['invitations']))
        self.invite(w,'wise');self.assertEqual(len(w['invitations']),3)

    def test_all_four_routes_score_actual_results_only_and_cap(self):
        for event,spec in EVENTS.items():
            w=self.world();w['festival']['prepared_by']=['wise'];w['bench_event'].update(status='repaired',progress=2)
            i=self.invite(w,spec['owner'],next(n['id'] for n in w['npcs'] if n['id']!=spec['owner']))
            completed=self.execute_pair(w,i);self.assertEqual(len(completed),1)
            entry=w['festival']['ledger'][0];self.assertEqual((entry['npc_id'],entry['points']),(spec['owner'],2))
            festival.settle(w,deepcopy(w),[],completed);self.assertEqual(len(w['festival']['ledger']),1)
            for j in range(10):festival.credit(w,spec['owner'],event,'extra'+str(j),2,'封顶验证')
            festival.refresh(w);self.assertEqual(w['festival']['ranking'][0]['score'],6)

    def test_decline_defer_absence_and_expiration_never_score(self):
        for reply in ('decline','defer','accept'):
            w=self.world();i=self.invite(w,'joe','wise')
            ds=[self.plan(n['id'],'rest',n['place']) for n in w['npcs']]
            ds[1]['invitation_replies']=[dict(invitation_id=i['id'],response=reply,reason='本回合先休息')]
            completed=invitations.resolve(w,ds);self.assertFalse(completed);self.assertFalse(w['festival']['ledger'])
            self.assertEqual(i['status'],{'accept':'accepted','decline':'declined','defer':'deferred'}[reply])
            w['turn']=i['expires_turn'];invitations.expire(w)
            self.assertEqual(i['status'],'declined' if reply=='decline' else 'expired')

    def test_low_energy_cannot_execute_even_accepted_invitation(self):
        w=self.world();i=self.invite(w,'joe','wise');npc_by_id(w,'wise')['energy']=1
        self.assertFalse(self.execute_pair(w,i));self.assertFalse(w['festival']['ledger'])

    def test_cancel_agenda_also_withdraws_invitation(self):
        w=self.world();i=self.invite(w,'joe','wise');npc=npc_by_id(w,'joe');task=npc['agenda'][0]
        apply_dialogue(w,npc,'取消关心邀请',answer(intent='cancel',activity=None,place=None,cancel_id=task['id']))
        self.assertEqual(i['status'],'cancelled');self.assertEqual(npc['agenda'],[])

    def test_mock_prepares_broadcasts_and_hosts_without_player_assigning_guests(self):
        w=self.world()
        for n in w['npcs']:
            if n['id']!='wise':n['energy']=0
        advance_world(w);self.assertIn('wise',w['festival']['prepared_by'])
        advance_world(w);self.assertEqual(len(w['invitations']),3)
        for n in w['npcs']:n['energy']=70
        advance_world(w)
        self.assertTrue(w['festival']['talk_completed'])
        self.assertEqual(w['festival']['ranking'][0]['score'],6)
        self.assertEqual(w['festival']['winners'],['wise'])

    def test_bench_scores_once_on_completion_and_news_requires_finished_bench(self):
        from backend.agenda import make_item
        w=self.world();n=npc_by_id(w,'stead');self.assertFalse(invitations.ready(w,'bench'))
        w['bench_event']['discovered']=True;n['agenda']=[make_item('repair_bench','forest',0)]
        advance_world(w);self.assertFalse(any(e['kind']=='bench' for e in w['festival']['ledger']))
        advance_world(w);self.assertTrue(invitations.ready(w,'bench'))
        self.assertEqual(sum(e['points'] for e in w['festival']['ledger'] if e['npc_id']=='stead'),2)

    def test_new_api_save_load_and_revision_protect_invitations(self):
        with TemporaryDirectory() as folder,patch('backend.storage.DB_PATH',Path(folder)/'saves.sqlite3'),TestClient(app) as client:
            w=client.post('/api/worlds').json();self.assertEqual(len(w['festival']['cards']),4)
            url='/api/worlds/'+w['world_id'];body=dict(request_id='turn',expected_revision=0)
            first=client.post(url+'/turns',json=body).json();self.assertEqual(first,client.post(url+'/turns',json=body).json())
            w=first['world'];self.assertTrue(w['invitations'])
            def command(type):
                nonlocal w
                r=client.post(url+'/commands',json=dict(type=type,request_id=type,expected_revision=w['revision']));self.assertEqual(r.status_code,200);w=r.json()['world']
            saved=deepcopy(w['invitations']);command('save');command('reset');command('load')
            self.assertEqual(w['invitations'],saved)
