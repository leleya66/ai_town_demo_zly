<!-- 展示后端冻结的六回合结局与居民后记；保存成功后才能重开，不在前端判定结局。 -->
<script setup lang="ts">
import { ref } from 'vue';
import AssessmentPanel from './AssessmentPanel.vue';
import FestivalPanel from './FestivalPanel.vue';
import type { Assessment, Ending } from '../api';
const props = defineProps<{ ending: Ending; assessment: Assessment; busy: boolean; restart: (save: boolean) => Promise<boolean> }>();
const emit = defineEmits<{ saves: [] }>();
const error = ref('');
async function start(save: boolean) {
 error.value = '';
 if (!await props.restart(save)) error.value = '操作未完成，当前结局已保留。若存档已满，请先管理存档再试。';
}
</script>
<template>
 <section class="ending-panel" aria-label="六回合结局">
  <small>第 {{ ending.turn }} 回合 · 游戏结束 · 结局依据实际状态与事件评定</small>
  <h3>{{ ending.title }}</h3><p>{{ ending.reason }}</p>
  <FestivalPanel v-if="ending.festival" :festival="ending.festival" :turn="ending.turn" :ended="true" :busy="busy"/>
  <AssessmentPanel :assessment="ending.assessment || assessment"/>
  <article v-for="resident in ending.residents" :key="resident.npc_id">
   <strong>{{ resident.name }}</strong><p>精力 {{ resident.energy }} · 情绪 {{ resident.mood }} · 社交意愿 {{ resident.social }}</p><p>{{ resident.text }}</p>
  </article>
  <p>可关闭此窗口继续回顾。是否保存本局后再开始？</p>
  <p v-if="error" role="alert">{{ error }}</p>
  <div class="ending-buttons"><button :disabled="busy" @click="start(true)">存档并重新开始</button><button :disabled="busy" @click="start(false)">不存档，重新开始</button><button :disabled="busy" @click="emit('saves')">管理存档</button></div>
 </section>
</template>
<style scoped>
.ending-panel{padding:0 24px 24px;line-height:1.8}.ending-panel h3{font-size:27px;color:#edce88;margin:8px 0}.ending-panel article{border-top:1px solid #a88c5755;padding:12px 0}.ending-panel article p{margin:4px 0}.ending-buttons{display:flex;gap:10px;flex-wrap:wrap}.ending-buttons button{padding:10px;border:1px solid #ab915c;border-radius:4px}.ending-panel [role=alert]{color:#ffce9e}
</style>
