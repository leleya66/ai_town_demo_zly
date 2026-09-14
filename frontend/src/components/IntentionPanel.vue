<!-- 展示后端意图的来源、状态、关联待办和实际结果，不在前端推断记忆是否改变决策。 -->
<script setup lang="ts">
import type { BenchIntention } from '../api';
defineProps<{ intention: BenchIntention }>();
const labels = {pending:'已接受 · 待执行', deferred:'暂缓', in_progress:'修缮中', completed:'已完成', invalid:'已失效', declined:'已拒绝'};
</script>
<template>
 <section class="intention-panel dark-panel" aria-label="长椅个人意图">
  <h3>Stead 的打算 · {{ intention.awaiting_ai ? '待 AI 判断' : labels[intention.status] }}</h3>
  <p><strong>起因：</strong>第{{ intention.source_turn }}回合的长椅需求交流</p>
  <details><summary>查看原始交流</summary><p>{{ intention.origin }}</p></details>
  <p><strong>安排：</strong>{{ intention.reason }}</p>
  <p v-if="intention.commitment_decision"><strong>{{ intention.commitment_decision.source === 'ai' ? 'AI 承诺判断' : '规则承诺判断' }}：</strong>{{ intention.commitment_decision.reason }}</p>
  <p v-if="intention.commitment_decision?.fallback_reason">降级原因：{{ intention.commitment_decision.fallback_reason }}</p>
  <p><strong>实际结果：</strong>{{ intention.outcome }}</p>
  <small>{{ intention.awaiting_ai ? '将在回合选择时一并判断' : intention.commitment_decision?.source === 'ai' ? intention.commitment_decision.model + ' · AI 判断承诺' : '规则模式' }} · 接受帮助不代表立即行动，执行仍由后端规则校验与结算。</small>
 </section>
</template>
<style scoped>
.intention-panel{padding:16px;margin:12px 0;line-height:1.8}.intention-panel h3{color:#edce88;margin:0}small{color:#bfcbbd}summary{cursor:pointer}
</style>
