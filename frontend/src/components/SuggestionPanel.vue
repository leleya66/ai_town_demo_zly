<!-- 展示后端活动目录、建议回应和回合结果，并提交用户选择的活动与地点。 -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { places, type NpcId, type PlaceId } from '../world';
import type { Activity, BackendWorld, Reply } from '../api';
const props = defineProps<{ world: BackendWorld; selected: NpcId; busy: boolean; replaying: boolean; reply: Reply | null; compact?: boolean }>();
const emit = defineEmits<{ suggest: [payload: {type: 'suggest_activity'; npc_id: NpcId; activity: Activity; target_place_id: PlaceId}] }>();
const activity = ref<Activity>('rest');
const destination = ref<PlaceId>('forest');
const labels = computed(() => Object.fromEntries(Object.entries(props.world.activity_rules).map(([id,rule])=>[id,rule.label])) as Record<Activity,string>);
const suggestionLabels = computed(() => Object.fromEntries(Object.entries(labels.value).filter(([id]) => props.world.activity_rules[id as Activity].suggestible !== false && (!props.world.festival.cards || props.selected==='wise' || !['prepare_talk','host_talk'].includes(id)))));
const allowed = computed(() => props.world.festival.cards && ['invite_event','run_event'].includes(activity.value) ? [({joe:'plaza',wise:'library',calm:'forest',stead:'forest'} as const)[props.selected]] : props.world.activity_rules[activity.value].places);
watch(()=>props.selected,()=>{if(!(activity.value in suggestionLabels.value))activity.value='rest';if(['invite_event','run_event'].includes(activity.value))destination.value=({joe:'plaza',wise:'library',calm:'forest',stead:'forest'} as const)[props.selected];});
watch(activity, value => { destination.value = ({seek_company:'plaza',rest:'forest',read:'library',chat:'plaza',work:'workshop',repair_bench:'forest',sit_bench:'forest',prepare_talk:'library',host_talk:'library',attend_talk:'library',invite_event:({joe:'plaza',wise:'library',calm:'forest',stead:'forest'} as const)[props.selected],run_event:'forest',join_event:'forest'} as const)[value]; });
const resident = computed(() => props.world.npcs.find(n => n.id === props.selected)!);
const duplicate = computed(() => resident.value.agenda.some(t => t.activity === activity.value && t.target_place_id === destination.value));
const decision = computed(() => props.world.last_decisions.find(d => d.npc_id === props.selected));
const result = computed(() => props.world.last_results.find(r => r.npc_id === props.selected));
</script>
<template>
 <section class="suggestion-panel dark-panel" :class="{ compact }" aria-label="居民活动建议">
  <div class="suggestion-heading"><h2>给 {{ resident.name }} 的活动建议</h2><span>本回合剩余 {{ world.interventions_remaining }} / 2 次</span></div>
  <form @submit.prevent="emit('suggest', {type:'suggest_activity',npc_id:selected,activity,target_place_id:destination})">
   <label>建议活动<select v-model="activity" aria-label="建议活动"><option v-for="(label,id) in suggestionLabels" :key="id" :value="id">{{ label }}</option></select></label>
   <label>目标地点<select v-model="destination" aria-label="建议地点"><option v-for="id in allowed" :key="id" :value="id">{{ places[id].name }}</option></select></label>
   <button type="submit" :disabled="busy || world.phase === 'ended' || (world.interventions_remaining === 0 && !duplicate)">提出建议</button>
   <small>接受或拒绝消耗一次机会；重复待办合并且不扣次数。每人最多3项，执行前重新检查条件。</small>
  </form>
  <p v-if="reply?.outcome" class="suggestion-reply" role="status"><strong>{{ reply.outcome === 'accepted' ? '已接受' : '已拒绝' }}</strong> · {{ reply.reason }}</p>
  <div class="agenda-panel" aria-label="居民待办">
   <p v-if="resident.agenda_preview" class="agenda-preview"><strong>{{ world.ai.enabled ? '规则参考 · AI将在推进时独立选择' : '下一回合预计' }} · {{ labels[resident.agenda_preview.activity] }}</strong>（非保证）<br>{{ resident.agenda_preview.reason }}</p>
   <p v-if="world.phase === 'ended'">本局已结束，待办仅供回顾，不再执行。</p>
   <p v-if="resident.agenda.length" class="pending-suggestion">有效待办 {{ resident.agenda.length }} / 3 · 当前仍在{{ places[resident.place].name }}。</p>
   <p v-else>暂无待办，居民将自主选择活动。</p>
   <ol class="agenda-list"><li v-for="item in resident.agenda" :key="item.id" class="agenda-item">
    <strong>{{ labels[item.activity] }} · {{ places[item.target_place_id].name }}</strong>
    <span> — {{ item.started ? '已开始' : item.status === 'deferred' ? '暂缓' : '待执行' }} · {{ item.accepted_turn === null ? '旧存档承诺' : `第${item.accepted_turn}回合接受` }}</span>
    <small>{{ item.expires_at_turn === null ? '保留至完成或条件失效' : `有效至第${item.expires_at_turn}回合` }}</small>
    <p v-if="item.defer_reason">暂缓原因：{{ item.defer_reason }}</p>
   </li></ol>
  </div>
  <div v-if="decision && result" class="turn-result"><strong>上一回合结果 · {{ labels[result.activity] }} · {{ decision.source === 'ai' ? 'AI选择' : '规则选择' }}</strong><p>{{ decision.reason }}</p><p v-if="decision.thought">角色心情：{{ decision.thought }}</p><p v-if="decision.fallback_reason">降级：{{ decision.fallback_reason }}</p><p>{{ places[result.from_place_id].name }} → {{ places[result.to_place_id].name }} · 精力 {{ result.effects.energy >= 0 ? '+' : '' }}{{ result.effects.energy }} · 情绪 {{ result.effects.mood >= 0 ? '+' : '' }}{{ result.effects.mood }} · 社交意愿 {{ result.effects.social >= 0 ? '+' : '' }}{{ result.effects.social }}</p><p v-for="note in result.notes" :key="note">{{ note }}</p></div>
 </section>
