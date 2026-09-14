<!-- 展示后端四条专属事件的阶段、分数与完成情况，点击定位负责人，不在前端结算。 -->
<script setup lang="ts">
import type {EventCard} from '../api';
import type {NpcId} from '../world';
const npcNames:Record<NpcId,string>={joe:'Joe',wise:'Wise',calm:'Calm',stead:'Stead'};
defineProps<{cards:EventCard[]}>();
defineEmits<{select:[id:NpcId]}>();
</script>
<template>
 <div class="event-tasks"><div class="quest-heading"><span>四条专属事件</span><small>{{ cards.filter(c=>c.completed).length }} / 4</small></div>
  <button v-for="card in cards" :key="card.id" class="event-task" @click="$emit('select',card.owner)">
   <strong>{{ card.completed?'✓':'○' }} {{ npcNames[card.owner] }} · {{ card.title }}</strong>
   <span>{{ card.score }} / 6 分 · {{ card.stage }}</span><small>{{ card.description }}</small>
  </button>
 </div>
</template>
<style scoped>
.event-task{display:flex;flex-direction:column;text-align:left;gap:5px;width:100%;padding:13px 4px;border-bottom:1px solid #9b805550;color:#34413b}.event-task strong{font-size:14px}.event-task span,.event-task small{font-size:11px;line-height:1.6}.event-task:hover{background:#fff3}.quest-heading{display:flex;justify-content:space-between}
</style>
