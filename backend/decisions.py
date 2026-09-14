"""把建议加入待办，并由规则偏好在合法候选项中选择；输出可追溯到真实状态的理由。"""
from backend.rules import PLACES, RULES
from backend.models import NpcDecision
from backend.world import fail, message, record, expression, npc_by_id
from backend.eligibility import blocked, partner
from backend.preferences import preference_refusal, ranked
from backend.agenda import MAX_AGENDA, make_item, reconcile
from backend.autonomy import choose_autonomous


def submit_suggestion(world, cmd):
    if cmd.activity == 'seek_company':
        fail(422, '寻找伙伴是居民自主行为；玩家可以提出闲聊邀请。')
    if cmd.target_place_id not in RULES[cmd.activity]['places']:
        fail(422, '该地点不支持这项活动。')
    reconcile(world)
    npc = npc_by_id(world, cmd.npc_id)
    duplicate = next((t for t in npc['agenda'] if t['activity'] == cmd.activity and t['target_place_id'] == cmd.target_place_id), None)
    if duplicate:
        reason = f"{RULES[cmd.activity]['label']}已在待办中，不重复添加，也不额外消耗建议机会。"
        return dict(outcome='accepted', reason=reason, merged=True, agenda_item_id=duplicate['id'])
    if world['interventions_remaining'] <= 0:
        fail(409, '本回合的两次建议机会已用完，请推进回合。')
    constraint = blocked(world, npc, cmd.activity, cmd.target_place_id)
    reason = constraint[1] if constraint else preference_refusal(npc, cmd.activity)
    if not reason and len(npc['agenda']) >= MAX_AGENDA:
        reason = '已有3项有效待办，暂时不能再答应新安排；先完成已有承诺。'
    outcome = 'declined' if reason else 'accepted'
    item = None
    if outcome == 'accepted':
        item = make_item(cmd.activity, cmd.target_place_id, world['turn'], cmd.request_id)
        npc['agenda'].append(item)
        ahead = ranked(npc, npc['agenda'])
        reason = f"我接受去{PLACES[cmd.target_place_id]['name']}{RULES[cmd.activity]['label']}的建议，精力{npc['energy']}/100，已加入待办。"
        if ahead[0]['id'] != item['id']:
            reason += f"按当前安排，先处理{RULES[ahead[0]['activity']]['label']}，之后再检查这项活动的条件。"
        else:
            reason += '预计下一回合优先考虑，执行前仍会检查状态。'
        if item['expires_at_turn'] is not None:
            reason += f"这次临时邀请有效至第{item['expires_at_turn']}回合。"
    elif npc['agenda']:
        reason += '已有待办保留，不受本次拒绝影响。'
    message(world, npc, 'user', f"建议你去{PLACES[cmd.target_place_id]['name']}{RULES[cmd.activity]['label']}。")
    message(world, npc, 'npc', reason)
    memory_id = record(world, npc, f"{npc['name']} {'拒绝' if outcome == 'declined' else '接受'}了{RULES[cmd.activity]['label']}建议：{reason}")
    if item:
        item['memory_id'] = memory_id
    world['interventions_remaining'] -= 1
    return dict(outcome=outcome, reason=reason, reply=reason, agenda_item_id=item['id'] if item else None,
                expressions=[expression(npc, 'pleased' if item else 'hesitant', reason)])


def decide(world, npc):
    # 硬约束筛掉不可执行事项，偏好层只在合法选项中排序；低精力不能继续劳动。
    valid = [t for t in npc['agenda'] if (t['expires_at_turn'] is None or t['expires_at_turn'] >= world['turn'] + 1)
             and not blocked(world, npc, t['activity'], t['target_place_id'])]
    chosen = None
    if npc['energy'] < 30:
        activity, place = 'rest', 'forest'
        chosen = next((t for t in ranked(npc, valid) if t['activity'] == 'rest'), None)
        reason = f"我现在精力不足（{npc['energy']}/100，低于30），本回合先去林间休息。"
        if chosen:
            place = chosen['target_place_id']
            reason = f"我现在精力不足（{npc['energy']}/100，低于30），按休息待办去{PLACES[place]['name']}休息。"
        if npc['agenda']:
            reason += '未执行的待办保留，临时邀请仍按原期限检查。'
    elif valid:
        chosen = ranked(npc, valid)[0]
        activity, place = chosen['activity'], chosen['target_place_id']
        origin = f"记得你第{chosen['accepted_turn']}回合建议我去" if chosen['accepted_turn'] is not None else '旧存档记录了尚未完成的承诺：去'
        if chosen.get('intention_id') and not chosen.get('source_action_id'):
            origin = '为落实听到长椅需求后形成的帮助打算，准备去'
        reason = f"{origin}{PLACES[place]['name']}{RULES[activity]['label']}。目前精力{npc['energy']}/100，"
        if chosen['started']:
            bench = world['bench_event']
            reason += f"长椅进度{bench['progress']}/{bench['required']}，优先完成已经开始的承诺。"
        else:
            reason += '按较早承诺优先、同回合结合需求与偏好的规则，选择执行这项待办。'
    else:
        activity, place, reason = choose_autonomous(world, npc)
    intention = npc.get('bench_intention')
    if intention and chosen and chosen['id'] == intention['agenda_item_id']:
        reason += f"这项安排关联第{intention['source_turn']}回合 Calm 告诉我的长椅需求；为履行帮助打算而行动。"
    constraint = blocked(world, npc, activity, place)
    if constraint:
        activity, place, chosen = 'rest', npc['place'], None
        reason = f"{constraint[1]}改在{PLACES[place]['name']}休息，未执行的待办保留。"
    target = partner(world, npc, place) if activity == 'chat' else None
    if target:
        reason += f"希望与{target['name']}交流，双方最终计划还需要匹配。"
    result = NpcDecision(npc_id=npc['id'], activity=activity, target_place_id=place,
                       target_npc_id=target['id'] if target else None, reason=reason,
                       agenda_item_id=chosen['id'] if chosen else None,
                       related_memory_ids=[chosen['memory_id']] if chosen and chosen['memory_id'] else [],
                       source_action_id=chosen['source_action_id'] if chosen else None).model_dump()
    from backend.invitations import rule_choice
    return rule_choice(world,npc,result)
