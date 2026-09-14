"""验证建议请求、回合结算及非法输入，使用独立测试世界和临时存档库。"""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.main import app, worlds


class SuggestionTests(unittest.TestCase):
    def setUp(self):
        # 原规则回归套件固定旧局版本；四条新版事件在test_event_routes中独立验收。
        from backend.world import fresh_world
        for module in ('backend.main','backend.commands'):
            version=patch(module+'.fresh_world',side_effect=lambda world_id:fresh_world(world_id,festival_version=1))
            version.start();self.addCleanup(version.stop)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch("backend.storage.DB_PATH", Path(directory.name) / "saves.sqlite3")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.world = self.client.post('/api/worlds').json()
        self.url = '/api/worlds/' + self.world['world_id']

    def post(self, route, **body):
        response = self.client.post(self.url + route, json=dict(request_id=str(uuid4()), expected_revision=self.world['revision'], **body))
        if response.status_code == 200:
            self.world = response.json()['world']
        return response

    def suggest(self, npc='wise', activity='rest', place='forest'):
        return self.post('/actions', type='suggest_activity', npc_id=npc, activity=activity, target_place_id=place)

    def npc(self, name='wise'):
        return next(n for n in self.world['npcs'] if n['id'] == name)

    def test_accept_then_execute_once(self):
        before = self.npc()['energy']
        response = self.suggest().json()
        self.assertEqual(response['result']['outcome'], 'accepted')
        self.assertEqual(self.npc()['place'], 'library')
        self.assertEqual(self.npc()['energy'], before)
        action_id = self.npc()['agenda'][0]['source_action_id']
        self.post('/turns')
        self.assertEqual(self.npc()['place'], 'forest')
        self.assertEqual(self.npc()['energy'], before + 12)
        self.assertEqual(self.npc()['agenda'], [])
        self.assertEqual(self.npc()['last_decision']['source_action_id'], action_id)
        self.assertTrue(self.npc()['last_decision']['related_memory_ids'])
        self.assertEqual(self.world['interventions_remaining'], 2)
        self.post('/turns')
        self.assertEqual(self.npc()['place'], 'library')

    def test_decline_reason_and_no_pending(self):
        result = self.suggest('wise', 'work', 'workshop').json()['result']
        self.assertEqual(result['outcome'], 'declined')
        self.assertTrue(result['reason'])
        self.assertEqual(self.npc()['agenda'], [])
        self.assertEqual(self.world['interventions_remaining'], 1)

    def test_invalid_and_budget(self):
        self.assertEqual(self.suggest('wise', 'read', 'forest').status_code, 422)
        self.assertEqual(self.world['interventions_remaining'], 2)
        self.suggest()
        self.suggest('wise', 'work', 'workshop')
        self.assertEqual(self.suggest('wise', 'read', 'library').status_code, 409)
        self.assertEqual(self.world['interventions_remaining'], 0)

    def test_idempotency_revision_and_extra_fields(self):
        body = dict(request_id='repeat', expected_revision=0,type='suggest_activity',npc_id='wise',activity='rest',target_place_id='forest')
        first = self.client.post(self.url+'/actions',json=body)
        second = self.client.post(self.url+'/actions',json=body)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(self.client.get(self.url).json()['interventions_remaining'], 1)
        self.assertEqual(self.client.post(self.url+'/actions',json={**body,'activity':'read'}).status_code,409)
        self.assertEqual(self.client.post(self.url+'/actions',json={**body,'request_id':'stale'}).status_code,409)
        self.assertEqual(self.client.post(self.url+'/actions',json={**body,'energy':100}).status_code,422)

    def test_clamp_effect_and_recheck_exhaustion(self):
        self.suggest('stead','work','workshop')
        state = worlds[self.world['world_id']]['world']
        next(n for n in state['npcs'] if n['id']=='stead')['energy'] = 5
        self.post('/turns')
        self.assertEqual(self.npc('stead')['last_decision']['activity'],'rest')
        self.assertIn('精力不足',self.npc('stead')['reason'])
        # 接近上限时应报告实际恢复量，不能直接显示理论活动奖励。
        state = worlds[self.world['world_id']]['world']
        next(n for n in state['npcs'] if n['id']=='calm')['energy'] = 70
        self.suggest('calm', 'rest', 'forest')
        state = worlds[self.world['world_id']]['world']
        next(n for n in state['npcs'] if n['id']=='calm')['energy'] = 97
        self.post('/turns')
        self.assertEqual(next(r for r in self.world['last_results'] if r['npc_id']=='calm')['effects']['energy'],3)

    def test_read_and_work_execute(self):
        self.assertEqual(self.suggest('wise','read','library').json()['result']['outcome'],'accepted')
        self.assertEqual(self.suggest('stead','work','workshop').json()['result']['outcome'],'accepted')
        self.post('/turns')
        self.assertEqual(self.npc()['last_decision']['activity'],'read')
        self.assertEqual(self.npc('stead')['last_decision']['activity'],'work')

    def test_chat_requires_mutual_plans(self):
        self.assertEqual(self.suggest('joe','chat','plaza').json()['result']['outcome'],'declined')
        self.post('/turns')
        self.suggest('stead','chat','plaza')
        self.suggest('joe','chat','plaza')
        self.post('/turns')
        self.assertEqual(self.npc('joe')['last_decision']['activity'],'chat')
        self.assertEqual(self.npc('stead')['last_decision']['activity'],'chat')
        self.assertEqual(self.npc('stead')['place'],'plaza')

    def test_save_restore_pending_and_atomic_rejection(self):
        self.suggest()
        self.post('/commands',type='save')
        self.post('/turns')
        self.post('/commands',type='load')
        self.assertTrue(self.npc()['agenda'])
        self.assertEqual(self.npc()['place'],'library')
        self.post('/turns')
        self.assertEqual(self.npc()['place'],'forest')


if __name__ == '__main__':
    unittest.main()
