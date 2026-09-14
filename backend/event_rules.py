"""四条专属事件的负责人、场地和计分上限；新局启用，旧档继续使用原规则。"""
EVENTS = {
    'care':dict(owner='joe',title='邻里交流',place='plaza',description='主动关心不同居民，每位实际完成+2'),
    'talk':dict(owner='wise',title='读书分享',place='library',description='准备后广播邀请，每位实际听众+2'),
    'listen':dict(owner='calm',title='倾听接纳',place='forest',description='邀请居民表达，每位实际倾听+2'),
    'bench':dict(owner='stead',title='修好长椅',place='forest',description='两次有效劳动修好+2，每位实际告知+2'),
}
CAP = 6
ACTIVE = ('pending','accepted','deferred')


def modern(world):
    return world.get('festival_version',1) >= 2


def owner_event(npc_id):
    return next(key for key,value in EVENTS.items() if value['owner']==npc_id)
