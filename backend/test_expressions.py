"""验证玩家与居民交流表情及记录，使用独立测试世界和临时存档库。"""
import unittest
from backend import test_api
from backend.service import worlds


class ExpressionTests(unittest.TestCase):
    setUp = test_api.SuggestionTests.setUp
    post = test_api.SuggestionTests.post
    suggest = test_api.SuggestionTests.suggest
    npc = test_api.SuggestionTests.npc
    def test_player_replies_and_read_only_commands(self):
        cue = self.suggest().json()['result']['expressions'][0]
        self.assertEqual((cue['npc_id'], cue['emotion'], cue['source']), ('wise', 'pleased', 'player'))
        declined = self.suggest('calm', 'work', 'workshop').json()['result']['expressions'][0]
        self.assertEqual(declined['emotion'], 'hesitant')
        self.assertEqual(self.post('/commands', type='message', npc_id='joe', text='你好').status_code,409)
        self.post('/turns')  # 两次干预后必须推进，再验证新的聊天表情。
        result = self.post('/commands', type='message', npc_id='joe', text='你好').json()['result']
        self.assertEqual(result['expressions'][0]['emotion'], 'happy')
        self.assertNotIn('expressions', self.world)
        for kind in ('save', 'load', 'reset'):
            self.assertNotIn('expressions', self.post('/commands', type=kind).json()['result'])

    def test_completed_mutual_chat_has_two_cues_and_memories(self):
        self.suggest('stead', 'chat', 'plaza')
        self.suggest('joe', 'chat', 'plaza')
        result = self.post('/turns').json()['result']
        self.assertEqual({c['npc_id'] for c in result['expressions']}, {'joe', 'stead'})
        self.assertTrue(all(c['source'] == 'npc' for c in result['expressions']))
        for name in ('joe', 'stead'):
            self.assertIn('Joe：', self.npc(name)['memory'][0])
            self.assertIn('Stead：', self.npc(name)['memory'][0])

    def test_unfulfilled_chat_does_not_emit_social_expression(self):
        for n in worlds[self.world['world_id']]['world']['npcs']:
            if n['id'] != 'joe': n['social'] = 0
        result = self.post('/turns').json()['result']
        self.assertEqual(result['expressions'], [])

    def test_duplicate_request_keeps_expression_identity(self):
        body = dict(request_id='same-talk', expected_revision=0, type='message', npc_id='joe', text='你好')
        first = self.client.post(self.url + '/commands', json=body).json()
        second = self.client.post(self.url + '/commands', json=body).json()
        self.assertEqual(first['result']['expressions'], second['result']['expressions'])
