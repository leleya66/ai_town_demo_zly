"""统一邀请、回应、到期配对和结果记忆；广播不强迫赴约，重复对象不重复创建活跃邀请。"""
from uuid import uuid4
from backend.event_rules import EVENTS, ACTIVE, modern, owner_event
from backend.agenda import make_item, MAX_AGENDA
from backend.world import record, npc_by_id


def ensure(world):
    world.setdefault('invitations',[])


def known(world,npc):
    return [i for i in world.get('invitations',[]) if npc['id'] in (i['sender'],i['recipient'])][-12:]


def ready(world,event):
    if event=='talk':return 'wise' in world.get('festival',{}).get('prepared_by',[])
    if event=='bench':return world['bench_event']['status']=='repaired'
    return True


def actions(event):
    return ('host_talk','attend_talk') if event=='talk' else ('run_event','join_event')


def remember(world,invite,text):
    for who in (invite['sender'],invite['recipient']):
        npc=npc_by_id(world,who)
        record(world,npc,text)
        npc.setdefault('invitation_memories',[]).insert(0,dict(id=str(uuid4()),turn=world['turn'],invitation_id=invite['id'],result=text))
        npc['invitation_memories']=npc['invitation_memories'][:12]


def expire(world):
    ensure(world)
    for i in world['invitations']:
        if i['status'] in ACTIVE and i['expires_turn'] < world['turn']+1:
            i.update(status='expired',result='邀请已过期，未完成不计分')
            remember(world,i,f"{EVENTS[i['event']]['title']}邀请已过期，{i['recipient']}未完成赴约，不计分。")
    for npc in world['npcs']:
        npc['agenda'][:]=[t for t in npc['agenda'] if not t.get('invitation_group') or any(i['group']==t['invitation_group'] and npc['id'] in (i['sender'],i['recipient']) and i['status'] in ACTIVE for i in world['invitations'])]


def targets(world,npc,event):
    return [n['id'] for n in world['npcs'] if n['id']!=npc['id']
            and not any(i['event']==event and i['recipient']==n['id'] and (i['status'] in ACTIVE or i['status']=='completed') for i in world.get('invitations',[]))]


def choices(world,npc):
    """显式候选含邀请ID、对象和地点，不让模型凭空创造参与者。"""
    if not modern(world) or npc['energy']<30:return []
    result=[]; event=owner_event(npc['id']);spec=EVENTS[event]
    if ready(world,event) and sum(t['activity']!='invite_event' for t in npc['agenda'])<MAX_AGENDA and targets(world,npc,event) and (world.get('max_turns') is None or world['turn']+2<=world['max_turns']):
        for target in ([None] if event=='talk' else targets(world,npc,event)):
            result.append(dict(activity='invite_event',place=spec['place'],target_npc_id=target,event=event,invitation_id=None))
    seen=set()
    for i in known(world,npc):
        if i['status'] not in ACTIVE or i['due_turn']>world['turn']+1 or i['expires_turn']<world['turn']+1:continue
        hosting=i['sender']==npc['id'];activity=actions(i['event'])[0 if hosting else 1]
        if hosting and i['group'] in seen:continue
        if len(npc['agenda'])>=MAX_AGENDA and not any(t.get('invitation_group')==i['group'] for t in npc['agenda']):continue
        result.append(dict(activity=activity,place=i['place'],target_npc_id=i['recipient'] if hosting else i['sender'],event=i['event'],invitation_id=i['id']))
        if hosting:seen.add(i['group'])
    return result


def rule_choice(world,npc,current):
    """Mock使用固定优先级：照顾精力、已有明确承诺、已发邀请、收到邀请、自身事件。"""
    if not modern(world):return current
    candidates=choices(world,npc)
    chosen=None
    task=next((t for t in npc['agenda'] if t['id']==current.get('agenda_item_id')),None)
    if npc['energy']>=30:
        if task and not task.get('invitation_group'):
            chosen=next((c for c in candidates if c['activity']==task['activity'] and (not task.get('invitation_group') or any(i['id']==c.get('invitation_id') and i['group']==task['invitation_group'] for i in world['invitations']))),None)
        else:
            scheduled=[c for c in candidates if c.get('invitation_id')]
            def order(c):
                i=next(i for i in world['invitations'] if i['id']==c['invitation_id'])
                return (i['due_turn'],('talk','care','listen','bench').index(i['event']),i['group'])
            chosen=min(scheduled,key=order) if scheduled else next(iter(candidates),None)
            if not chosen and npc['id']=='wise' and 'wise' not in world.get('festival',{}).get('prepared_by',[]):
                chosen=dict(activity='prepare_talk',place='library',invitation_id=None,target_npc_id=None)
            if not chosen and npc['id']=='stead' and world['bench_event']['discovered'] and world['bench_event']['status']!='repaired':
                chosen=dict(activity='repair_bench',place='forest',invitation_id=None,target_npc_id=None)
    if chosen:
        current.update(activity=chosen['activity'],target_place_id=chosen['place'],target_npc_id=chosen.get('target_npc_id'),invitation_id=chosen.get('invitation_id'),
                       reason='按当前精力、已有承诺与有效邀请安排专属事件。',related_memory_ids=[])
    current['invitation_replies']=[dict(invitation_id=i['id'],response='accept' if current.get('invitation_id')==i['id'] else 'defer',
                                    reason='本回合可以赴约' if current.get('invitation_id')==i['id'] else '本回合优先处理其他安排或恢复精力')
                                  for i in known(world,npc) if i['recipient']==npc['id'] and i['status'] in ACTIVE]
    return current


