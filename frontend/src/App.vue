<!-- 编排地图、居民、任务和对话界面；通信与回放分别交由组合式模块管理。 -->
<script setup lang="ts">
import { computed, nextTick, ref, watch, onBeforeUnmount } from 'vue';
import { Feather, House, Users, ScrollText, ChartNoAxesCombined, BookOpen, Settings, Sun, ChevronRight, MapPin, Zap, Smile, MessageCircle, Hand, Eye, Play, Plus, Minus, RotateCcw, Save, FolderOpen, X, TreePine, Hammer, Compass, Send, Sparkles, Heart } from '@lucide/vue';
import Portrait from './components/Portrait.vue';
import LifeMap from './components/LifeMap.vue';
import EmotionBubble from './components/EmotionBubble.vue';
import BenchEvent from './components/BenchEvent.vue';
import { useWorld } from './composables/useWorld';
import SuggestionPanel from './components/SuggestionPanel.vue';
import SaveList from './components/SaveList.vue';
import EndingPanel from './components/EndingPanel.vue';
import IntentionPanel from './components/IntentionPanel.vue';
import SocialMemories from './components/SocialMemories.vue';
import AssessmentPanel from './components/AssessmentPanel.vue';
import AiPanel from './components/AiPanel.vue';
import FestivalPanel from './components/FestivalPanel.vue';
import DialoguePanel from './components/DialoguePanel.vue';
import StreamPanel from './components/StreamPanel.vue';
import EventTasks from './components/EventTasks.vue';
import InvitationPanel from './components/InvitationPanel.vue';
import { places, metrics, type NpcId, type PlaceId, type Metric } from './world';
const { world, backendWorld, busy, connectionError, suggestionReply, streamStatus, streamDraft, streamInput, connect, command, suggest,
 replaying, playbackRoutes, playbackFrames, expressions, skipPlayback } = useWorld(
 () => setMapView('life'), value => { selectedPlace.value = value.npcs.find(n => n.id === selected.value)!.place; }, toast);

