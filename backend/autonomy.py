"""从合法候选中选择自主活动；需求、人格及重复行为影响选择，不依赖随机游走。"""
from backend.rules import PREFERRED, RULES
from backend.eligibility import blocked


def choose_autonomous(world, npc):
    streak = npc.get('activity_streak', {})
    repeated = streak.get('count', 0)
    previous = streak.get('activity')
    candidates = [('rest', 'forest'), ('read', 'library'), ('seek_company', 'plaza')]
    if npc['id'] in ('stead', 'joe'):
        candidates.append(('work', 'workshop'))
    if world['bench_event']['status'] == 'repaired':
        candidates.append(('sit_bench', 'forest'))
    energy, mood, social = npc['energy'], npc['mood'], npc['social']
    def score(activity):
        if activity in ('rest', 'sit_bench'):
            value = 8 + (100-energy)*.9 + (100-mood)*.15
            value += 30 if npc['id'] == 'calm' else 0
            value -= 35 if energy >= 75 else 0
            value += 4 if activity == 'sit_bench' else 0
        elif activity == 'seek_company':
            value = social*.8 + {'joe':25, 'calm':8, 'wise':-10, 'stead':-10}[npc['id']]
            value -= 20 if energy < 50 else 0
            value -= 25 if world['turn'] - npc.get('last_chat_turn', -100) <= 1 else 0
        else:
            value = 26 if activity == 'work' else 24
            value += 30 if activity == PREFERRED[npc['id']][0] else 0
        return value - (18 * repeated if previous == activity else 0)
    valid = [(activity, place) for activity, place in candidates if not blocked(world, npc, activity, place)]
    activity, place = max(valid, key=lambda c: score(c[0]))
    facts = f"我目前精力{energy}/100、情绪{mood}/100、社交意愿{social}/100。"
    if previous and repeated:
        facts += f"已连续{repeated}回合{RULES[previous]['label']}。"
    motives = {'rest':'根据当前精力与连续活动，先去林间休息调整节奏。',
               'sit_bench':'长椅已经修好，去那里休憩并调整节奏。',
               'read':'比较当前需求、个人偏好与连续活动后，去图书馆阅读。',
               'work':'比较当前需求、个人偏好与连续活动后，去工坊修缮。',
               'seek_company':'我愿意交流，先去广场寻找伙伴；遇到双方都愿意交流的人才聊天。'}
    return activity, place, facts + motives[activity]
