<!-- 展示林间长椅事件条件、进度和操作入口；发现与修缮由后端执行。 -->
<script setup lang="ts">
import type { BenchEvent } from '../api';
defineProps<{ event: BenchEvent; busy: boolean; remaining: number }>();
defineEmits<{ discover: []; repair: []; locate: [] }>();
</script>
<template>
 <section class="bench-event" aria-label="长椅现场：修好林间长椅" :data-state="event.status">
  <small>长椅现场 · 林间</small><h3>修缮状态</h3>
  <template v-if="!event.discovered"><p>林间有一把摇晃的旧长椅，走近看看发生了什么。</p><button :disabled="busy" @click="$emit('discover')">观察林间长椅</button></template>
  <template v-else>
   <p v-if="event.status === 'broken'">Calm 想找回安静的休息角。请 Stead 帮忙，累计两次有效劳动即可修好。</p>
   <p v-else-if="event.status === 'repairing'">支架已经固定，木板还需修整。Stead 会继续工作；精力不足时先休息，已开始的修缮优先，其他建议进入待办。</p>
   <p v-else>长椅已在第 {{ event.completed_turn }} 回合修好。解锁「长椅休憩」，每次最多恢复16精力。</p>
   <progress :value="event.progress" :max="event.required" aria-label="长椅修缮进度"/>
   <strong>{{ event.status === 'repaired' ? '已完成' : '修缮进度' }} {{ event.progress }} / {{ event.required }}</strong>
   <button v-if="event.status !== 'repaired'" :disabled="busy || remaining === 0" @click="$emit('repair')">邀请 Stead 修缮</button>
   <button :disabled="busy" @click="$emit('locate')">查看林间长椅</button>
   <small v-if="event.status !== 'repaired'">条件：精力至少30 · 每次劳动消耗12精力 · 新邀请消耗1次建议机会，重复待办不扣次数</small>
  </template>
 </section>
</template>
<style scoped>
.bench-event{margin-top:14px;border-top:1px solid #a48755;padding-top:14px;color:#34413b}.bench-event h3{margin:5px 0;font-size:17px}.bench-event p{font-size:12px;line-height:1.7;margin:8px 0}.bench-event small{display:block;font-size:10px;line-height:1.6;color:#756340}.bench-event progress{width:100%;height:9px;accent-color:#667c48}.bench-event strong{display:block;font-size:12px;margin:5px 0}.bench-event button{display:block;width:100%;border:1px solid #9b8055;border-radius:4px;padding:7px 5px;margin:7px 0;font-size:12px;background:#fcf0d599}.bench-event[data-state=repaired] strong{color:#3c7154}
</style>
