<!-- 显示真实流式进度及未校验的回复草稿，不将生成中的文案当成已执行结果。 -->
<script setup lang="ts">
defineProps<{status:string;draft:string;input:string}>();
</script>
<template>
 <aside v-if="status" class="stream-panel" aria-label="实时生成进度" role="status">
  <strong>{{ status }}</strong><p v-if="input">你说：{{ input }}</p>
  <p v-if="draft" class="stream-draft">{{ draft }}</p>
  <small v-if="draft">生成中 · 待后端校验，尚未写入属性或待办</small>
 </aside>
</template>
<style scoped>
.stream-panel{position:fixed;right:20px;bottom:22px;width:min(460px,85vw);padding:16px;z-index:120;background:#20373bf5;color:#f5e4bd;border:1px solid #c9ad72;border-radius:8px;box-shadow:0 8px 28px #0006;line-height:1.6;pointer-events:none}.stream-panel p{margin:6px 0}.stream-panel small{color:#c8d7d0}
</style>
