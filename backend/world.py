"""管理世界初始化、居民查询、状态变化与事件记忆；不负责 HTTP 路由或决策选择。"""
from copy import deepcopy
from uuid import uuid4
from fastapi import HTTPException
from backend.navigation import destination
from backend.rules import DATA, METRICS
from backend.balance import configure, INITIAL_MOODS
from backend.assessment import assess_world


def fail(status, message):
    raise HTTPException(status, detail=message)


def npc_by_id(world, npc_id):
    return next(n for n in world['npcs'] if n['id'] == npc_id)


def fresh_world(world_id, festival_version=2):
    """从唯一初始化数据建立第0回合，清空历史并配置活动规则和脚底坐标。"""
    world = deepcopy(DATA['world'])
    world.update(turn=0, events=[], tasks=[False, False, False], rules_version=2, festival_version=festival_version, invitations=[], max_turns=6, phase='playing', ending=None, ai_enabled=False)
    for npc in world['npcs']:
        npc['mood'] = INITIAL_MOODS[npc['id']]
        npc['life_stats'] = dict(actions={}, chats=0)
        npc['memory'] = []
        npc['messages'] = [dict(role='npc', text=npc['reason'], turn=0)]
    world.update(world_id=world_id, revision=0, interventions_remaining=2, last_decisions=[], last_results=[])
    world.update(bench_event=dict(id='forest_bench', discovered=False, status='broken', progress=0, required=2, assigned_npc_id=None, completed_turn=None), last_movements=[])
    for npc in world['npcs']:
        npc.update(agenda=[], last_decision=None, position=destination(npc['id'], npc['place']))
    configure(world)
    update_summary(world)
    return world


def update_summary(world):
    """小镇近况由后端统一描述；这里只是当前状态概览，尚非游戏结局。"""
    world['assessment'] = world.get('ending', {}).get('assessment') if world.get('ending') else None
    if not world['assessment']:
        world['assessment'] = assess_world(world)
    world['ecology'] = world['ending']['title'] if world.get('ending') else world['assessment']['status']


def record(world, npc, text, publish=True):
    """记忆保留完整行动事实；重复日常不发布到事件列表，重要事件正常发布。"""
    event_id = str(uuid4()) if publish else None
    if publish:
        world['events'].insert(0, dict(id=event_id, turn=world['turn'], npc=npc['id'], text=text))
    world['events'] = world['events'][:80]
    npc['memory'].insert(0, f"第 {world['turn']} 回合：{text}")
    npc['memory'] = npc['memory'][:12]
    return event_id


def apply_effects(npc, values):
    """将属性限制在0至100，返回实际变化量，而非未经截断的理论奖励。"""
    effects = {}
    for metric, delta in zip(METRICS, values):
        before = npc[metric]
        npc[metric] = max(0, min(100, before + delta))
        effects[metric] = npc[metric] - before
    return effects


def message(world, npc, role, text):
    npc['messages'].append(dict(role=role, text=text, turn=world['turn']))
    npc['messages'] = npc['messages'][-30:]


def expression(npc, emotion, reason, source='player'):
    # 表情是本次交流的临时展示事件，不进入永久存档。
    return dict(id=str(uuid4()), npc_id=npc['id'], emotion=emotion, reason=reason, source=source)