def schedule(npc,invite,hosting,turn):
    existing=next((t for t in npc['agenda'] if t.get('invitation_group')==invite['group']),None)
    if existing:return existing
    if len(npc['agenda'])>=MAX_AGENDA:return None
    item=make_item(actions(invite['event'])[0 if hosting else 1],invite['place'],turn)
    item.update(invitation_group=invite['group'],invitation_id=invite['id'],scheduled_turn=invite['due_turn'],expires_at_turn=invite['expires_turn'])
    npc['agenda'].append(item)
    return item


def issue(world,decision):
    sender=npc_by_id(world,decision['npc_id']);event=owner_event(sender['id'])
    if not ready(world,event):return
    candidates=targets(world,sender,event)
    if event!='talk':candidates=[decision.get('target_npc_id')] if decision.get('target_npc_id') in candidates else candidates[:1]
    if not candidates or len(sender['agenda'])>=MAX_AGENDA:return
    group=str(uuid4())
    for target in candidates:
        i=dict(id=str(uuid4()),group=group,event=event,sender=sender['id'],recipient=target,
               place=EVENTS[event]['place'],created_turn=world['turn'],due_turn=world['turn']+1,
               expires_turn=min(world['turn']+2,world.get('max_turns') or world['turn']+2),status='pending',response_reason='',response_source='',result='等待回应')
        world['invitations'].append(i)
        schedule(sender,i,True,world['turn'])
        remember(world,i,f"{sender['name']}邀请{target}第{i['due_turn']}回合到{EVENTS[event]['place']}参与{EVENTS[event]['title']}，等待对方自主回应。")


def resolve(world,decisions):
    """先写入真实回应，再匹配双方本回合选择；未到场只暂缓，不结算互动。"""
    by_id={d['npc_id']:d for d in decisions}
    for d in decisions:
        npc=npc_by_id(world,d['npc_id']);selected=d.get('invitation_id')
        if selected and not any(c.get('invitation_id')==selected and c['activity']==d['activity'] and c['place']==d['target_place_id'] for c in choices(world,npc)):
            d.update(activity='rest',target_place_id=npc['place'],invitation_id=None,agenda_item_id=None,source_action_id=None)
            d['reason']+=' 邀请或活动条件已不合法，未执行赴约。'
            selected=None
        replies={r['invitation_id']:r for r in d.pop('invitation_replies',[])}
        for i in known(world,npc):
            if i['recipient']!=npc['id'] or i['status'] not in ACTIVE:continue
            reply=replies.get(i['id'])
            if selected==i['id']:reply=dict(response='accept',reason=d['reason'])
            if not reply:continue
            status={'accept':'accepted','decline':'declined','defer':'deferred'}[reply['response']]
            if status=='accepted' and schedule(npc,i,False,world['turn']) is None:
                status='deferred';reply=dict(reason='已有3项待办，暂时无法承诺')
            changed=i['status']!=status or i['response_reason']!=reply['reason']
            i.update(status=status,response_reason=reply['reason'],response_source=d['source'])
            if changed:remember(world,i,f"{npc['name']}对{EVENTS[i['event']]['title']}邀请回应：{status}。{reply['reason']}")
    completed=[];matched=set()
    for i in world['invitations']:
        if i['status']!='accepted' or not(i['due_turn']<=world['turn']+1<=i['expires_turn']):continue
        host=by_id[i['sender']];guest=by_id[i['recipient']]
        host_i=next((x for x in world['invitations'] if x['id']==host.get('invitation_id')),None)
        if not host_i or host_i['group']!=i['group'] or guest.get('invitation_id')!=i['id']:continue
        if (host['activity'],guest['activity'])!=actions(i['event']):continue
        if host['target_place_id']!=i['place'] or guest['target_place_id']!=i['place']:continue
        i.update(status='completed',result='双方实际到场并完成互动',completed_turn=world['turn']+1)
        completed.append(i);matched.update([i['sender'],i['recipient']])
        for d in (host,guest):
            item=schedule(npc_by_id(world,d['npc_id']),i,d is host,world['turn'])
            d['agenda_item_id']=item['id'] if item else None
            d['reason']+=' 双方已匹配，本回合完成约定互动。'
    for d in decisions:
        if d['activity'] in ('host_talk','attend_talk','run_event','join_event') and d['npc_id'] not in matched:
            d.update(activity='read' if d['target_place_id']=='library' else 'rest',agenda_item_id=None,source_action_id=None)
            d['reason']+=' 对方未在本回合赴约，未完成互动、不计分，未过期邀请保留。'
    return completed


def finish(world,decisions,completed):
    for i in completed:
        remember(world,i,f"第{world['turn']}回合，{i['sender']}与{i['recipient']}实际完成{EVENTS[i['event']]['title']}。")
    for d in decisions:
        if d['activity']=='invite_event':issue(world,d)
