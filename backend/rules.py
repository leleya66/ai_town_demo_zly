"""集中维护初始世界、活动合法地点、属性效果和居民偏好，作为后端唯一规则来源。"""
import json
from pathlib import Path

DATA = json.loads(Path(__file__).with_name('initial.json').read_text(encoding='utf-8'))
PLACES = DATA['places']
METRICS = ('energy', 'mood', 'social')
RULES = {
    'invite_event': {'places': set(PLACES), 'effects': (-2,1,0), 'label':'发出专属事件邀请'},
    'run_event': {'places': set(PLACES), 'effects': (-4,3,-2), 'label':'开展专属事件'},
    'join_event': {'places': set(PLACES), 'effects': (-3,3,-2), 'label':'赴约参与事件'},
    'prepare_talk': {'places': {'library'}, 'effects': (-6, 2, 2), 'label': '准备读书分享'},
    'host_talk': {'places': {'library'}, 'effects': (-6, 4, -4), 'label': '举办读书分享'},
    'attend_talk': {'places': {'library'}, 'effects': (-3, 3, -2), 'label': '参加读书分享'},
    'seek_company': {'places': {'plaza', 'forest'}, 'effects': (-2, 0, 0), 'label': '寻找伙伴'},
    'rest': {'places': set(PLACES), 'effects': (12, 3, -2), 'label': '休息'},
    'read': {'places': {'library'}, 'effects': (4, 3, -5), 'label': '阅读'},
    'chat': {'places': {'plaza', 'forest'}, 'effects': (-2, 2, -1), 'label': '闲聊'},
    'work': {'places': {'workshop'}, 'effects': (-10, 4, -4), 'label': '修缮'},
    'repair_bench': {'places': {'forest'}, 'effects': (-12, 4, -2), 'label': '修好林间长椅'},
    'sit_bench': {'places': {'forest'}, 'effects': (16, 5, -2), 'label': '长椅休憩'},
}
PREFERRED = {'joe': ('chat', 'plaza'), 'wise': ('read', 'library'), 'calm': ('rest', 'forest'), 'stead': ('work', 'workshop')}
