"""开放日目标、分享配对与贡献账本；只按真实执行记分，支持旧存档和并列最佳居民。"""
from backend.world import fail
from backend.event_rules import modern, EVENTS, CAP


def ensure(world):
    world.setdefault('festival', dict(started_turn=world['turn'], supported_npc_id=None,
                                    prepared_by=[], talk_completed=False, ledger=[]))
    refresh(world)


def support(world, npc_id):
    ensure(world)
    if world['turn'] != 0 or world['festival']['supported_npc_id'] is not None:
        fail(409, '请在第0回合选择一次支持对象；支持不会增加能力或积分。')
    world['festival']['supported_npc_id'] = npc_id
    return dict(message='已选择支持对象，冠军仍由实际贡献决定。')


def refresh(world):
    f = world['festival']
    scores = {n['id']: 0 for n in world['npcs']}
    for entry in f['ledger']:
        scores[entry['npc_id']] += entry['points']
    f['ranking'] = sorted([dict(npc_id=n['id'], name=n['name'], score=scores[n['id']]) for n in world['npcs']], key=lambda row: -row['score'])
    top = max(scores.values())
    f['winners'] = [key for key, value in scores.items() if value == top] if top else []
    f['goals'] = dict(bench=world['bench_event']['status']=='repaired', talk=f['talk_completed'],
                      exchange=any(e['kind']=='exchange' for e in f['ledger']))
    f['success'] = sum(f['goals'].values()) >= 2
    if modern(world):
        f['goals']=dict(care=any(e['kind']=='care' for e in f['ledger']),talk=f['talk_completed'],listen=any(e['kind']=='listen' for e in f['ledger']),bench=world['bench_event']['status']=='repaired')
        f['success']=sum(f['goals'].values())>=2
        f['total_score']=sum(scores.values());f['score_cap']=CAP
        f['cards']=[]
        for key,spec in EVENTS.items():
            entries=[e for e in f['ledger'] if e['npc_id']==spec['owner']]
            invitations=[i for i in world.get('invitations',[]) if i['event']==key]
            stage='尚未发起'
            if key=='talk' and 'wise' in f['prepared_by']:stage='已准备，可以发布邀请'
            if key=='bench':stage=f"修缮 {world['bench_event']['progress']}/{world['bench_event']['required']}" if world['bench_event']['status']!='repaired' else '已修好，可以告知居民'
            if any(i['status'] in ('pending','accepted','deferred') for i in invitations):stage='等待回应或赴约'
            if f['goals'][key]:stage='已产生实际成果，可继续服务其他居民'
            f['cards'].append(dict(id=key,**spec,score=scores[spec['owner']],completed=f['goals'][key],stage=stage,invitations=invitations,ledger=entries))


def credit(world, npc_id, kind, key, points, reason):
    f = world['festival']
    if not any(e['key']==key and e['npc_id']==npc_id for e in f['ledger']):
        if modern(world):points=min(points,max(0,CAP-sum(e['points'] for e in f['ledger'] if e['npc_id']==npc_id)))
        if not points:return
        f['ledger'].append(dict(npc_id=npc_id, kind=kind, key=key, points=points, reason=reason, turn=world['turn']))


def match_talk(world, decisions):
    """主持与听众都选择参加才成立；不匹配则回到阅读，原待办仍保留。"""
    hosts = [d for d in decisions if d['activity']=='host_talk']
    attendees = [d for d in decisions if d['activity']=='attend_talk']
    chosen = hosts[0] if hosts and attendees else None
    for d in hosts + attendees:
        if chosen and (d is chosen or d in attendees):
            d['reason'] += '本回合主持与听众均选择在图书馆参加，分享成立。'
        else:
            d.update(activity='read', agenda_item_id=None, source_action_id=None)
            d['reason'] += '本回合未匹配到主持与听众，改为阅读，分享待办保留。'


def settle(world, snapshot, decisions, completed=()):
    ensure(world)
    if modern(world):
        for d in decisions:
            if d['activity']=='prepare_talk' and d['npc_id']=='wise' and 'wise' not in world['festival']['prepared_by']:
                world['festival']['prepared_by'].append('wise')
        if snapshot['bench_event']['status']!='repaired' and world['bench_event']['status']=='repaired':
            credit(world,'stead','bench','bench-complete',2,'两次有效修缮后长椅实际修好')
        for i in completed:
            if i['event']=='talk':world['festival']['talk_completed']=True
            credit(world,i['sender'],i['event'],i['event']+'-'+i['recipient'],2,f"与{i['recipient']}实际完成{EVENTS[i['event']]['title']}")
        refresh(world)
        return
    for d in decisions:
        who, activity = d['npc_id'], d['activity']
        if activity=='prepare_talk' and who not in world['festival']['prepared_by']:
            world['festival']['prepared_by'].append(who)
        if activity=='host_talk':
            world['festival']['talk_completed'] = True
            credit(world, who, 'talk', 'talk-host', 4, '完成准备并实际主持有听众的读书分享')
        if activity=='attend_talk':
            credit(world, who, 'talk', 'talk-listener', 1, '实际出席读书分享')
        if activity=='repair_bench':
            credit(world, who, 'bench', f"bench-{world['bench_event']['progress']}", 2, '实际完成一次长椅修缮')
        if activity=='chat':
            pair = '-'.join(sorted([who, d['target_npc_id']]))
            credit(world, who, 'exchange', pair, 1, '与该伙伴首次完成有效交流')
            other = next(n for n in snapshot['npcs'] if n['id']==d['target_npc_id'])
            if other['mood'] < 45:
                credit(world, who, 'care', 'care-'+other['id'], 1, '交流中关心结算前情绪低落的伙伴')
    refresh(world)
