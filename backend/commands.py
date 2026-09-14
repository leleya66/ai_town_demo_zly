"""处理对话、观察、陪伴及存档命令；复用统一建议规则，不在接口中重复结算。"""
from copy import deepcopy
import sqlite3
from backend import storage
from backend.agenda import migrate
from backend.models import Suggestion
from backend.decisions import submit_suggestion
from backend.rules import PLACES
from backend.world import npc_by_id, fail, message, record, expression, fresh_world
from uuid import uuid4


def execute_command(world, cmd, rule_only=False):
    if cmd.type != 'message':
        return _execute_command(world,cmd)
    if not cmd.npc_id:
        fail(422,'需要指定居民。')
    if not cmd.text.strip():
        fail(422,'消息不能为空。')
    if world['interventions_remaining'] <= 0:
        fail(409,'本回合两次干预机会已用完，请推进回合。')
    npc = npc_by_id(world,cmd.npc_id)
    if world.get('ai_enabled',False) and not rule_only:
        from backend.dialogue import talk
        return talk(world,npc,cmd.text.strip())
    before = world['interventions_remaining']
    result = _execute_command(world,cmd)
    if world['interventions_remaining']==before:
        world['interventions_remaining'] -= 1
    reply = npc['messages'][-1]['text']
    trace = dict(source='rules',input=cmd.text,reply=reply,thought='',intent='keyword',
                 effects=dict(energy=0,mood=0,social=0),effect_summary=result.get('reason','固定角色回复，未改变待办'),
                 fallback_reason='',memory_ids=[])
    npc['last_dialogue'] = trace
    npc.setdefault('dialogue_memories',[]).insert(0,dict(id=str(uuid4()),turn=world['turn'],player_input=cmd.text,
                                                     reply=reply,result=trace['effect_summary']))
    npc['dialogue_memories'] = npc['dialogue_memories'][:16]
    return {**result,'dialogue':trace}


def _execute_command(world, cmd):
    world_id = world['world_id']
    npc = npc_by_id(world, cmd.npc_id) if cmd.npc_id else None
    if cmd.type in ('message', 'interact') and not npc:
        fail(422, '需要指定居民。')
    if cmd.type == 'message':
        text = cmd.text.strip()
        if not text:
            fail(422, '消息不能为空。')
        if any(word in text for word in ('休息', '累', '歇')):
            result = submit_suggestion(world, Suggestion(**cmd.model_dump(exclude={'type', 'place_id', 'text', 'save_id'}), type='suggest_activity', activity='rest', target_place_id='forest'))
            if npc['id'] in ('wise', 'calm'):
                world['tasks'][0 if npc['id'] == 'wise' else 1] = True
            return result
        reply = {'joe':'和你聊天真开心！', 'wise':'谢谢你愿意认真听，我想再读一会儿。', 'calm':'谢谢你的陪伴，我喜欢这里的安静。', 'stead':'把眼前的事情做好，心里自然踏实。'}[npc['id']]
        message(world, npc, 'user', text)
        message(world, npc, 'npc', reply)
        record(world, npc, f"你对 {npc['name']} 说：“{text}”")
        if npc['id'] in ('wise', 'calm'):
            world['tasks'][0 if npc['id'] == 'wise' else 1] = True
        return dict(message='操作完成', expressions=[expression(npc, 'happy' if npc['id'] == 'joe' else 'warm', reply)])
    elif cmd.type == 'observe':
        if not cmd.place_id:
            fail(422, '需要指定地点。')
        if cmd.place_id == 'forest' and world['bench_event']['status'] != 'repaired':
            calm = npc_by_id(world, 'calm')
            if calm['place'] == 'forest':
                calm.setdefault('bench_knowledge', dict(turn=world['turn'], source='共同观察林间长椅'))
        if cmd.place_id == 'forest' and not world['bench_event']['discovered']:
            world['bench_event']['discovered'] = True
            record(world, npc_by_id(world, 'calm'), '发现林间长椅的木板断裂了。Calm 希望恢复这处休息角，可以邀请 Stead 修缮，需要两个有效劳动回合。')
        resident = next((n for n in world['npcs'] if n['place'] == cmd.place_id), None)
        if resident:
            record(world, resident, f"你观察了{PLACES[cmd.place_id]['name']}。")
        if cmd.place_id == 'plaza':
            world['tasks'][2] = True
    elif cmd.type == 'interact':
        record(world, npc, f"你陪伴了 {npc['name']}，没有打断对方的活动。")
    elif cmd.type in ('save', 'save_restart'):
        replacement = fresh_world(world_id) if cmd.type == 'save_restart' else None
        snapshot = deepcopy(world)
        snapshot['revision'] += 1
        try:
            storage.save(snapshot)
        except storage.SaveLimitReached:
            fail(409, '存档已达10条上限，请先在存档列表手动删除旧存档。')
        except (OSError, sqlite3.Error):
            fail(503, '存档写入失败，请检查磁盘空间或目录权限后重试。')
        if replacement is not None:
            world.clear()
            world.update(replacement)
            return {'message': '已保存上一局并开始新游戏。'}
        return {'message': f"已存档：第 {world['turn']} 回合。"}
    elif cmd.type == 'load':
        saved = storage.read(cmd.save_id or world_id)
        if not saved:
            fail(409, '还没有手动存档。')
        world.clear()
        world.update(deepcopy(saved))
        world['world_id'] = world_id
        migrate(world)
    elif cmd.type == 'reset':
        world.clear()
        world.update(fresh_world(world_id))
    return {'message': '操作完成'}