const ended = computed(() => backendWorld.value?.phase === 'ended');
async function toggleAi() {
 const result = await command('ai-mode', { enabled: !backendWorld.value?.ai.enabled });
 if (result?.message) toast(result.message);
}
watch(() => backendWorld.value?.ending?.id, id => { if (id) modal.value = '游戏结局'; });
async function restartEnding(save: boolean) {
 const result = await command('commands', {type: save ? 'save_restart' : 'reset'});
 if (!result) return false;
 selectNpc('joe'); suggestionReply.value = null; input.value = ''; modal.value = ''; toast(result.message || '新游戏已开始'); return true;
}
const selected = ref<NpcId>('joe'); const selectedPlace = ref<PlaceId>('plaza');
watch(selected, () => { suggestionReply.value = null; });
const npc = computed(() => world.value.npcs.find(n => n.id === selected.value)!);
const scene = computed(() => places[selectedPlace.value]);
const typicalActivity = computed(() => ({forest:'rest',library:'read',plaza:'chat',workshop:'work'} as const)[selectedPlace.value]);
const sceneRule = computed(() => backendWorld.value?.activity_rules[typicalActivity.value]);
const sceneEffects = computed(() => sceneRule.value?.effects);
const input = ref(''); const chatInput = ref<HTMLInputElement>(); const messagesEl = ref<HTMLElement>();
const modal = ref(''); const dialog = ref<HTMLDialogElement>(); const notice = ref(''); let noticeTimer: ReturnType<typeof setTimeout>;
function openSaves() { modal.value='存档列表'; }
async function restoreSave(id:string) { if (await command('commands',{type:'load',save_id:id})) { modal.value=ended.value ? '游戏结局' : ''; suggestionReply.value=null; toast('存档已恢复。'); } }
const showReasons = ref(false);
const mapView = ref<'overview' | 'life'>('overview');
function setMapView(view: 'overview' | 'life') { mapView.value = view; resetView(); }
const zoom = ref(1); const pan = ref({ x: 0, y: 0 }); let drag: { x: number; y: number; px: number; py: number } | null = null;
const icons = { forest: TreePine, library: BookOpen, plaza: Users, workshop: Hammer };
const metricIcons = { energy: Zap, mood: Smile, social: Users };
const nav = [{ name: '小镇地图', icon: House }, { name: '角色一览', icon: Users }, { name: '事件日志', icon: ScrollText }, { name: '世界状态', icon: ChartNoAxesCombined }, { name: '图鉴', icon: BookOpen }, { name: '设置', icon: Settings }];
const clock = computed(() => { const total = 510 + world.value.turn * 10; return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`; });
const means = computed(() => Object.fromEntries(metrics.map(({ key }) => [key, Math.round(world.value.npcs.reduce((sum, n) => sum + n[key], 0) / 4)])) as Record<Metric, number>);
const ecology = computed(() => world.value.ecology ?? '等待世界状态');
const completedEventCount = computed(() => backendWorld.value?.festival.cards?.filter(card => card.completed).length ?? 0);
const compactRanking = computed(() => backendWorld.value?.festival.ranking ?? []);
function toast(text: string) { notice.value = text; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => notice.value = '', 4500); }
// 选择、镜头和弹窗只改变界面，不写入世界状态。
function selectNpc(id: NpcId) { selected.value = id; selectedPlace.value = npc.value.place; resetView(); }
function selectPlace(id: PlaceId) { selectedPlace.value = id; const resident = world.value.npcs.find(n => n.place === id); if (resident) selected.value = resident.id; }
function resetView() { zoom.value = 1; pan.value = { x: 0, y: 0 }; }
function changeZoom(delta: number) { zoom.value = Math.max(1, Math.min(1.8, +(zoom.value + delta).toFixed(1))); if (zoom.value === 1) pan.value = { x: 0, y: 0 }; }
function startDrag(event: PointerEvent) { if ((event.target as HTMLElement).closest('button')) return; drag = { x: event.clientX, y: event.clientY, px: pan.value.x, py: pan.value.y }; (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId); }
function moveDrag(event: PointerEvent) { if (!drag) return; pan.value = { x: Math.max(-220, Math.min(220, drag.px + event.clientX - drag.x)), y: Math.max(-160, Math.min(160, drag.py + event.clientY - drag.y)) }; }
// 玩家命令交给统一通信模块，成功后更新界面提示。
async function send(text = input.value) { if (!text.trim()) return; const result = await command('commands', {type:'message',npc_id:selected.value,text}); if (!result) return; input.value = ''; await nextTick(); messagesEl.value?.scrollTo({top:messagesEl.value.scrollHeight,behavior:'smooth'}); }
async function nextTurn() { suggestionReply.value = null; if (await command('turns')) toast(`第 ${world.value.turn} 回合 · 决策与执行结果已更新`); }
async function saveWorld() { if (await command('commands',{type:'save'})) { toast(`已存档：第 ${world.value.turn} 回合（服务重启后仍可加载）。`); return true; } return false; }
async function loadWorld() { suggestionReply.value = null; if (await command('commands',{type:'load'})) toast('已恢复后端存档。'); }
async function resetWorld() { if (await command('commands',{type:'reset'})) { selectNpc('joe'); suggestionReply.value = null; input.value=''; modal.value=''; toast('新游戏已开始 · 第 0 回合'); } }
function locateBench() { setMapView('life'); selectPlace('forest'); }
async function discoverBench() { locateBench(); if (ended.value) return; await command('commands',{type:'observe',place_id:'forest'}); }
async function repairBench() { selectNpc('stead'); setMapView('life'); await suggest({type:'suggest_activity',npc_id:'stead',activity:'repair_bench',target_place_id:'forest'}); }
async function doObserve() { await command('commands',{type:'observe',place_id:selectedPlace.value}); }
async function doInteract() { await command('commands',{type:'interact',npc_id:selected.value}); }
function openNav(name: string) { if (name === '小镇地图') { modal.value = ''; resetView(); } else modal.value = name; }
onBeforeUnmount(() => clearTimeout(noticeTimer));
watch(modal, async value => { await nextTick(); if (value && !dialog.value?.open) dialog.value?.showModal(); else if (!value && dialog.value?.open) dialog.value.close(); });
</script>

<template>
 <StreamPanel :status="streamStatus" :draft="streamDraft" :input="streamInput"/>
 <div v-if="backendWorld" class="game-shell" :inert="busy && !replaying" :aria-busy="busy">
  <div v-if="connectionError" role="alert">{{ connectionError }} <button @click="connect">重新连接</button></div>
  <header class="topbar">
   <div class="brand"><Feather :size="38" stroke-width="1.3"/><div><h1>AI 智能体小镇</h1><p>每个人都有自己的生活，而你，可以成为改变的起点。</p></div></div>
   <div class="world-clock"><div><strong>第 {{ world.turn }} 回合<span v-if="backendWorld.max_turns"> / {{ backendWorld.max_turns }}</span></strong><span>春季 · 4月{{ 12 + Math.floor(world.turn / 24) }}日</span></div><Sun :size="32"/><div><strong>晴天</strong><span>{{ clock }}</span></div></div>
   <div class="motto">平凡的日子里，<br>也藏着不平凡的故事。</div>
   <div class="ai-control"><button class="ai-switch" role="switch" :aria-checked="backendWorld.ai.enabled" aria-label="AI模式" :disabled="busy" @click="toggleAi"><span>AI模式</span><span class="switch-track" :class="{ on: backendWorld.ai.enabled }"><i></i></span><span>{{ backendWorld.ai.enabled ? '开启' : '关闭' }}</span></button><small>{{ !backendWorld.ai.enabled ? 'Mock · 规则模拟' : backendWorld.ai.available ? backendWorld.ai.model + ' · 已启用' : '配置不可用' }}</small></div>
   <button class="save-top" :disabled="busy || !backendWorld" @click="saveWorld"><Save :size="18"/>存档</button><button class="icon-button settings-top" aria-label="打开设置" @click="modal = '设置'"><Settings :size="21"/></button>
  </header>

  <div class="session-banner"><span>{{ ended ? '本局已结束，可回顾居民与事件。' : backendWorld.max_turns ? '第0回合准备，完成6次结算后查看结局。' : '旧版自由回合存档；重新开始可体验六回合新规则。' }}</span><button v-if="ended" @click="modal = '游戏结局'">查看结局</button></div>
  <section class="dashboard-strip dark-panel" aria-label="AI决策概览">
   <div class="dashboard-item ai-summary"><small>决策模式</small><strong>{{ backendWorld.ai.enabled ? (backendWorld.ai.available ? 'AI · ' + backendWorld.ai.model : 'AI配置不可用') : 'Mock · 规则模拟' }}</strong><span class="mode-note">{{ backendWorld.ai.enabled ? '模型参与理解与选择，最终仍由后端规则执行' : '规则决策，无需模型即可完整试玩' }}</span></div>
   <div class="dashboard-item festival-summary"><small>开放日进度</small><strong>{{ completedEventCount }} / 4 · 全镇 {{ backendWorld.festival.total_score }} 分</strong><span class="ranking-mini"><b v-for="row in compactRanking" :key="row.npc_id">{{ row.name }} {{ row.score }}</b></span></div>
   <div class="dashboard-tools"><button @click="modal='邀请链路'">邀请链路</button><button v-if="backendWorld.npcs.find(n => n.id === selected)?.last_dialogue" @click="modal='对话影响'">对话影响</button><button v-if="backendWorld.npcs.find(n => n.id === selected)?.bench_intention" @click="modal='长椅意图'">长期意图</button></div>
  </section>
  <section class="inline-control-strip" aria-label="开放日详情与活动建议">
   <FestivalPanel compact :festival="backendWorld.festival" :turn="world.turn" :ended="ended" :busy="busy" :command="command"/>
   <SuggestionPanel compact :world="backendWorld" :selected="selected" :busy="busy || ended" :replaying="replaying" :reply="suggestionReply" @suggest="suggest"/>
  </section>
  <div class="upper-layout">
   <nav class="navigation" aria-label="主导航"><button v-for="item in nav" :key="item.name" :class="{ active: (modal || '小镇地图') === item.name }" @click="openNav(item.name)"><component :is="item.icon" :size="21"/><span>{{ item.name }}</span></button><div class="nav-decoration"><Compass :size="78" stroke-width=".7"/><small>A SMALL TOWN<br>A BIGGER LIFE</small></div></nav>

   <section class="quest-panel parchment"><h2><ScrollText :size="25"/>任务与目标</h2><EventTasks :cards="backendWorld.festival.cards || []" @select="selectNpc"/><BenchEvent v-if="backendWorld" :event="backendWorld.bench_event" :busy="busy || ended" :remaining="backendWorld.interventions_remaining" @discover="discoverBench" @repair="repairBench" @locate="locateBench"/><div v-else class="quest-empty"><Feather :size="26" stroke-width="1"/><span>故事从一次相遇开始</span><p>与居民交谈，<br>让平常的一天有些不同。</p></div>
    <div class="quest-bottom"><span>探索不必匆忙</span><i></i></div>
   </section>

   <section class="map-panel" :class="{ 'life-view': mapView === 'life' }" aria-label="可交互小镇地图" @pointerdown="startDrag" @pointermove="moveDrag" @pointerup="drag = null" @pointercancel="drag = null" @wheel.prevent="changeZoom($event.deltaY < 0 ? .1 : -.1)">
    <div class="map-view-tabs" role="tablist" aria-label="地图视角"><button id="overview-tab" role="tab" aria-controls="town-map-content" :aria-selected="mapView === 'overview'" @click.stop="setMapView('overview')">小镇全景</button><button id="life-tab" role="tab" aria-controls="town-map-content" :aria-selected="mapView === 'life'" @click.stop="setMapView('life')">居民生活</button></div>
    <div id="town-map-content" class="map-world" role="tabpanel" :aria-labelledby="mapView === 'overview' ? 'overview-tab' : 'life-tab'" :style="{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }"><template v-if="mapView === 'overview'"><img class="map-image" src="/assets/town-map.png" alt="湖畔小镇全景：林间、图书馆、喷泉广场与水车工坊" draggable="false"/>
     <div v-for="(place, id) in places" :key="id" class="map-location" :class="{ chosen: selectedPlace === id }" :style="{ left: `${place.x}%`, top: `${place.y}%` }">
      <div class="map-residents"><button v-for="resident in world.npcs.filter(n => n.place === id)" :key="resident.id" class="map-portrait" :aria-label="`选择 ${resident.name}：${resident.action}`" @click.stop="selectNpc(resident.id)"><Portrait :id="resident.id" :size="47"/><EmotionBubble v-if="expressions[resident.id]" class="overview-emotion" :cue="expressions[resident.id]!"/><span class="resident-hover">{{ resident.name }} · {{ resident.action }}</span></button></div>
      <button class="map-label" :aria-label="`查看${place.name}`" :aria-pressed="selectedPlace === id" @click.stop="selectPlace(id)"><span class="location-icon"><component :is="icons[id]" :size="24"/></span><span><strong>{{ place.name }}</strong><small>{{ place.subtitle }}</small></span></button>
     </div>
    </template><LifeMap v-else :npcs="world.npcs" :expressions="expressions" :last-routes="backendWorld?.last_movements ?? []" :positions="Object.fromEntries(backendWorld?.npcs.map(n=>[n.id,n.position]) ?? [])" :bench="backendWorld?.bench_event" :frames="playbackFrames" :routes="playbackRoutes" :selected="selected" :selected-place="selectedPlace" @inspect-bench="discoverBench" @select-npc="selectNpc" @select-place="selectPlace"/></div>
    <div class="map-tools"><button aria-label="放大地图" @click.stop="changeZoom(.2)"><Plus :size="22"/></button><button aria-label="缩小地图" @click.stop="changeZoom(-.2)"><Minus :size="22"/></button><button aria-label="重置地图视角" @click.stop="resetView"><RotateCcw :size="18"/></button></div>
    <div v-if="mapView === 'overview'" class="map-poem">不同的选择，<br>会让小镇走向不同的未来。</div><div class="map-help">{{ mapView === 'life' ? '居民位置 · 点击人物或地点查看' : '拖动探索 · 滚轮缩放' }} <span>{{ Math.round(zoom * 100) }}%</span></div>
   </section>

   <section class="scene-panel dark-panel"><div class="scene-image" :class="scene.image"></div><div class="scene-copy"><h2><component :is="icons[selectedPlace]" :size="26"/>{{ scene.name }}</h2><p class="scene-tagline">{{ scene.subtitle }}</p><p class="scene-desc">{{ scene.desc }}</p><h3><Sparkles :size="15"/>{{ sceneRule?.label ?? '典型活动' }} · 回合基础效果</h3><div v-if="sceneEffects" class="effects"><div v-for="{key, label} in metrics" :key="key"><component :is="metricIcons[key]" :size="16" :class="key"/><span>{{ label }}</span><b :class="sceneEffects[key] > 0 ? 'positive' : 'negative'">{{ sceneEffects[key] > 0 ? '+' : '' }}{{ sceneEffects[key] }}</b><small>{{ sceneEffects[key] > 0 ? '有所恢复' : '少量消耗' }}</small></div></div><h3><Users :size="15"/>行为倾向</h3><div class="tags"><span v-for="action in scene.actions" :key="action">{{ action }}</span></div><h3><Eye :size="15"/>场景限制</h3><div class="tags limits"><span v-for="limit in scene.limits" :key="limit">{{ limit }}</span></div><p v-if="backendWorld.rules_version === 2" class="scene-desc">连续重复同一活动时，情绪收益逐次减少，最低为−2；修好长椅另获一次性情绪+6。实际变化见行动结果。</p><p class="scene-signature">人来人往，才是生活。</p></div></section>
  </div>

  <div v-if="replaying" class="replay-banner" role="status">居民正在沿路前往目的地 · 到达后展示活动结果 <button @click="skipPlayback">跳过动画</button></div>
  <div class="bottom-layout">
   <section class="npc-panel dark-panel"><div class="panel-heading"><h2>NPC 角色</h2><button class="text-button" @click="modal = '角色一览'">角色详情 <ChevronRight :size="14"/></button></div><div class="npc-grid"><button v-for="n in world.npcs" :key="n.id" class="npc-card" :class="{ selected: selected === n.id }" :aria-pressed="selected === n.id" :data-npc="n.id" @click="selectNpc(n.id)"><div class="npc-top"><Portrait :id="n.id" :size="51"/><div><strong>{{ n.name }}</strong><small>{{ n.personality }}<br>{{ n.subtitle }}</small></div></div><div class="npc-metrics"><div v-for="{key, label} in metrics" :key="key" class="metric"><component :is="metricIcons[key]" :size="13" :class="key"/><span>{{ label }}</span><div class="meter"><i :class="key" :style="{ width: `${n[key]}%` }"></i></div><b>{{ n[key] }}</b></div></div><div class="npc-location"><MapPin :size="13"/>{{ playbackFrames[n.id] ? (playbackFrames[n.id]!.moving ? '前往' : '到达') + places[playbackFrames[n.id]!.destination].name : places[n.place].name }}</div></button></div></section>

   <section class="events-panel dark-panel"><div class="panel-heading"><h2><ScrollText :size="18"/>最近事件</h2><button class="text-button" @click="modal = '事件日志'">全部 <ChevronRight :size="14"/></button></div><div class="event-list"><div v-for="(event, i) in world.events.slice(0,4)" :key="`${event.turn}-${i}-${event.text}`" class="event"><span class="event-turn">第{{ event.turn }}回合</span><Portrait :id="event.npc" :size="25"/><p>{{ event.text }}</p></div></div><div class="events-bottom">⌁ &nbsp; 今天 &nbsp; ⌁</div></section>

   <section class="chat-panel parchment"><div class="panel-heading"><h2><MessageCircle :size="20"/>与 {{ npc.name }} 的对话</h2><button class="text-button memory-button" @click="modal = '近期记忆'">查看记忆</button></div><div class="chat-messages" ref="messagesEl" aria-live="polite"><div v-for="(message, i) in npc.messages" :key="`${selected}-${i}`" class="chat-message" :class="message.role"><Portrait v-if="message.role === 'npc'" :id="selected" :size="31"/><div><small>{{ message.role === 'npc' ? npc.name : '你' }} <span>第{{ message.turn }}回合</span></small><p>{{ message.text }}</p></div></div></div><div class="quick-replies" :inert="ended"><button @click="send('聊聊最近的见闻吧。')"><MessageCircle :size="13"/>最近的见闻</button><button @click="send('累了就去林间休息吧。')"><TreePine :size="13"/>去休息吧</button><button @click="send('真是很棒的想法！')"><Heart :size="13"/>鼓励一下</button></div><form :inert="ended" class="chat-form" @submit.prevent="send()"><input ref="chatInput" v-model="input" maxlength="240" aria-label="对话内容" :placeholder="`和 ${npc.name} 说点什么…`"><button aria-label="发送消息" :disabled="!input.trim()"><Send :size="17"/></button></form></section>

   <section class="actions-panel dark-panel"><h2>你的行动</h2><div class="actions-grid"><button @click="chatInput?.focus()"><MessageCircle :size="22"/><span>与 NPC 对话<small>了解他们的想法</small></span></button><button :disabled="busy || ended" @click="doInteract"><Hand :size="22"/><span>进行互动<small>感受场景的影响</small></span></button><button :disabled="busy || ended" @click="doObserve"><Eye :size="22"/><span>观察场景<small>发现日常的细节</small></span></button><button class="advance-button" :disabled="!backendWorld || busy || ended" @click="nextTurn"><Play :size="22" fill="currentColor"/><span>推进回合<small>让时间继续流逝</small></span></button></div><button class="reason-button" @click="showReasons = !showReasons">{{ npc.name }} 正在{{ npc.action }} <ChevronRight :size="15" :class="{ rotated: showReasons }"/></button><p v-if="showReasons" class="reason-copy">{{ npc.reason }}</p><p v-else class="action-quote">“每一个微小的选择，<br>都可能让世界不同。”</p></section>
  </div>
  <footer class="statusbar"><span><span class="status-dot"></span>{{ backendWorld.ai.enabled ? 'AI 驱动模式 · ' + backendWorld.ai.model : 'Mock · 规则模拟' }} / FastAPI 执行</span><span>{{ ended ? '本局结局' : '世界近况' }}：{{ ecology }}</span><div><button :disabled="busy" @click="saveWorld"><Save :size="13"/>保存</button><button :disabled="busy" @click="loadWorld"><FolderOpen :size="13"/>加载</button></div></footer>
  <div v-if="notice" class="toast" role="status"><Feather :size="18"/>{{ notice }}</div>

  <dialog ref="dialog" class="town-dialog" @cancel="modal = ''" @close="modal = ''" @click="($event.target === dialog) && (modal = '')"><div class="dialog-heading"><h2>{{ modal }}</h2><button class="icon-button" aria-label="关闭弹窗" @click="modal = ''"><X :size="22"/></button></div>
   <div v-if="modal === '设置'" class="settings-content"><h3>运行模式 · {{ backendWorld.ai.enabled ? 'AI 驱动模式' : 'Mock' }}</h3><AiPanel :ai="backendWorld.ai" :busy="busy"/><p>右上角“AI模式”开关控制自由对话和下一回合的居民活动选择是否调用真实模型。已有记忆与待办保留，行动校验、执行与属性结算由后端负责。</p><p>存档保存在本机，服务重启后仍可加载。最多保留10条手动快照，可在存档列表删除；重新开始不会删除已有存档。</p><div class="dialog-buttons"><button :disabled="busy" @click="saveWorld"><Save :size="16"/>保存世界</button><button :disabled="busy" @click="loadWorld"><FolderOpen :size="16"/>加载存档</button><button :disabled="busy" @click="openSaves">存档列表</button><button :disabled="busy" @click="resetWorld()">重新开始</button></div></div>
   <InvitationPanel v-else-if="modal === '邀请链路'" :invitations="backendWorld.invitations || []" :selected="selected" @select="selectNpc"/>
   <DialoguePanel v-else-if="modal === '对话影响' && backendWorld.npcs.find(n => n.id === selected)?.last_dialogue" :trace="backendWorld.npcs.find(n => n.id === selected)!.last_dialogue!" :name="npc.name"/>
   <IntentionPanel v-else-if="modal === '长椅意图' && backendWorld.npcs.find(n => n.id === selected)?.bench_intention" :intention="backendWorld.npcs.find(n => n.id === selected)!.bench_intention!"/>
   <EndingPanel v-else-if="modal === '游戏结局' && backendWorld.ending" :ending="backendWorld.ending" :assessment="backendWorld.assessment" :busy="busy" :restart="restartEnding" @saves="openSaves"/>
   <SaveList v-else-if="modal === '存档列表'" :busy="busy" :save="saveWorld" :load="restoreSave"/>
   <div v-else-if="modal === '角色一览'" class="character-details"><button v-for="n in world.npcs" :key="n.id" class="character-detail" @click="selectNpc(n.id); modal = ''"><Portrait :id="n.id" :size="64"/><div><h3>{{ n.name }} · {{ n.personality }}</h3><p>{{ places[n.place].name }} · {{ n.action }}</p><p>{{ n.reason }}</p></div></button></div>
   <div v-else-if="modal === '事件日志'" class="full-events"><p v-for="(e,i) in world.events" :key="i"><span>第 {{ e.turn }} 回合</span>{{ e.text }}</p></div>
   <div v-else-if="modal === '近期记忆'" class="full-events"><IntentionPanel v-if="backendWorld.npcs.find(n => n.id === selected)?.bench_intention" :intention="backendWorld.npcs.find(n => n.id === selected)!.bench_intention!"/><SocialMemories :memories="backendWorld.npcs.find(n => n.id === selected)?.social_memories || []"/><h3>{{ npc.name }} 记住的经历</h3><p v-for="(m,i) in npc.memory" :key="i">{{ m }}</p><p v-if="!npc.memory.length">还没有新的共同经历，先和 {{ npc.name }} 聊聊吧。</p></div>
   <div v-else-if="modal === '世界状态'" class="world-summary"><p v-if="ended">本局结局：{{ ecology }}</p><AssessmentPanel v-if="backendWorld.assessment" :assessment="backendWorld.assessment"/><p>以下平均值仅供参考，不代替对每位居民的检查。</p><div v-for="{key,label} in metrics" :key="key"><span>平均{{ label }}</span><strong>{{ means[key] }}</strong><div class="meter"><i :class="key" :style="{ width: `${means[key]}%` }"></i></div></div><small>社交意愿代表交流倾向，不代表状态的好坏。</small></div>
   <div v-else-if="modal === '图鉴'" class="place-guide"><button v-for="(place,id) in places" :key="id" @click="selectPlace(id); modal = ''"><component :is="icons[id]" :size="30"/><div><h3>{{ place.name }}</h3><p>{{ place.desc }}</p></div></button></div>
  </dialog>
 </div>
 <div v-else class="game-shell" :aria-busy="busy"><p role="status">{{ connectionError || '正在连接小镇…' }}</p><button v-if="connectionError" @click="connect">重新连接</button></div>
</template>

<style scoped>
.session-banner{display:flex;justify-content:space-between;gap:12px;padding:10px 16px;color:#dfcda3;font-size:13px}.session-banner button{border:1px solid #aa925e;padding:5px 12px;border-radius:4px}
.save-top{display:flex;align-items:center;gap:6px;border:1px solid #aa925e;border-radius:4px;padding:7px 10px;background:#213536;color:#efdaad;white-space:nowrap}
.overview-emotion{position:absolute;left:32px;top:-22px;z-index:5}
.replay-banner{position:sticky;bottom:12px;z-index:20;background:#172e32f5;color:#f5dfaa;border:1px solid #b79a60;padding:12px 18px;border-radius:5px;display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:13px}.replay-banner button{background:#d5bb83;color:#223435;padding:7px 14px;border-radius:3px;white-space:nowrap}
</style>
