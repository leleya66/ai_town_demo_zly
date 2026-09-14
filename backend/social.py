"""集中匹配本回合社交意图：同场、双向意愿、一人一对；没有匹配不结算聊天收益。"""
from backend.rules import PLACES, RULES
from backend.eligibility import blocked
from backend.conversations import partner_evidence


def match_social(world, decisions):
    plans = {d['npc_id']: d for d in decisions}
    residents = {n['id']: n for n in world['npcs']}
    social = [d for d in decisions if d['activity'] in ('chat', 'seek_company')]
    paired = set()
    # 明确指定对象的邀请优先，之后按居民ID稳定配对，避免遍历顺序随机改变结果。
    ordered = sorted(social, key=lambda d: (d['target_npc_id'] is None, d['npc_id']))
    for a in ordered:
        if a['npc_id'] in paired:
            continue
        # 明确对象仍是约束；在可匹配对象中，双方共同记忆只改变选择偏好。
        def affinity(b):
            return sum(partner_evidence(residents[x], y, world['turn'])[0]
                       for x,y in ((a['npc_id'], b['npc_id']), (b['npc_id'], a['npc_id'])))
        for b in sorted(ordered, key=lambda b: (-affinity(b), b['npc_id'])):
            if b['npc_id'] == a['npc_id'] or b['npc_id'] in paired or a['target_place_id'] != b['target_place_id']:
                continue
            if a['target_npc_id'] not in (None, b['npc_id']) or b['target_npc_id'] not in (None, a['npc_id']):
                continue
            # 执行层再次守住状态门槛，候选选择不能越权创建交流。
            if any(residents[d['npc_id']]['energy'] < 30 or residents[d['npc_id']]['mood'] < 40 or residents[d['npc_id']]['social'] < 35 for d in (a,b)):
                continue
            for current, other in ((a,b),(b,a)):
                _, memory = partner_evidence(residents[current['npc_id']], other['npc_id'], world['turn'])
                if memory:
                    current['related_memory_ids'].append(memory['id'])
                    current['reason'] += f"记得第{memory['turn']}回合与{residents[other['npc_id']]['name']}的{memory['topic_label']}，在双方可匹配的伙伴中优先续聊；这不代表对方仍处于当时的状态。"
                current.update(activity='chat', target_npc_id=other['npc_id'])
                current['reason'] += f"本回合与{residents[other['npc_id']]['name']}都选择来到{PLACES[current['target_place_id']]['name']}交流，双方计划匹配成功。"
            paired.update((a['npc_id'], b['npc_id']))
            break
    for d in social:
        if d['npc_id'] in paired:
            continue
        target = d['target_npc_id']
        why = '本回合没有匹配到同场且双方愿意交流的居民。'
        if target:
            other = plans[target]
            why = f"{residents[target]['name']}本回合选择{PLACES[other['target_place_id']]['name']}{RULES[other['activity']]['label']}，未与我的邀请匹配。"
        # 赴约可以发生，但邀请只有成功聊天才完成；不把等待误当成履约。
        d.update(activity='seek_company', target_npc_id=None, agenda_item_id=None, source_action_id=None, related_memory_ids=[])
        constraint = blocked(world, residents[d['npc_id']], 'seek_company', d['target_place_id'])
        if constraint:
            d.update(activity='rest', target_place_id=residents[d['npc_id']]['place'])
            d['reason'] += constraint[1] + '改为原地休息，未完成的邀请保留原期限。'
        else:
            d['reason'] += why + '这次只寻找伙伴，不获得聊天收益；未完成的邀请保留原期限。'
