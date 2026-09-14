<!-- 展示选中居民收发邀请的真实回应与赴约结果，待回复不冒充已承诺或已得分。 -->
<script setup lang="ts">
import {computed} from 'vue';
import type {Invitation} from '../api';
import {places,type NpcId} from '../world';
const props=defineProps<{invitations:Invitation[];selected:NpcId}>();
defineEmits<{select:[id:NpcId]}>();
const entries=computed(()=>props.invitations.filter(i=>i.sender===props.selected||i.recipient===props.selected).slice(-12).reverse());
const statuses:Record<string,string>={pending:'待回应',accepted:'已接受',deferred:'暂缓',declined:'已拒绝',completed:'已完成',expired:'已过期',cancelled:'已撤回'};
const events:Record<string,string>={care:'邻里交流',talk:'读书分享',listen:'倾听接纳',bench:'长椅告知'};
const npcNames:Record<NpcId,string>={joe:'Joe',wise:'Wise',calm:'Calm',stead:'Stead'};
</script>
<template>
 <section class="invitation-panel dark-panel" aria-label="邀请与回应"><h3>{{ npcNames[selected] }} · 邀请与回应</h3>
  <div class="resident-tabs" aria-label="邀请记录角色"><button v-for="(name,id) in npcNames" :key="id" :aria-pressed="selected===id" @click="$emit('select',id)">{{ name }}</button></div>
  <p class="chain">发出邀请 → 接受／暂缓／拒绝 → 双方实际赴约 → 后端结算</p>
  <p>显示该居民最近12条收发邀请。接受不等于到场；实际得分以开放日贡献账本为准。</p>
  <p v-if="!entries.length">暂无邀请。准备好专属事件后，居民可自主发出邀请；也可在建议区选择“发出专属事件邀请”。</p>
  <article v-for="i in entries" :key="i.id" :data-invitation="i.id"><strong>{{ events[i.event] }} · {{ npcNames[i.sender] }} → {{ npcNames[i.recipient] }} · {{ statuses[i.status] }}</strong>
   <p>约定第{{ i.due_turn }}回合 · {{ places[i.place].name }} · 有效至第{{ i.expires_turn }}回合</p>
   <p v-if="i.response_reason">{{ i.response_source==='ai'?'AI回应':'规则回应' }}：{{ i.response_reason }}</p>
   <small>{{ i.result }}。邀请和接受本身不计分。</small>
  </article>
 </section>
</template>
<style scoped>
.invitation-panel{padding:14px 18px;margin:12px 0;line-height:1.6}.invitation-panel h3{margin:0;color:#edce88}.invitation-panel article{padding:10px 0;border-top:1px solid #a88c5755}.invitation-panel p{margin:5px 0;font-size:13px}.invitation-panel small{color:#bfcbc6}
.resident-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.resident-tabs button{border:1px solid #a88c57;border-radius:4px;padding:6px 12px}.resident-tabs button[aria-pressed=true]{background:#edce88;color:#20373b}.chain{color:#edce88}
</style>