</template>
<style scoped>
.suggestion-panel{margin-top:9px;padding:14px 18px;color:#eaddbe}.suggestion-heading{display:flex;justify-content:space-between;gap:12px;align-items:center}.suggestion-heading span{font-size:12px;color:#ddc186}.suggestion-panel form{display:flex;align-items:end;gap:14px;margin:12px 0;flex-wrap:wrap}.suggestion-panel label{display:flex;flex-direction:column;gap:6px;font-size:12px}.suggestion-panel select{background:#20373b;color:#f5e4bd;border:1px solid #a88c57;border-radius:4px;padding:8px;min-width:130px;font:inherit}.suggestion-panel button{background:#c9ad72;color:#1d3033;border-radius:4px;padding:10px 18px;font-weight:600}.suggestion-panel small{max-width:440px;color:#b3beb6;line-height:1.6}.suggestion-reply,.pending-suggestion{margin:8px 0;font-size:13px}.suggestion-reply strong{color:#e9c985}.turn-result{border-top:1px solid #a88c5755;padding-top:10px;font-size:12px;line-height:1.8}.turn-result p{color:#c8d7d0}
.agenda-panel{border-top:1px solid #a88c5755;padding-top:10px;font-size:13px;line-height:1.7}.agenda-panel ol{padding-left:22px}.agenda-item{margin:8px 0}.agenda-item small{display:block}.agenda-item p{color:#c8d7d0}.suggestion-panel.compact{margin:0;padding:8px 10px;height:100%;overflow:auto}.compact .suggestion-heading h2{font-size:13px}.compact .suggestion-heading span{font-size:9px}.compact form{margin:4px 0;gap:6px;flex-wrap:nowrap}.compact label{gap:2px;font-size:9px}.compact select{padding:3px 5px;min-width:95px;font-size:9px}.compact button{padding:4px 7px;font-size:9px}.compact form>small{display:none}.compact .suggestion-reply,.compact .pending-suggestion{margin:2px 0;font-size:8px}.compact .agenda-panel{padding-top:3px;font-size:8px;line-height:1.35}.compact .agenda-preview{margin:2px 0}.compact .agenda-list{display:none}.compact .turn-result{padding-top:3px;font-size:8px;line-height:1.35}.compact .turn-result p{display:inline;margin-right:7px}.compact .turn-result p:nth-of-type(n+3){display:none}
</style>
