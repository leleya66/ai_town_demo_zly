"""规则模式的自主偏好：接受意愿与待办排序；未来模型可替换选择，不能绕过硬约束。"""
from backend.rules import PREFERRED


def preference_refusal(npc, activity):
    if activity == 'rest' and npc['energy'] >= 85:
        return f"我现在精力为{npc['energy']}/100，暂时不想休息；已有承诺仍会保留。"
    if activity == 'read' and npc['id'] == 'joe' and npc['social'] >= 60:
        return f"我现在社交意愿为{npc['social']}/100，更想和人交流，还静不下心来阅读。"
    if activity == 'work' and npc['id'] in ('wise', 'calm'):
        return '修缮不是我现在想做的事，我更愿意阅读或休整。'
    return None


def ranked(npc, items):
    """先已开始、再较早承诺；同回合按当前需求与偏好，最后按入队顺序稳定排序。"""
    def rank(pair):
        index, item = pair
        activity = item['activity']
        wanted = (activity == 'rest' and npc['energy'] < 50) or activity == PREFERRED[npc['id']][0]
        wanted = wanted or (npc['id'] == 'stead' and activity == 'repair_bench')
        return (not item['started'], item['accepted_turn'] if item['accepted_turn'] is not None else -1, not wanted, index)
    return [item for _, item in sorted(enumerate(items), key=rank)]
