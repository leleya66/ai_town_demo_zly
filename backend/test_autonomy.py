"""验证无玩家干预的自主移动、双向社交、失败无奖励及稳定可复现的选择。"""
import unittest
from copy import deepcopy
from backend.world import fresh_world
from backend.simulation import advance_world
from backend.service import enrich
from backend.decisions import decide
from backend.social import match_social
from backend.models import NpcDecision
from backend.eligibility import blocked
from backend import test_api


class AutonomyTests(unittest.TestCase):
    def test_passive_six_turns_move_every_resident_and_allow_real_chat(self):
        def play():
            world = fresh_world('passive', festival_version=1)
            traces = {n['id']:{n['place']} for n in world['npcs']}
            turns = []
            for _ in range(6):
                advance_world(world); enrich(world)
                turns.append([(n['id'], n['place'], n['last_decision']['activity'], n['energy']) for n in world['npcs']])
                for n in world['npcs']: traces[n['id']].add(n['place'])
                for d in world['last_decisions']:
                    if d['activity']=='chat':
                        other = next(p for p in world['last_decisions'] if p['npc_id']==d['target_npc_id'])
                        self.assertEqual(other['target_npc_id'], d['npc_id'])
                        self.assertEqual(other['target_place_id'], d['target_place_id'])
            self.assertTrue(all(len(places)>=2 for places in traces.values()))
            self.assertGreater(world['ending']['chat_count'],0)
            self.assertTrue(all(n['energy'] >= 35 for n in world['npcs']))
            return turns
        self.assertEqual(play(), play(), '相同初始状态产生相同决策，不靠随机表演')

    def test_no_partner_is_seeking_not_chat_and_has_no_chat_reward(self):
        world = fresh_world('alone', festival_version=1)
        for n in world['npcs']:
            if n['id'] != 'joe': n['social'] = 0
        result = advance_world(world)
        joe = world['npcs'][0]
        self.assertEqual(joe['last_decision']['activity'], 'seek_company')
        self.assertEqual(joe['life_stats']['chats'],0)
        self.assertEqual(joe['social'],75)
        self.assertEqual(joe['mood'],64)
        self.assertEqual(result['expressions'],[])
        self.assertIn('不获得聊天收益', joe['reason'])

    def test_reading_plan_is_not_forced_to_join_seekers(self):
        world=fresh_world('plans', festival_version=1)
        plans=[NpcDecision(npc_id='joe',activity='seek_company',target_place_id='plaza',reason='愿意交流').model_dump(),
               NpcDecision(npc_id='wise',activity='read',target_place_id='library',reason='继续阅读').model_dump()]
        match_social(world,plans)
        self.assertEqual(plans[1]['activity'],'read')
        self.assertEqual(plans[0]['activity'],'seek_company')

    def test_soft_fatigue_and_hard_constraint_are_distinct(self):
        world=fresh_world('energy', festival_version=1)
        wise=world['npcs'][1]
        wise['energy']=40
        self.assertIsNone(blocked(world,wise,'read','library'))
        self.assertEqual(decide(world,wise)['activity'],'rest')
        wise['energy']=20
        self.assertIsNotNone(blocked(world,wise,'read','library'))
        self.assertEqual(decide(world,wise)['activity'],'rest')

    def test_seek_pairing_checks_final_conditions(self):
        world=fresh_world('invalid', festival_version=1)
        world['npcs'][0]['energy']=5
        plans=[NpcDecision(npc_id=id,activity='seek_company',target_place_id='plaza',reason='候选').model_dump() for id in ('joe','calm')]
        match_social(world,plans)
        self.assertEqual(plans[0]['activity'],'rest')
        self.assertEqual(plans[1]['activity'],'seek_company')

    def test_world_assessment_uses_frozen_ending(self):
        world=fresh_world('final', festival_version=1)
        for _ in range(6): advance_world(world)
        enrich(world)
        self.assertEqual(world['ecology'],world['ending']['title'])
        self.assertEqual(world['assessment'],world['ending']['assessment'])


class AutonomyApiTests(unittest.TestCase):
    setUp=test_api.SuggestionTests.setUp
    post=test_api.SuggestionTests.post
    suggest=test_api.SuggestionTests.suggest

    def test_seek_is_an_autonomous_action_not_an_extra_player_command(self):
        self.assertFalse(self.world['activity_rules']['seek_company']['suggestible'])
        self.assertEqual(self.suggest('joe','seek_company','plaza').status_code,422)
        self.assertEqual(self.world['interventions_remaining'],2)

    def test_same_turn_is_not_settled_twice_with_autonomous_socializing(self):
        body={'request_id':'once','expected_revision':0}
        first=self.client.post(self.url+'/turns',json=body)
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.json(),self.client.post(self.url+'/turns',json=body).json())
        world=self.client.get(self.url).json()
        self.assertEqual(world['assessment']['chat_count'],1)
