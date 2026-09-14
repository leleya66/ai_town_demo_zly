"""管理运行中的世界、版本校验和请求去重；通过原子提交避免重复结算。"""
from copy import deepcopy
from threading import RLock
from backend import storage
from backend.world import fail, update_summary
from backend.agenda import migrate
from backend.decisions import decide
from backend.balance import configure
from backend.ai_mode import describe
from backend.festival import ensure

worlds: dict = {}
lock = RLock()


def get_store(world_id):
    if world_id not in worlds:
        saved = storage.read(world_id)
        if not saved:
            fail(404, '世界不存在，请重新连接。')
        worlds[world_id] = dict(world=saved, requests={})
    enrich(worlds[world_id]['world'])
    return worlds[world_id]


def mutate(world_id, cmd, operation, kind):
    # 去重、版本检查与状态提交在同一临界区执行，业务失败时保留原世界。
    with lock:
        store = get_store(world_id)
        fingerprint = (kind, cmd.model_dump())
        if cmd.request_id in store['requests']:
            old, response = store['requests'][cmd.request_id]
            if old != fingerprint:
                fail(409, '请求 ID 已用于另一项操作。')
            return deepcopy(response)
        if cmd.expected_revision != store['world']['revision']:
            fail(409, '世界状态已变化，请刷新状态后重试。')
        if store['world']['phase'] == 'ended' and kind != 'ai_mode' and not (kind == 'legacy' and getattr(cmd, 'type', '') in ('save', 'load', 'reset', 'save_restart')):
            fail(409, '本局已结束，请查看结局、存档或重新开始。')
        world = deepcopy(store['world'])
        result = operation(world)
        enrich(world)
        world['revision'] = store['world']['revision'] + 1
        store['world'] = world
        response = dict(world=world, result=result)
        store['requests'][cmd.request_id] = (fingerprint, deepcopy(response))
        return response


def enrich(world):
    """统一迁移旧快照并生成预计安排；预测不结算，实际双方匹配在回合推进时进行。"""
    configure(world)
    migrate(world)
    ensure(world)
    update_summary(world)
    world.setdefault('ai_enabled', True)
    world['ai'] = describe(world)
    for npc in world['npcs']:
        npc['agenda_preview'] = decide(world, npc) if world['phase'] == 'playing' else None
