<!-- 展示开放日目标、支持对象、实际贡献与同快照对照入口；所有评分与分支均由后端生成。 -->
<script setup lang="ts">
import { ref } from 'vue';
import type { Festival, Reply } from '../api';
import type { NpcId } from '../world';
const props = defineProps<{ festival: Festival; turn: number; ended: boolean; busy: boolean; compact?: boolean; command?: (route: string, payload?: Record<string, unknown>) => Promise<Reply | undefined> }>();
const selected = ref<NpcId>('wise');
const comparison = ref<Reply['comparison']>();
async function compare() { comparison.value = (await props.command?.('comparisons'))?.comparison; }
</script>
<template>
 <section class="festival-panel dark-panel" :class="{ compact }" aria-label="开放日与贡献榜">
  <div class="festival-head"><h2>六回合开放日 · {{ ended ? (festival.success ? '筹备成功' : '目标尚未完成') : '一起建设，竞争本日最佳居民' }}</h2>
   <span>公共目标：完成至少两类贡献</span></div>
  <div v-if="festival.cards" class="goals"><span v-for="card in festival.cards" :key="card.id">{{ card.completed?'✓':'○' }} {{ card.title }}</span><strong>全镇总贡献 {{ festival.total_score }} 分</strong></div>
  <div v-else class="goals"><span>{{ festival.goals.bench ? '✓' : '○' }} 修好长椅</span><span>{{ festival.goals.talk ? '✓' : '○' }} 有听众的读书分享</span><span>{{ festival.goals.exchange ? '✓' : '○' }} 有效邻里交流</span></div>
  <div class="rankings"><div v-for="row in festival.ranking" :key="row.npc_id"><strong>{{ row.name }} · {{ row.score }} 分</strong><small v-if="festival.supported_npc_id === row.npc_id">你支持的居民</small></div></div>
  <p v-if="ended">本日最佳居民：{{ festival.winners.length ? festival.winners.join('、') : '暂无有效贡献，不评选冠军' }}<span v-if="festival.supported_npc_id"> · {{ festival.winners.includes(festival.supported_npc_id) ? '你的支持对象获选' : '你的支持对象未获选' }}</span></p>
  <div v-if="command" class="controls">
   <template v-if="turn === 0 && !festival.supported_npc_id"><label>支持对象 <select v-model="selected" aria-label="支持对象"><option v-for="row in festival.ranking" :key="row.npc_id" :value="row.npc_id">{{ row.name }}</option></select></label><button :disabled="busy" @click="command('support',{npc_id:selected})">确认支持</button></template>
   <button :disabled="busy || ended" @click="compare">创建同起点对照</button>
   <template v-if="comparison"><a :href="`/?world=${comparison.mock}`" target="_blank" rel="noopener">打开 Mock 对照</a><a :href="`/?world=${comparison.ai}`" target="_blank" rel="noopener">打开 AI 对照</a></template>
  </div>
  <details :open="compact"><summary>贡献明细与玩法说明</summary><p v-if="festival.cards">Joe每位关心对象+2；Wise每位实际听众+2；Calm每位倾听对象+2；Stead修好长椅+2、每位实际告知对象+2。同一对象不重复计分，每条路线封顶6分。最高分可并列；支持、邀请、接受均不直接加分。</p><p v-else>旧局：修缮每次2分；分享主持4分、听众1分；同一伙伴首次交流各1分，关心低落对象额外1分。</p><p>准备后发出邀请，接收者自主回应，双方实际到场才完成互动。支持对象没有属性加成。</p><p v-if="!festival.ledger.length">尚无贡献。完成行动后才记分。</p><p v-for="entry in (compact ? festival.ledger.slice(-2) : festival.ledger)" :key="entry.npc_id+entry.key">第{{ entry.turn }}回合 · {{ entry.npc_id }} +{{ entry.points }}：{{ entry.reason }}</p></details>
 </section>
</template>
<style scoped>
.festival-panel{padding:16px 18px;margin:12px 0;line-height:1.6}.festival-head,.goals,.rankings,.controls{display:flex;gap:14px;flex-wrap:wrap;align-items:center}.festival-head h2{font-size:18px;color:#edce88;margin:0}.festival-head span{font-size:12px}.goals{margin:8px 0}.rankings>div{padding:8px 14px;border:1px solid #a88c5766;border-radius:5px}.rankings small{display:block;color:#e1bd72}.controls{margin:10px 0}.controls button,.controls select,.controls a{border:1px solid #a88c57;border-radius:4px;padding:6px 10px;color:#edce88;background:#20373b}.festival-panel summary{cursor:pointer;font-size:13px;margin-top:10px}.festival-panel details p{font-size:13px}.festival-panel.compact{margin:0;padding:8px 10px;min-width:0;height:100%;overflow:auto}.compact .festival-head h2{font-size:13px}.compact .festival-head span{font-size:9px}.compact .goals{margin:3px 0;gap:7px;font-size:9px}.compact .rankings{gap:5px}.compact .rankings>div{padding:3px 6px;font-size:9px}.compact .rankings small{display:none}.compact .controls{margin:4px 0;gap:5px}.compact .controls button,.compact .controls select,.compact .controls a{padding:3px 5px;font-size:9px}.compact details{margin-top:2px}.compact details summary{font-size:9px;display:none}.compact details p{font-size:8px;line-height:1.35;margin:2px 0}.compact>p{font-size:9px}
</style>
