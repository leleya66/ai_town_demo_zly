"""验证第0回合重置与持久存档恢复，使用独立测试世界和临时存档库。"""
import unittest
from unittest.mock import patch
from backend import test_api, storage
from backend.main import worlds


class SaveTests(unittest.TestCase):
    setUp = test_api.SuggestionTests.setUp
    post = test_api.SuggestionTests.post
    suggest = test_api.SuggestionTests.suggest
    npc = test_api.SuggestionTests.npc

    def test_zero_reset_clears_game_and_preserves_save(self):
        self.assertEqual(self.world['turn'], 0)
        self.suggest()
        self.post('/turns')
        self.post('/commands', type='save')
        self.post('/commands', type='reset')
        self.assertEqual(self.world['turn'], 0)
        self.assertEqual(self.world['events'], [])
        self.assertEqual(self.world['last_movements'], [])
        self.assertEqual(self.world['tasks'], [False]*3)
        self.assertEqual(self.world['bench_event']['progress'], 0)
        self.assertTrue(all(n['memory'] == [] and n['agenda'] == [] for n in self.world['npcs']))
        self.post('/commands', type='load')
        self.assertEqual(self.world['turn'], 1)

    def test_disk_save_survives_lost_process_memory_and_loads_in_new_world(self):
        self.suggest()
        self.post('/commands', type='save')
        expected = self.world
        worlds.pop(self.world['world_id'])
        restored = self.client.get(self.url).json()
        self.assertEqual(restored, expected)
        entries = self.client.get('/api/saves').json()
        self.assertEqual(len(entries), 1)
        self.world = self.client.post('/api/worlds').json()
        self.url = '/api/worlds/' + self.world['world_id']
        self.post('/commands', type='load', save_id=entries[0]['id'])
        self.assertTrue(self.npc()['agenda'])
        self.assertEqual(self.world['world_id'], self.url.split('/')[-1])

    def test_failed_save_leaves_state_and_existing_snapshot_untouched(self):
        self.post('/commands', type='save')
        old = storage.listing()
        revision = self.world['revision']
        with patch('backend.storage.save', side_effect=OSError('disk full')):
            self.assertEqual(self.post('/commands', type='save').status_code, 503)
        self.assertEqual(self.world['revision'], revision)
        self.assertEqual(storage.listing(), old)

    def test_save_retry_does_not_duplicate_and_missing_load_is_atomic(self):
        body = dict(type='save', request_id='save-once', expected_revision=0)
        a = self.client.post(self.url+'/commands', json=body)
        b = self.client.post(self.url+'/commands', json=body)
        self.assertEqual(a.json(), b.json())
        self.assertEqual(len(storage.listing()), 1)
        self.world = a.json()['world']
        self.assertEqual(self.post('/commands', type='load', save_id='missing').status_code, 409)

    def test_each_save_keeps_an_independent_snapshot(self):
        self.post('/commands', type='save')
        first_id = self.client.get('/api/saves').json()[0]['id']
        self.post('/turns')
        self.post('/commands', type='save')
        entries = self.client.get('/api/saves').json()
        self.assertEqual(len(entries), 2)
        self.assertEqual({entry['turn'] for entry in entries}, {0, 1})
        self.post('/commands', type='load', save_id=first_id)
        self.assertEqual(self.world['turn'], 0)
        self.assertEqual(len(self.client.get('/api/saves').json()), 2)
