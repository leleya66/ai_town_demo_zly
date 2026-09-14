<!-- 展示规则交流的结构化共同记忆；事实与历史时间由后端提供，不推断当前状态。 -->
<script setup lang="ts">
import type { SocialMemory } from '../api';
defineProps<{ memories: SocialMemory[] }>();
</script>
<template>
 <section class="social-memories" aria-label="共同交流记忆">
  <h3>共同交流记忆 · Mock</h3>
  <p v-if="!memories.length">暂无结构化交流记忆；旧记录不会被推测补写。</p>
  <article v-for="memory in memories" :key="memory.id">
   <strong>第{{ memory.turn }}回合 · {{ memory.topic_label }} · 与 {{ memory.partner_id }}</strong>
   <p>{{ memory.dialogue }}</p>
   <small>规则生成 · 历史共同经历，可用于后续伙伴选择，不代表对方当前状态。</small>
  </article>
 </section>
</template>
<style scoped>
article{border-bottom:1px solid #a88c5755;padding:10px 0}small{color:#bfcbbd}
</style>
