"""管理最多三项有效待办、旧存档迁移、期限与执行后状态；关闭项目写入事件而不无限堆积。"""
from uuid import uuid4
from backend.rules import RULES, PLACES
from backend.eligibility import blocked
from backend.world import record

MAX_AGENDA = 3


def make_item(activity, place, turn, source_id=None, memory_id=None, started=False):
    return dict(id=str(uuid4()), activity=activity, target_place_id=place,
                event_id='forest_bench' if activity == 'repair_bench' else None,
                accepted_turn=turn, expires_at_turn=turn + 3 if activity == 'chat' else None,
                source_action_id=source_id, memory_id=memory_id, started=started,
                status='in_progress' if started else 'pending', defer_reason='')


def migrate(world):
    """只在读取旧格式时转换一次；保留旧建议与已开始的长椅，不运行旧调度逻辑。"""
    for npc in world['npcs']:
        old = npc.pop('pending_suggestion', None)
        if 'agenda' in npc:
            continue
        npc['agenda'] = []
        if old:
            item = make_item(old['activity'], old['target_place_id'], old['expires_after_turn'] - 1,
                             old.get('source_action_id'), old.get('memory_id'))
            npc['agenda'].append(item)
        bench = world['bench_event']
        if bench['status'] == 'repairing' and bench['assigned_npc_id'] == npc['id']:
            repair = next((t for t in npc['agenda'] if t['activity'] == 'repair_bench'), None)
            if repair:
                repair.update(started=True, status='in_progress')
            else:
                npc['agenda'].append(make_item('repair_bench', 'forest', None, started=True))
    world['agenda_version'] = 1


def close_item(world, npc, item, status, reason):
    npc['agenda'].remove(item)
    record(world, npc, f"{npc['name']} 的待办「{RULES[item['activity']]['label']}」{status}：{reason}")


def reconcile(world):
    # 执行下一回合前清理过期或永久失效事项；暂时受阻继续占用待办名额。
    for npc in world['npcs']:
        for item in list(npc['agenda']):
            expiry = item['expires_at_turn']
            if expiry is not None and expiry < world['turn'] + 1:
                close_item(world, npc, item, '已过期', f'邀请有效至第{expiry}回合，需重新邀请。')
                continue
            constraint = blocked(world, npc, item['activity'], item['target_place_id'])
            if constraint and constraint[0]:
                close_item(world, npc, item, '已取消', constraint[1])


def settle_agenda(world, snapshot, npc, decision):
    """只完成真正执行的待办；劳动未完保留，休息或配对失败不冒充履约。"""
    before = next(n for n in snapshot['npcs'] if n['id'] == npc['id'])
    for item in list(npc['agenda']):
        if item['id'] == decision.get('agenda_item_id'):
            if item['activity'] == 'repair_bench' and world['bench_event']['status'] != 'repaired':
                item.update(started=True, status='in_progress', defer_reason='')
            else:
                close_item(world, npc, item, '已完成', f"第{world['turn']}回合实际执行。")
        else:
            constraint = blocked(snapshot, before, item['activity'], item['target_place_id'])
            reason = constraint[1] if constraint else f"本回合选择{PLACES[decision['target_place_id']]['name']}{RULES[decision['activity']]['label']}。{decision['reason']}"
            item.update(status='deferred', defer_reason=reason)
