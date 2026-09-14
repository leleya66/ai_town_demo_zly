"""统一检查活动硬约束；状态不足可暂缓，失效事件则关闭待办，不包含人格偏好。"""
from backend.rules import PLACES, RULES
from backend.event_rules import modern, EVENTS, owner_event


def partner(world, npc, place):
    return next((n for n in world['npcs'] if n['id'] != npc['id']
                 and (n['place'] == place or any(t['activity'] == 'chat' and t['target_place_id'] == place
                      and (t['expires_at_turn'] is None or t['expires_at_turn'] >= world['turn'] + 1)
                      for t in n.get('agenda', [])))
                 and n['energy'] >= 30 and n['social'] >= 35 and n['mood'] >= 40), None)


def blocked(world, npc, activity, place):
    """返回（永久失效，真实原因）；None 表示当前硬条件允许，双方最终计划另行匹配。"""
    if place not in RULES[activity]['places']:
        return True, '该地点不支持这项活动。'
    bench = world['bench_event']
    if modern(world):
        if activity in ('prepare_talk','host_talk') and npc['id']!='wise':
            return True,'读书分享由Wise准备和主持，其他居民可以作为听众。'
        if activity in ('invite_event','run_event','join_event','host_talk','attend_talk'):
            from backend.invitations import choices
            if not any(c['activity']==activity and c['place']==place for c in choices(world,npc)):
                return False,'当前没有该地点的有效邀请或尚未满足专属事件前提。'
    elif activity in ('invite_event','run_event','join_event'):
        return True,'旧局保留原玩法，新游戏启用四条事件路线。'
    if activity in ('prepare_talk', 'host_talk', 'attend_talk'):
        festival = world.get('festival', {})
        if festival.get('talk_completed') and not modern(world):
            return True, '本局读书分享已经完成。'
        if activity=='prepare_talk' and npc['id'] in festival.get('prepared_by', []):
            return True, '我已完成分享准备，可以邀请听众参加。'
        if activity=='host_talk' and npc['id'] not in festival.get('prepared_by', []):
            return False, '需要先完成一次分享准备。'
    if activity == 'repair_bench':
        if bench['status'] == 'repaired':
            return True, '林间长椅已经修好了，不需要重复修缮。'
        if not bench['discovered']:
            return True, '先去林间观察长椅，确认需要修缮的地方吧。'
        if npc['id'] != 'stead':
            return True, '我不擅长木工修缮，这件事更适合请 Stead 帮忙。'
    if activity == 'sit_bench' and bench['status'] != 'repaired':
        return False, '长椅还没修好，暂时不能坐下使用。'
    if activity != 'rest' and npc['energy'] < 30:
        return False, f"现在精力不足（{npc['energy']}/100，活动至少需要30），先休息。"
    if activity in ('chat', 'seek_company'):
        if npc['social'] < 35 or npc['mood'] < 40:
            return False, f"我的社交意愿{npc['social']}/100、情绪{npc['mood']}/100未达到闲聊门槛35和40。"
        if activity == 'chat' and not partner(world, npc, place):
            return False, f"{PLACES[place]['name']}没有符合条件的交流对象。"
    return None
