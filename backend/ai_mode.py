"""管理世界级 AI 开关和公开状态；只返回配置可用性与真实历史结果，不泄露密钥。"""
from backend.commitments import settings
from backend.world import fail


def describe(world):
    config = settings()
    available = bool(config['DASHSCOPE_API_KEY']) and config['LLM_ENABLED'].lower() != 'false'
    enabled = world.get('ai_enabled', True)
    decision = next((n['bench_intention']['commitment_decision'] for n in world['npcs']
                     if n.get('bench_intention', {}).get('commitment_decision')), None)
    status = 'mock' if not enabled else 'ready' if available else 'unavailable'
    return dict(enabled=enabled, available=available, model=config['LLM_MODEL'], thinking=False, status=status,
                last_decision=decision)


def set_mode(world, enabled):
    if enabled and not describe(world)['available']:
        fail(409, 'AI 未启用或服务端未配置密钥，请检查后端配置。')
    # 切换只影响后续新承诺；不清空记忆、重抽旧决定或重复创建待办。
    world['ai_enabled'] = enabled
    return dict(message='AI 模式已开启：自由对话与下一回合活动选择将调用模型。' if enabled else '已切换 Mock，对话和活动选择使用规则。')
