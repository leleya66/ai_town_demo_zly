"""六回合数值版本：旧局保持旧效果，新局使用有消耗、独处恢复社交及重复活动衰减的规则。"""
from backend.rules import RULES, METRICS

BALANCED_EFFECTS = {
    'invite_event':(-2,1,0), 'run_event':(-4,3,-2), 'join_event':(-3,3,-2),
    'prepare_talk': (-6, 2, 2), 'host_talk': (-6, 4, -4), 'attend_talk': (-3, 3, -2),
    'seek_company': (-2, 0, 0),
    'rest': (12, 2, 5), 'read': (-6, 3, 4), 'chat': (-4, 6, -12),
    'work': (-10, 1, 2), 'repair_bench': (-12, 1, 2), 'sit_bench': (16, 3, 4),
}
INITIAL_MOODS = {'joe': 64, 'wise': 66, 'calm': 60, 'stead': 62}


def configure(world):
    """旧快照缺少版本时按旧规则读取，绝不截断原回合或改写居民数值。"""
    world.setdefault('rules_version', 1)
    world.setdefault('max_turns', None)
    world.setdefault('phase', 'playing')
    world.setdefault('ending', None)
    effects = BALANCED_EFFECTS if world['rules_version'] == 2 else {key: rule['effects'] for key, rule in RULES.items()}
    world['activity_rules'] = {key: dict(label=rule['label'], places=sorted(rule['places']), effects=dict(zip(METRICS, effects[key])), suggestible=key != 'seek_company') for key, rule in RULES.items()}


def action_effects(world, npc, activity):
    # 连续重复的收益逐次下降；记录在结果中，不能用台词掩盖数值来源。
    previous = npc.get('activity_streak', {})
    count = previous.get('count', 0) + 1 if previous.get('activity') == activity else 1
    npc['activity_streak'] = dict(activity=activity, count=count)
    if world['rules_version'] == 1:
        return RULES[activity]['effects'], []
    energy, mood, social = BALANCED_EFFECTS[activity]
    adjusted = max(-2, mood - 2 * (count - 1))
    notes = [f'连续第{count}回合{RULES[activity]["label"]}，情绪效果由{mood:+d}调整为{adjusted:+d}。'] if count > 1 else []
    if activity == 'repair_bench' and world['bench_event']['progress'] + 1 == world['bench_event']['required']:
        adjusted += 6
        notes.append('本次修好长椅，获得一次性情绪奖励+6。')
    stats = npc.setdefault('life_stats', dict(actions={}, chats=0))
    stats['actions'][activity] = stats['actions'].get(activity, 0) + 1
    if activity == 'chat':
        stats['chats'] += 1
    return (energy, adjusted, social), notes
