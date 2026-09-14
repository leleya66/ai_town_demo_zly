"""验证统一状态评估、缺失统计与冻结终局，不允许平均值或成就隐藏风险。"""
import unittest
from copy import deepcopy
from backend.world import fresh_world, update_summary
from backend.assessment import assess_world
from backend.endings import finish_if_due


class AssessmentTests(unittest.TestCase):
    def test_tired_and_low_mood_both_visible_despite_achievement(self):
        world = fresh_world('test', festival_version=1)
        world['turn'] = 6
        world['npcs'][0].update(energy=20, mood=20)
        world['npcs'][1]['energy'] = 25
        world['bench_event'].update(status='repaired', completed_turn=5)
        result = assess_world(world)
        self.assertEqual(result['status'], '疲惫的小镇')
        self.assertEqual(len(result['warnings']), 2)
        self.assertIn('Joe', result['warnings'][1])
        self.assertIn('长椅已修好', result['experiences'])
        finish_if_due(world)
        update_summary(world)
        self.assertEqual(world['ecology'], world['ending']['title'])
        self.assertEqual(world['assessment'], world['ending']['assessment'])
        self.assertEqual(world['ending']['assessment']['warnings'], result['warnings'])

    def test_single_mild_fatigue_cannot_be_called_peaceful(self):
        world = fresh_world('test', festival_version=1)
        world['npcs'][0]['energy'] = 34
        for n in world['npcs']: n['social'] = 10
        result = assess_world(world)
        self.assertEqual(result['status'], '有人需要歇歇')
        self.assertEqual(result['ending_title'], '有人需要歇歇')

    def test_unknown_chat_count_is_not_zero(self):
        world = fresh_world('test', festival_version=1)
        world['turn'] = 9
        for n in world['npcs']: n.pop('life_stats')
        result = assess_world(world)
        self.assertIsNone(result['chat_count'])
        self.assertIn('交流次数未记录', result['experiences'])
        self.assertNotIn('没有双人交流', result['ending_reason'])

    def test_social_willingness_alone_does_not_prove_conversation(self):
        world = fresh_world('test', festival_version=1)
        for n in world['npcs']: n['social'] = 100
        result = assess_world(world)
        self.assertEqual(result['status'], '状态平稳')
        self.assertEqual(result['chat_count'], 0)
        self.assertNotEqual(result['ending_title'], '烟火共生')
        world['npcs'][0]['life_stats']['chats'] = 1
        world['npcs'][1]['life_stats']['chats'] = 1
        self.assertEqual(assess_world(world)['ending_title'], '烟火共生')

    def test_existing_ending_title_is_preserved_on_read(self):
        world = fresh_world('test', festival_version=1)
        world.update(phase='ended', turn=6, ending={'id':'old', 'title':'历史结局', 'reason':'原快照'})
        old = deepcopy(world['ending'])
        update_summary(world)
        self.assertEqual(world['ending'], old)
        self.assertEqual(world['ecology'], '历史结局')
