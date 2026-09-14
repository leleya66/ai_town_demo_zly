"""将已获知的长椅需求转为个人意图和现有待办；跟踪延期、执行、完成及失效。"""
from uuid import uuid4
from backend.agenda import make_item, MAX_AGENDA
from backend.world import npc_by_id, record
from backend.commitments import choose_commitment


def update_intentions(world, settled=False, defer_ai=False, merged_choice=None):
    npc = npc_by_id(world, 'stead')
    bench = world['bench_event']
    intent = npc.get('bench_intention')
    if not intent:
        memory = next((m for m in npc.get('social_memories', [])
                       if m['partner_id']=='calm' and m.get('facts', {}).get('need')=='repair_bench'
                       and m['turn'] <= world['turn']), None)
        if not memory:
            return
        intent = dict(id=str(uuid4()), owner_id='stead', event_id='forest_bench',
                      source_memory_id=memory['id'], source_turn=memory['turn'], created_turn=world['turn'],
                      status='pending', reason='', agenda_item_id=None, outcome='尚未执行',
                      origin=memory['dialogue'])
        npc['bench_intention'] = intent
        if defer_ai and world.get('ai_enabled',False) and bench['status'] != 'repaired':
            intent['awaiting_ai'] = True
        if bench['status'] != 'repaired':
            # 只在首次收到需求时询问模型，已接受的待办不重新抽签，也不改写玩家承诺。
            choice = None if intent.get('awaiting_ai') else choose_commitment(world, npc, memory)
            if choice is None:
                change(world,npc,intent,'pending','已获知需求，等待下一次回合选择时一并判断是否承诺。')
                return
            intent['commitment_decision'] = choice
            label = 'AI 承诺判断' if choice['source'] == 'ai' else '规则承诺判断'
            record(world,npc,f"【{label}】{choice['reason']}" + (f"（降级：{choice['fallback_reason']}）" if choice['fallback_reason'] else ''))
            if choice['choice'] == 'decline':
                change(world,npc,intent,'declined',choice['reason'])
                return
    if intent.get('awaiting_ai') and bench['status'] != 'repaired':
        if merged_choice is None:
            if world.get('ai_enabled',False):
                return
            memory = next(m for m in npc['social_memories'] if m['id']==intent['source_memory_id'])
            merged_choice = choose_commitment(world,npc,memory)
        intent['commitment_decision'] = merged_choice
        if merged_choice['choice']=='defer':
            change(world,npc,intent,'deferred',merged_choice['reason'])
            return
        intent.pop('awaiting_ai',None)
        record(world,npc,f"【{'AI' if merged_choice['source']=='ai' else '规则降级'}承诺判断】{merged_choice['reason']}")
        if merged_choice['choice']=='decline':
            change(world,npc,intent,'declined',merged_choice['reason'])
            return
    if intent['status'] in ('completed','invalid','declined'):
        return
    decision = npc.get('last_decision') or {}
    executed = settled and decision.get('agenda_item_id') == intent['agenda_item_id'] and intent['agenda_item_id'] is not None
    if bench['status'] == 'repaired':
        if executed:
            intent['outcome'] = f"第{world['turn']}回合实际修缮完成，长椅进度{bench['progress']}/{bench['required']}。"
        change(world,npc,intent,'completed' if executed else 'invalid',
               '实际修缮完成，长椅已恢复。' if executed else '长椅已修好，无需继续履行这项需求。')
        return
    item = next((t for t in npc['agenda'] if t['activity']=='repair_bench'),None)
    if item is None:
        if len(npc['agenda']) >= MAX_AGENDA:
            change(world,npc,intent,'deferred','已有3项待办，先处理承诺；暂不创建新的执行待办。')
            return
        item = make_item('repair_bench','forest',world['turn'],memory_id=intent['source_memory_id'])
        npc['agenda'].append(item)
    # 已有玩家修缮承诺只关联，不复制、不改写其来源或优先级。
    intent['agenda_item_id'] = item['id']
    item['intention_id'] = intent['id']
    if executed:
        intent['outcome'] = f"第{world['turn']}回合实际修缮，长椅进度{bench['progress']}/{bench['required']}。"
        change(world,npc,intent,'in_progress',intent['outcome'])
    elif npc['energy'] < 30:
        change(world,npc,intent,'deferred',f"精力{npc['energy']}/100不足30，先休息，帮助打算保留。")
    elif item['status']=='deferred':
        change(world,npc,intent,'deferred',item['defer_reason'])
    elif item['started']:
        change(world,npc,intent,'in_progress','已经开始修缮，按承诺继续；执行前检查精力。')
    else:
        change(world,npc,intent,'pending','已加入待办，按既有承诺顺序安排；执行前重新检查条件。')


def change(world,npc,intent,status,reason):
    if intent['status'] != status or intent['reason'] != reason:
        intent.update(status=status,reason=reason)
        record(world,npc,f"Stead 的长椅打算：{reason}")
