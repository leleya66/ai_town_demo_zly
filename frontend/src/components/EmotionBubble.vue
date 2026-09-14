<!-- 将后端交流表情映射为短气泡及可访问说明，不自行推断居民情绪。 -->
<script setup lang="ts">
import type { Expression } from '../api';
defineProps<{ cue: Expression }>();
const faces = { pleased: '😊', hesitant: '😕', happy: '😄', warm: '☺️' };
const labels = { pleased: '欣然接受', hesitant: '有些犹豫', happy: '聊得开心', warm: '感到温暖' };
</script>
<template><span class="emotion-bubble" :data-emotion-npc="cue.npc_id" :data-emotion="cue.emotion" :data-source="cue.source" role="img" :aria-label="`${labels[cue.emotion]}：${cue.reason}`" :title="cue.reason">{{ faces[cue.emotion] }}</span></template>
<style scoped>
.emotion-bubble{position:relative;display:inline-flex;align-items:center;justify-content:center;min-width:37px;height:32px;padding:2px 5px;border:1.5px solid #b4945b;border-radius:10px;background:#fff4dcec;box-shadow:0 2px 5px #14282066;color:#513a20;font:23px/1 'Segoe UI Emoji',sans-serif;pointer-events:none}
.emotion-bubble::after{content:'';position:absolute;bottom:-5px;left:7px;width:7px;height:7px;background:#fff4dc;border-right:1.5px solid #b4945b;border-bottom:1.5px solid #b4945b;transform:skewY(-20deg) rotate(35deg)}
</style>
