<!-- 展示后端返回的 AI 开关、配置状态和最近承诺结果；不把启用状态等同于调用成功。 -->
<script setup lang="ts">
import type { AiStatus } from '../api';
defineProps<{ ai: AiStatus; busy: boolean }>();
</script>
<template>
 <section class="ai-panel dark-panel" aria-label="AI 决策模块" aria-live="polite">
  <div class="ai-heading"><h3>AI 决策模块 · {{ ai.model }} · 非思考模式</h3><strong>{{ !ai.enabled ? 'Mock · 规则模拟' : !ai.available ? 'AI 配置不可用' : 'AI 已启用' }}</strong></div>
  <p v-if="!ai.enabled">Mock：关键词对话与状态评分选择活动，不请求模型。</p>
  <p v-else-if="!ai.available">请检查服务端密钥与启用配置；无法调用时会使用规则降级。</p>
  <p v-else>{{ busy ? '正在处理：模型会理解对话或为居民选择活动，请等待结果。' : 'AI：自由对话影响记忆与待办，推进回合时四位居民基于状态和记忆自主选择。' }}</p>
  <p class="scope">选择居民查看对话影响和上一回合结果。AI提出选择，后端校验、执行、记分；失败时明确降级。</p>
  <details>
   <summary>最近一次承诺判断{{ ai.last_decision ? '' : ' · 尚未发生' }}</summary>
   <template v-if="ai.last_decision">
    <p><strong>{{ ai.last_decision.source === 'ai' ? '真实 AI 调用成功' : ai.last_decision.fallback_reason ? '本次调用已降级' : '规则模拟结果' }}</strong> · {{ ai.last_decision.choice === 'accept' ? '接受承诺' : ai.last_decision.choice === 'defer' ? '暂缓决定' : '拒绝承诺' }}</p>
    <p>{{ ai.last_decision.reason }}</p>
    <p v-if="ai.last_decision.fallback_reason">原因：{{ ai.last_decision.fallback_reason }}</p>
    <small>引用记忆：{{ ai.last_decision.memory_ids.join('、') }}。此处保留历史来源，切换模式不会重做已处理的承诺。</small>
   </template>
   <p v-else>观察林间长椅后，让 Calm 与 Stead 在林间交流，再推进回合。</p>
  </details>
 </section>
</template>
<style scoped>
.ai-panel{padding:14px 18px;margin:12px 0;line-height:1.7;overflow-wrap:anywhere}.ai-heading{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.ai-heading h3{margin:0;color:#edce88}.ai-heading strong{color:#bbd3b7}.ai-panel p{margin:6px 0}.scope,small{color:#bfcbc6;font-size:13px}summary{cursor:pointer;color:#edce88}
</style>
