"""统一推进回合：校验双人计划、生成移动路线、结算属性和长椅事件，并记录交流。"""
from copy import deepcopy
from uuid import uuid4
from backend.decisions import decide
from backend.agenda import reconcile, settle_agenda
from backend.balance import action_effects
from backend.endings import finish_if_due
from backend.intentions import update_intentions
from backend.social import match_social
from backend.conversations import converse
from backend.rules import PLACES, RULES
from backend.models import ActionResult
from backend.navigation import destination, movement
from backend.world import npc_by_id, apply_effects, record
from backend.agent_decisions import choose_all
from backend.festival import ensure, match_talk, settle
from backend.streaming import emit
from backend.commitments import choose_commitment
from backend.event_rules import modern
from backend import invitations


def advance_world(world):
    ensure(world)
    if modern(world):invitations.expire(world)
    reconcile(world)
    update_intentions(world, defer_ai=True)
    snapshot = deepcopy(world)
    decisions = choose_all(snapshot)
    # 长椅承诺包含在Stead同一次选择中；失败只本地降级，不发起额外模型请求。
    stead = npc_by_id(world,'stead')
    intent = stead.get('bench_intention') or {}
    if intent.get('awaiting_ai'):
        decision = next(d for d in decisions if d['npc_id']=='stead')
        choice = decision.pop('bench_commitment',None)
        if choice is None:
            memory = next(m for m in stead['social_memories'] if m['id']==intent['source_memory_id'])
            choice = choose_commitment({**world,'ai_enabled':False},stead,memory)
            choice['fallback_reason'] = decision.get('fallback_reason','未得到有效AI承诺')
        update_intentions(world, defer_ai=True, merged_choice=choice)
        if choice['choice']=='accept' and decision['activity']=='repair_bench':
            decision['agenda_item_id'] = intent.get('agenda_item_id')
    emit('progress', message='居民选择已返回，正在校验配对并结算')
    match_social(snapshot, decisions)
    completed=invitations.resolve(world,decisions) if modern(world) else []
    if not modern(world):match_talk(snapshot, decisions)
    # 世界由后端一次性结算，前端随后只回放路线，不再次计算属性。
    world['turn'] += 1
    results = []
    movements = []
    for d in decisions:
        npc = npc_by_id(world, d['npc_id'])
        origin = npc['place']
        movements.append(movement(npc, d['target_place_id'], d['activity']))
        npc.update(place=d['target_place_id'], action=RULES[d['activity']]['label'], reason=d['reason'], last_decision=d, rest=False)
        if d['activity'] == 'chat':
            npc['last_chat_turn'] = world['turn']
        npc['position'] = destination(npc['id'], npc['place'], d['activity'])
        values, notes = action_effects(world, npc, d['activity'])
        effects = apply_effects(npc, values)
        if d['activity'] == 'repair_bench':
            bench = world['bench_event']
            bench['assigned_npc_id'] = npc['id']
            bench['progress'] = min(bench['required'], bench['progress'] + 1)
            bench['status'] = 'repaired' if bench['progress'] == bench['required'] else 'repairing'
            if bench['status'] == 'repaired':
                bench['completed_turn'] = world['turn']
                record(world, npc, '林间长椅修好了！所有居民现在可以使用长椅休憩。')
                calm = npc_by_id(world, 'calm')
                record(world, calm, 'Stead 修好了林间长椅，我又有一处安静休憩的地方。')
            else:
                record(world, npc, f"长椅修缮进度 {bench['progress']}/{bench['required']}：固定了支架，下回合继续铺好木板。")
        settle_agenda(world, snapshot, npc, d)
        before = npc_by_id(snapshot, npc['id'])
        previous = (before.get('last_decision') or {}).get('activity')
        changed = before['place'] != npc['place'] or previous != d['activity']
        # 每位居民仍有完整行动结果；相同地点重复同一活动不刷屏。
        event_id = record(world, npc, f"{npc['name']} 在{PLACES[npc['place']]['name']}{npc['action']}。{d['reason']}", publish=changed)
        results.append(ActionResult(npc_id=npc['id'], agenda_item_id=d['agenda_item_id'], activity=d['activity'], from_place_id=origin, to_place_id=npc['place'], status='completed', effects=effects, event_id=event_id, notes=notes).model_dump())
        npc.setdefault('action_memories',[]).insert(0,dict(id=str(uuid4()),turn=world['turn'],activity=d['activity'],
                                                         place=npc['place'],effects=effects,result='实际执行完成'))
        npc['action_memories'] = npc['action_memories'][:12]
    # 每对有效交流只生成一次双人对话，分别写入双方记忆并返回临时气泡。
    expressions = []
    for d in decisions:
        if d['activity'] != 'chat' or d['npc_id'] > d['target_npc_id']:
            continue
        expressions.extend(converse(world, snapshot, d['npc_id'], d['target_npc_id'], d['target_place_id']))
    world.update(last_decisions=decisions, last_results=results, last_movements=movements, interventions_remaining=2)
    update_intentions(world, settled=True, defer_ai=True)
    if modern(world):invitations.finish(world,decisions,completed)
    settle(world,snapshot,decisions,completed)
    finish_if_due(world)
    return dict(decisions=decisions, results=results, movements=movements, expressions=expressions)
