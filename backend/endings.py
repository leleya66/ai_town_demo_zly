"""在第六次实际结算后冻结结局；基于个体状态及真实参与记录生成后记，不由前端或模型判定。"""
from uuid import uuid4
from copy import deepcopy
from backend.rules import RULES
from backend.assessment import assess_world


def finish_if_due(world):
    if world['max_turns'] is None or world['turn'] < world['max_turns'] or world['ending']:
        return
    residents = world['npcs']
    assessment = assess_world(world)
    title, reason = assessment['ending_title'], assessment['ending_reason']
    chats = assessment['chat_count']
    bench = world['bench_event']
    epilogues = []
    for npc in residents:
        actions = npc.get('life_stats', {}).get('actions', {})
        experience = '、'.join(f'{RULES[key]["label"]}{count}回合' for key, count in actions.items()) or '没有活动记录'
        text = f'这六回合：{experience}。'
        if bench['status'] == 'repaired' and bench['assigned_npc_id'] == npc['id']:
            text += '亲手修好了林间长椅。'
        if npc['id'] in assessment['tired_ids']:
            text += '结束时有些疲惫，需要休息。'
        if npc['id'] in assessment['low_mood_ids']:
            text += '心情仍然低落。'
        if npc['agenda']:
            text += f'仍有{len(npc["agenda"])}项承诺未完成，随本局结束保留在回顾中。'
        epilogues.append(dict(npc_id=npc['id'], name=npc['name'], energy=npc['energy'], mood=npc['mood'], social=npc['social'], text=text))
    world.update(phase='ended', interventions_remaining=0,
                 ending=dict(id=str(uuid4()), title=title, reason=reason, turn=world['turn'], residents=epilogues,
                             bench_repaired=bench['status'] == 'repaired', chat_count=chats, assessment=assessment,
                             festival=deepcopy(world.get('festival'))))
