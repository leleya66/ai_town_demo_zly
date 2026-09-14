<!-- 根据居民标识裁切展示头像，不包含角色数值或决策逻辑。 -->
<script setup lang="ts">
import type { NpcId } from '../world';
defineProps<{ id: NpcId; size?: number }>();
const offsets = { joe: 18, wise: 173, calm: 334, stead: 492 };
</script>
<template><span class="portrait" aria-hidden="true" :style="{width: `${size || 52}px`, height: `${size || 52}px`}"><img src="/assets/reference-ui.png" alt="" draggable="false" :style="{width: `${1672 * (size || 52) / 70}px`, left: `${-offsets[id] * (size || 52) / 70}px`, top: `${-680 * (size || 52) / 70}px`}"></span></template>
