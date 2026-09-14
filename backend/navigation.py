"""定义地图脚底坐标、场景通道与路线时长；为回合结算提供移动路径，不处理人物动画。"""
from math import dist

IDS = ('joe', 'wise', 'calm', 'stead')
SPOTS = {
    'library': [(155,155),(195,155),(240,155),(280,155)],
    'plaza': [(550,190),(580,190),(625,190),(660,190)],
    'forest': [(140,420),(175,420),(205,445),(285,425)],
    'workshop': [(550,465),(585,465),(620,465),(650,465)],
}
# 跨场景依次经过室内通道、入口和公共道路，避免直接穿越建筑。
CORRIDORS = {
    'library': [(195,155),(195,205),(195,270)],
    'plaza': [(600,190),(600,240),(600,270)],
    'forest': [(200,400),(200,325),(200,270)],
    'workshop': [(600,465),(600,350),(600,270)],
}


def destination(npc_id, place, activity=None):
    if activity == 'repair_bench':
        return [250,420]
    if activity == 'sit_bench':
        return [225 + IDS.index(npc_id) * 15, 442]
    return list(SPOTS[place][IDS.index(npc_id)])


def route(npc, target, activity):
    start = npc.get('position', destination(npc['id'], npc['place']))
    end = destination(npc['id'], target, activity)
    if start == end:
        return [start]
    if npc['place'] == target:
        # 同场景只在预留活动地面内移动，无需绕行公共道路。
        points = [start, end]
    else:
        points = [start, *CORRIDORS[npc['place']], *reversed(CORRIDORS[target]), end]
    unique = []
    for point in points:
        if not unique or list(point) != unique[-1]:
            unique.append(list(point))
    return unique


def movement(npc, target, activity):
    points = route(npc, target, activity)
    length = sum(dist(a,b) for a,b in zip(points,points[1:]))
    return dict(npc_id=npc['id'], from_place_id=npc['place'], to_place_id=target,
                points=points, duration_ms=round(length / 130 * 1000))
