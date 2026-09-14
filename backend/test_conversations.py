"""验证话题事实、双边记忆、记忆配对偏好与失败边界；使用独立世界不改用户数据。"""
import unittest
from copy import deepcopy
from backend.world import fresh_world
from backend.conversations import converse
from backend.social import match_social
from backend.models import NpcDecision
from backend.simulation import advance_world


class ConversationTests(unittest.TestCase):
    def test_three_topics_and_snapshot_facts(self):
        for topic in ('care', 'experience', 'greeting'):
            w=fresh_world(topic, festival_version=1); before=deepcopy(w)
            if topic=='care': before['npcs'][0]['mood']=42
            if topic=='experience': before['npcs'][0]['last_decision']=dict(activity='work')
            converse(w,before,'joe','calm','plaza')
            a,b=w['npcs'][0]['social_memories'][0],w['npcs'][2]['social_memories'][0]
            self.assertEqual(a['topic'],topic); self.assertEqual(a['id'],b['id'])
            self.assertEqual(a['partner_id'],'calm'); self.assertEqual(b['partner_id'],'joe')
            self.assertIsNot(a['facts'],b['facts'])
            if topic=='care': self.assertEqual(a['facts']['value'],42)
            self.assertEqual(w['npcs'][0]['energy'],78)
            self.assertEqual(len(w['events']),1)

    def plans(self):
        return [NpcDecision(npc_id=id,activity='seek_company',target_place_id='plaza',reason='愿意交流').model_dump() for id in ('joe','wise','calm','stead')]

    def test_memory_changes_partner_without_forcing_unwilling(self):
        w=fresh_world('partners', festival_version=1)
        for n in w['npcs']: n['social']=70
        baseline=self.plans(); match_social(w,baseline)
        before=deepcopy(w); before['npcs'][1]['mood']=42
        converse(w,before,'wise','calm','plaza')
        plans=self.plans(); match_social(w,plans)
        calm=next(d for d in plans if d['npc_id']=='calm')
        self.assertEqual(calm['target_npc_id'],'wise')
        self.assertNotEqual(next(d for d in baseline if d['npc_id']=='calm')['target_npc_id'],'wise')
        self.assertTrue(calm['related_memory_ids']); self.assertIn('关心近况',calm['reason'])
        plans=self.plans(); plans[1].update(activity='read',target_place_id='library'); match_social(w,plans)
        self.assertNotEqual(next(d for d in plans if d['npc_id']=='calm')['target_npc_id'],'wise')
        w['turn']=7
        expired=self.plans(); match_social(w,expired)
        self.assertEqual([(d['npc_id'],d['target_npc_id']) for d in expired],[(d['npc_id'],d['target_npc_id']) for d in baseline])

    def test_failed_seek_no_memories_and_success_one_per_person(self):
        w=fresh_world('failure', festival_version=1)
        for n in w['npcs']: n['social']=0
        advance_world(w)
        self.assertTrue(all(not n.get('social_memories') for n in w['npcs']))
        w=fresh_world('success', festival_version=1); advance_world(w)
        self.assertEqual(sum(len(n.get('social_memories',[])) for n in w['npcs']),2)

class ConversationPersistenceTests(unittest.TestCase):
    def test_retry_and_save_restore(self):
        from backend import test_api
        helper=test_api.SuggestionTests(); helper.setUp()
        self.addCleanup(helper.doCleanups)
        body=dict(request_id='social-once',expected_revision=helper.world['revision'])
        first=helper.client.post(helper.url+'/turns',json=body).json()
        again=helper.client.post(helper.url+'/turns',json=body).json()
        self.assertEqual(first,again)
        helper.world=first['world']
        memories=[n.get('social_memories',[]) for n in helper.world['npcs']]
        helper.post('/commands',type='save')
        helper.post('/commands',type='reset')
        self.assertTrue(all(not n.get('social_memories') for n in helper.world['npcs']))
        helper.post('/commands',type='load')
        self.assertEqual([n.get('social_memories',[]) for n in helper.world['npcs']],memories)
