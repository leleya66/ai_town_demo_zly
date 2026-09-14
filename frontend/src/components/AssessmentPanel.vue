<!-- 同一套居民状态、风险提示与经历标签用于世界近况和结局，避免平均值掩盖个体。 -->
<script setup lang="ts">
import type { Assessment } from '../api';
defineProps<{ assessment: Assessment }>();
</script>
<template>
 <section class="assessment-panel" aria-label="世界评估">
  <h3>居民状态 · {{ assessment.status }}</h3>
  <ul v-if="assessment.warnings.length"><li v-for="warning in assessment.warnings" :key="warning">{{ warning }}</li></ul>
  <p v-else>{{ assessment.reason }}</p>
  <p class="assessment-tags"><span v-for="experience in assessment.experiences" :key="experience">{{ experience }}</span></p>
  <small>社交倾向：{{ assessment.quiet_residents.length ? assessment.quiet_residents.join('、') + '的社交意愿较低' : '目前没有社交意愿较低的居民' }}。这不代表状态好坏。</small>
 </section>
</template>
<style scoped>
.assessment-panel{line-height:1.8;margin:12px 0}.assessment-panel h3{font-size:17px!important;margin:6px 0}.assessment-panel ul{padding-left:20px;color:#f0c18e}.assessment-tags{display:flex;flex-wrap:wrap;gap:8px}.assessment-tags span{border:1px solid #a88c5777;border-radius:4px;padding:3px 9px;font-size:13px}.assessment-panel small{color:#bfcbbd}
</style>
