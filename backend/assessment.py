"""统一世界评估：居民风险、实际经历与社交倾向分开描述，供近况和终局共同使用。"""
TIRED_ENERGY = 35
LOW_MOOD = 45
QUIET_SOCIAL = 45


def assess_world(world):
    residents = world['npcs']
    tired = [n for n in residents if n['energy'] < TIRED_ENERGY]
    low = [n for n in residents if n['mood'] < LOW_MOOD]
    quiet = [n['name'] for n in residents if n['social'] <= QUIET_SOCIAL]
    warnings = []
    if tired:
        warnings.append('、'.join(f"{n['name']}（精力{n['energy']}）" for n in tired) + '需要休息。')
    if low:
        warnings.append('、'.join(f"{n['name']}（情绪{n['mood']}）" for n in low) + '情绪低落，需要关心。')
    status = '疲惫的小镇' if len(tired) >= 2 else '心事未解' if low else '有人需要歇歇' if tired else '状态平稳'
    # 旧存档缺少统计时显示未知，不能把缺失记录当成没有交流。
    known = world['turn'] == 0 or all('life_stats' in n for n in residents)
    chats = sum(n.get('life_stats', {}).get('chats', 0) for n in residents) // 2 if known else None
    repaired = world['bench_event']['status'] == 'repaired'
    experiences = ['长椅已修好' if repaired else '长椅未修好', f'实际双人交流{chats}次' if chats is not None else '交流次数未记录']
    if status != '状态平稳':
        title = status
        reason = ' '.join(warnings)
    elif repaired:
        title, reason = '守望相助', '居民状态平稳，并共同拥有了修好的林间长椅。'
    elif chats:
        title, reason = '烟火共生', f'居民状态平稳，本局实际发生{chats}次双人交流。'
    elif len(quiet) >= 2:
        title, reason = '各自安宁', '无人明显疲惫或低落，至少两位居民倾向安静独处。'
    else:
        title, reason = '平凡的日子', '居民状态平稳。' + ('本局未修好长椅，也没有双人交流。' if chats == 0 else '已有经历见下方记录。')
    return dict(status=status, reason=' '.join(warnings) if warnings else '所有居民精力至少35、情绪至少45。',
                warnings=warnings, experiences=experiences, quiet_residents=quiet,
                tired_ids=[n['id'] for n in tired], low_mood_ids=[n['id'] for n in low],
                chat_count=chats, bench_repaired=repaired, ending_title=title, ending_reason=reason)
