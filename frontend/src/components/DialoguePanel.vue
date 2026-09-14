<!-- 显示玩家原句、实际语义处理、角色心情和已结算影响，区分模型回复与规则降级。 -->
<script setup lang="ts">
import type { DialogueTrace } from '../api';
defineProps<{ trace: DialogueTrace; name: string }>();
</script>
<template>
 <section class="dialogue-feedback dark-panel" aria-label="对话影响">
  <h3>{{ name }} · {{ trace.source === 'ai' ? 'AI 对话' : 'Mock 对话' }}</h3>
  <p>你说：{{ trace.input }}</p><p>回应：{{ trace.reply }}</p>
  <p v-if="trace.thought">角色心情：{{ trace.thought }}</p>
  <p><strong>实际影响：</strong>{{ trace.effect_summary }}</p>
  <p>情绪 {{ trace.effects.mood >= 0 ? '+' : '' }}{{ trace.effects.mood }} · 社交意愿 {{ trace.effects.social >= 0 ? '+' : '' }}{{ trace.effects.social }} · 精力 {{ trace.effects.energy }}</p>
  <p v-if="trace.fallback_reason">降级：{{ trace.fallback_reason }}</p>
  <details v-if="trace.memory_ids.length"><summary>依据的记忆</summary>{{ trace.memory_ids.join('、') }}</details>
 </section>
</template>
<style scoped>
.dialogue-feedback{padding:14px 18px;margin:10px 0;line-height:1.6;overflow-wrap:anywhere}.dialogue-feedback h3{margin:0;color:#edce88}.dialogue-feedback p{margin:6px 0;font-size:14px}summary{cursor:pointer}
</style>
