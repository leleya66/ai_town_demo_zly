"""生成有事实依据的三类规则交流，保存双方结构化记忆，并提供伙伴偏好证据。"""
from copy import deepcopy
from uuid import uuid4
from backend.rules import RULES, PLACES
from backend.world import npc_by_id, record, expression


def partner_evidence(npc, other_id, turn):
    # 只检索已发生且尚在最近六回合内的共同经历；历史情绪不等于当前情绪。
    memories = [m for m in npc.get('social_memories', [])
                if m['partner_id'] == other_id and 0 <= turn-m['turn'] <= 6]
    if not memories:
        return 0, None
    memory = max(memories, key=lambda m: (m['topic'] == 'care', m['turn']))
    return (12 if memory['topic'] == 'care' else 6) + 6-(turn-memory['turn']), memory


def converse(world, snapshot, a_id, b_id, place):
    before = [npc_by_id(snapshot, id) for id in (a_id, b_id)]
    a, b = before
    # 话题依据结算前快照，避免刚获得聊天收益就掩盖交流前的疲惫或低落。
    subject = next((n for n in before if n['mood'] < 45), None)
    if subject is None:
        subject = next((n for n in before if n['energy'] < 50), None)
    if subject:
        other = b if subject is a else a
        metric = 'mood' if subject['mood'] < 45 else 'energy'
        condition = '情绪有些低落' if metric == 'mood' else '有点疲惫'
        topic, label = 'care', '关心近况'
        facts = dict(npc_id=subject['id'], metric=metric, value=subject[metric], observed_turn=snapshot['turn'])
        lines = [(subject, f'我现在{condition}，愿意和你聊一会儿。'), (other, '谢谢你告诉我，我愿意听你说说。')]
    else:
        subject = next((n for n in before if (n.get('last_decision') or {}).get('activity') in ('read', 'work', 'repair_bench', 'sit_bench')), None)
        if subject:
            other = b if subject is a else a
            activity = subject['last_decision']['activity']
            topic, label = 'experience', '分享经历'
            facts = dict(npc_id=subject['id'], activity=activity, place_id=subject['place'], occurred_turn=snapshot['turn'])
            text = f"上一回合我在{PLACES[subject['place']]['name']}{RULES[activity]['label']}。"
            if activity == 'repair_bench':
                bench = snapshot['bench_event']
                facts['progress'] = bench['progress']
                text += f"长椅目前修到了{bench['progress']}/{bench['required']}。"
            lines = [(subject, text), (other, '谢谢你分享，我记住这件事了。')]
        else:
            topic, label, facts = 'greeting', '普通寒暄', {}
            lines = [(a, '你好，见到你很高兴。'), (b, '你好，一起聊一会儿吧。')]
    # 只在 Calm 确实通过观察获知损坏、且双方实际交流时传递需求；不读取全知信息给 Stead。
    calm = next((n for n in before if n['id']=='calm'), None)
    stead = next((n for n in before if n['id']=='stead'), None)
    if calm and stead and calm.get('bench_knowledge') and snapshot['bench_event']['status'] != 'repaired' and not stead.get('bench_intention'):
        topic, label = 'experience', '分享经历·长椅需求'
        facts = dict(need='repair_bench', event_id='forest_bench', npc_id='calm',
                     learned_turn=calm['bench_knowledge']['turn'], source=calm['bench_knowledge']['source'])
        lines = [(calm,'我观察到林间长椅坏了，想恢复这处休息角。你愿意帮忙修好吗？'),
                 (stead,'我听到了你的需求，会根据当前状态和已有承诺决定是否帮忙。')]
    dialogue = ' '.join(f"{n['name']}：{text}" for n, text in lines)
    memory_id = str(uuid4())
    expressions = []
    for self_id, other_id in ((a_id,b_id),(b_id,a_id)):
        npc = npc_by_id(world, self_id)
        memory = dict(id=memory_id, turn=world['turn'], partner_id=other_id, topic=topic,
                      topic_label=label, source='rules', place_id=place, facts=deepcopy(facts), dialogue=dialogue)
        npc.setdefault('social_memories', []).insert(0, memory)
        npc['social_memories'] = npc['social_memories'][:24]
        record(world, npc, f'【规则交流·{label}】{dialogue}', publish=self_id == a_id)
        expressions.append(expression(npc, 'happy', f'规则交流·{label}：{dialogue}', 'npc'))
    return expressions
