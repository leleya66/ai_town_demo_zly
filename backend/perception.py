"""为对话和回合选择提供真实角色状态、有限记忆与合法活动；不暴露其他居民私密记忆。"""
from backend.rules import RULES
from backend.eligibility import blocked
from backend.event_rules import modern, EVENTS


def memories(npc, turn):
    entries = [*npc.get('dialogue_memories', []), *npc.get('social_memories', []), *npc.get('action_memories', []), *npc.get('invitation_memories',[])]
    pinned = {t.get('memory_id') for t in npc.get('agenda',[])}
    pinned.add((npc.get('bench_intention') or {}).get('source_memory_id'))
    # 未完成承诺的来源优先保留，避免精简上下文后忘记承诺依据。
    return sorted([m for m in entries if m['turn'] <= turn], key=lambda m: (m['id'] in pinned,m['turn']), reverse=True)[:6]


def context(world, npc):
    data = dict(turn=world['turn'], remaining_turns=None if world.get('max_turns') is None else world['max_turns']-world['turn'],
                resident={key: npc.get(key) for key in ('id','name','personality','subtitle','place','energy','mood','social','agenda')},
                memories=memories(npc,world['turn']),
                public_residents=[dict(id=n['id'],place=n['place'],announced_agenda=[{'activity':t['activity'],'place':t['target_place_id']} for t in n['agenda']]) for n in world['npcs']],
                public_activity={k:world.get('festival',{}).get(k) for k in ('prepared_by','talk_completed','goals','ranking')},
                contribution_rules={'repair_bench':'每次实际修缮2分','host_talk':'准备后有听众的实际分享4分',
                                    'attend_talk':'实际参加1分','chat':'同一伙伴首次有效交流1分，关心低落对象另加1分',
                                    'other':'休息、阅读、准备、普通工坊work不直接加分；不能声称它们完成公共目标'},
                known_bench=world['bench_event'] if world['bench_event']['discovered'] else '尚未发现需求')
    if modern(world):
        from backend.invitations import known
        data['invitations']=known(world,npc)
        data['event_roles']=EVENTS
        data['contribution_rules']='每条路线封顶6分：Joe每位实际关心对象2分；Wise每位实际听众2分；Calm每位实际倾听对象2分；Stead修好长椅2分、每位实际告知对象2分。同一对象不重复计分，邀请和接受不计分。'
    return data


def options(world, npc):
    result = []
    for activity, rule in RULES.items():
        if modern(world) and activity in ('invite_event','run_event','join_event','host_talk','attend_talk'):continue
        for place in sorted(rule['places']):
            if not blocked(world,npc,activity,place):
                item = next((t for t in npc['agenda'] if t['activity']==activity and t['target_place_id']==place),None)
                result.append(dict(id=str(len(result)),activity=activity,place=place,label=rule['label'],
                                   agenda_item_id=item['id'] if item else None))
    if modern(world):
        from backend.invitations import choices
        for choice in choices(world,npc):
            item=next((t for t in npc['agenda'] if t['activity']==choice['activity'] and t['target_place_id']==choice['place']),None)
            result.append(dict(id=str(len(result)),label=RULES[choice['activity']]['label'],agenda_item_id=item['id'] if item else None,**choice))
    return result
