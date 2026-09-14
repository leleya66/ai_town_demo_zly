"""验证长椅事件状态与道路移动，使用独立测试世界和临时存档库。"""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.main import app, worlds
from backend.navigation import CORRIDORS, destination, movement


class BenchTests(unittest.TestCase):
    def setUp(self):
        # 保留旧档长椅计分和动作回归，新版路线另有端到端测试。
        from backend.world import fresh_world
        version=patch('backend.main.fresh_world',side_effect=lambda world_id:fresh_world(world_id,festival_version=1))
        version.start();self.addCleanup(version.stop)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch("backend.storage.DB_PATH", Path(directory.name) / "saves.sqlite3")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.world = self.client.post('/api/worlds').json()
        self.url = '/api/worlds/' + self.world['world_id']

    def post(self, path, **kwargs):
        r = self.client.post(self.url + path, json=dict(request_id=str(uuid4()), expected_revision=self.world['revision'], **kwargs))
        self.assertEqual(r.status_code, 200, r.text)
        self.world = r.json()['world']
        return r.json()['result']

    def suggest(self, who='stead', activity='repair_bench'):
        return self.post('/actions',type='suggest_activity',npc_id=who,activity=activity,target_place_id='forest')

    def discover(self):
        self.post('/commands',type='observe',place_id='forest')

    def test_discovery_skill_and_locked_seat(self):
        self.assertEqual(self.suggest()['outcome'],'declined')
        self.assertEqual(self.suggest('calm','sit_bench')['outcome'],'declined')
        self.assertFalse(self.world['bench_event']['discovered'])
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['progress'],0, 'ordinary workshop labor must not count')
        self.discover()
        self.assertTrue(self.world['bench_event']['discovered'])
        self.assertEqual(self.suggest('wise')['outcome'],'declined')
        self.assertEqual(self.suggest()['outcome'],'accepted')
        self.assertEqual(self.world['bench_event']['progress'],0)

    def test_two_labor_turns_complete_once_and_unlock(self):
        self.discover(); self.suggest()
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['progress'],1)
        self.assertEqual(self.world['bench_event']['status'],'repairing')
        result=next(r for r in self.world['last_results'] if r['npc_id']=='stead')
        self.assertEqual(result['effects']['energy'],-12)
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['status'],'repaired')
        completed=self.world['bench_event']['completed_turn']
        self.assertEqual(self.suggest()['outcome'],'declined')
        self.assertEqual(self.suggest('calm','sit_bench')['outcome'],'accepted')
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['completed_turn'],completed)
        self.assertEqual(self.world['bench_event']['progress'],2)
        self.assertEqual(next(d for d in self.world['last_decisions'] if d['npc_id']=='calm')['activity'],'sit_bench')

    def test_fatigue_pauses_and_resumes_committed_repair(self):
        self.discover(); self.suggest(); self.post('/turns')
        state=worlds[self.world['world_id']]['world']
        next(n for n in state['npcs'] if n['id']=='stead')['energy']=20
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['progress'],1)
        self.assertEqual(next(d for d in self.world['last_decisions'] if d['npc_id']=='stead')['activity'],'rest')
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['status'],'repaired')

    def test_save_restore_and_idempotent_turn(self):
        self.discover(); self.suggest(); self.post('/turns'); self.post('/commands',type='save')
        body=dict(request_id='same-turn',expected_revision=self.world['revision'])
        first=self.client.post(self.url+'/turns',json=body).json()
        again=self.client.post(self.url+'/turns',json=body).json()
        self.assertEqual(first,again)
        self.world=first['world']
        self.assertEqual(self.world['bench_event']['progress'],2)
        self.post('/commands',type='load')
        self.assertEqual(self.world['bench_event']['progress'],1)
        self.assertEqual(self.world['bench_event']['status'],'repairing')
        self.post('/turns')
        self.assertEqual(self.world['bench_event']['progress'],2)

    def test_cross_scene_routes_use_both_doors_and_road(self):
        for origin in CORRIDORS:
            for target in CORRIDORS:
                if origin==target: continue
                npc=dict(id='stead',place=origin,position=destination('stead',origin))
                move=movement(npc,target,'rest')
                self.assertEqual(move['points'][0],npc['position'])
                self.assertEqual(move['points'][-1],destination('stead',target,'rest'))
                for point in (*CORRIDORS[origin],*CORRIDORS[target]):
                    self.assertIn(list(point),move['points'])
                self.assertGreater(move['duration_ms'],0)
                self.assertTrue(all(0<=x<=800 and 0<=y<=600 for x,y in move['points']))

    def test_result_position_equals_last_waypoint(self):
        self.discover();self.suggest();self.post('/turns')
        for move in self.world['last_movements']:
            npc=next(n for n in self.world['npcs'] if n['id']==move['npc_id'])
            self.assertEqual(npc['position'],move['points'][-1])
            self.assertEqual(npc['place'],move['to_place_id'])


if __name__=='__main__': unittest.main()
