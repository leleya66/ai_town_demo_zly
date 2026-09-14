"""验证全库十条上限、并发保存、幂等删除及超额旧库保护，所有数据均在临时库。"""
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from backend import test_api, storage


class SaveLimitTests(unittest.TestCase):
    setUp = test_api.SuggestionTests.setUp
    post = test_api.SuggestionTests.post

    def test_limit_and_deletion_leave_world_unchanged(self):
        for _ in range(10):
            self.assertEqual(self.post('/commands', type='save').status_code, 200)
        before = self.world
        entries = storage.listing()
        response = self.post('/commands', type='save')
        self.assertEqual(response.status_code, 409)
        self.assertIn('10条', response.json()['detail'])
        self.assertEqual(self.client.get(self.url).json(), before)
        self.assertEqual(storage.listing(), entries)
        key = entries[-1]['id']
        self.assertEqual(self.client.delete('/api/saves/' + key).status_code, 200)
        self.assertEqual(self.client.delete('/api/saves/' + key).status_code, 200)
        self.assertEqual(len(storage.listing()), 9)
        self.assertEqual(self.client.get(self.url).json(), before)
        self.assertEqual(self.post('/commands', type='save').status_code, 200)
        self.assertEqual(len(storage.listing()), 10)

    def test_concurrent_saves_share_one_remaining_slot(self):
        for _ in range(9):
            storage.save(self.world)
        def attempt(_):
            try:
                storage.save(self.world)
                return 'saved'
            except storage.SaveLimitReached:
                return 'full'
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))
        self.assertEqual(results.count('saved'), 1)
        self.assertEqual(len(storage.listing()), 10)

    def test_legacy_over_limit_is_preserved_and_blocks_new_save(self):
        with storage.connect() as db:
            for i in range(11):
                db.execute('INSERT INTO saves VALUES (?, ?, ?)', (f'legacy-{i}', str(i), json.dumps(self.world)))
        before = storage.listing()
        self.assertEqual(self.post('/commands', type='save').status_code, 409)
        self.assertEqual(storage.listing(), before)
        self.client.delete('/api/saves/legacy-0')
        self.assertEqual(self.post('/commands', type='save').status_code, 409)
        self.client.delete('/api/saves/legacy-1')
        self.assertEqual(self.post('/commands', type='save').status_code, 200)

    def test_delete_failure_reports_error_without_removing_snapshot(self):
        storage.save(self.world)
        before = storage.listing()
        with patch('backend.storage.delete', side_effect=OSError('read only')):
            self.assertEqual(self.client.delete('/api/saves/' + before[0]['id']).status_code, 503)
        self.assertEqual(storage.listing(), before)
