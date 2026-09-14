<!-- 展示居民生活地图、道路回放、长椅和表情；位置与事件状态来自后端。 -->
<script setup lang="ts">
import { computed } from 'vue';
import type { BenchEvent, Expression, Movement, Point } from '../api';
import { frameAt, type Frame } from '../movement';
import spriteFrames from '../sprite-frames.json';
import EmotionBubble from './EmotionBubble.vue';
import { places } from '../world';
import type { Npc, NpcId, PlaceId } from '../world';
const props = defineProps<{ npcs: Npc[]; selected: NpcId; selectedPlace: PlaceId; positions: Partial<Record<NpcId,Point>>; bench?: BenchEvent; frames: Partial<Record<NpcId,Frame>>; routes: Movement[]; lastRoutes: Movement[]; expressions: Partial<Record<NpcId,Expression>> }>();
const emit = defineEmits<{ 'select-npc': [id: NpcId]; 'select-place': [id: PlaceId]; 'inspect-bench': [] }>();
const directionColumns = { down: 0, left: 1, right: 2, up: 3 };
// 地点标签和人物共用800×600坐标，避免背景缩放后位置偏移。
const areas: { id: PlaceId; name: string; x: number; y: number; anchor: [number, number] }[] = [
 { id: 'library', name: '图书馆', x: 105, y: 65, anchor: [128, 108] },
 { id: 'plaza', name: '中心广场', x: 515, y: 115, anchor: [540, 153] },
 { id: 'forest', name: '林间', x: 100, y: 358, anchor: [130, 402] },
 { id: 'workshop', name: '老旧工坊', x: 520, y: 373, anchor: [549, 415] },
];
const people = computed(() => props.npcs.map(n => {
 const frame=props.frames[n.id];
 const area=areas.find(a=>a.id===n.place)!;
 const point=frame?.point ?? props.positions[n.id] ?? [area.anchor[0]+5,area.anchor[1]+61];
 const lastRoute=props.lastRoutes.find(r=>r.npc_id===n.id);
 const direction=frame?.direction ?? (lastRoute ? frameAt(lastRoute,Infinity).direction : 'down');
 const pose=frame?.pose ?? 0;
 return {...n,direction,pose,column:directionColumns[direction],spriteViewBox:spriteFrames[n.id][pose]![directionColumns[direction]],x:point[0],y:point[1],moving:frame?.moving ?? false,displayPlace:frame ? (frame.moving ? 'moving' : frame.destination) : n.place,displayAction:frame?.moving ? `前往${places[frame.destination].name}` : frame ? '已到达，等待结算' : n.action};
}).sort((a,b)=>a.y-b.y));
const selectedRoute = computed(()=>props.routes.find(r=>r.npc_id===props.selected && r.points.length>1));
</script>
<template>
 <div class="life-map"><svg viewBox="0 0 800 600" role="group" aria-label="中世纪奇幻居民生活地图，开放图书馆、广场、林间与工坊由道路连接">
  <image class="life-map-art" href="/assets/life-map-interiors.png" width="800" height="600" preserveAspectRatio="xMidYMid meet"/>
  <polyline v-if="selectedRoute" class="resident-route" :points="selectedRoute.points.map(p=>p.join(',')).join(' ')" fill="none" stroke="#ffe2a0" stroke-width="3" stroke-dasharray="7 5"/>
  <g class="forest-bench" :data-state="bench?.status ?? 'broken'" transform="translate(245 448)">
   <ellipse cy="10" rx="35" ry="10" fill="#15271966"/>
   <path d="M-25 4v13M25 4v13" stroke="#353f38" stroke-width="5"/>
   <path d="M-29 -7v18M29 -7v18" stroke="#705039" stroke-width="4"/>
   <g v-if="bench?.status === 'repaired'" fill="#b78247" stroke="#68462b" stroke-width="1.4">
    <rect x="-30" y="-16" width="60" height="6" rx="2"/><rect x="-30" y="-8" width="60" height="6" rx="2"/>
    <path d="M-30 1H30L34 8H-34Z" fill="#cf9b60"/>
    <path d="M-25 -13H25M-25 -5H25M-24 4H24" stroke="#edc48a" stroke-width=".7"/>
   </g>
   <g v-else fill="#826346" stroke="#493d30" stroke-width="1.5">
    <path d="M-30 -16H-5L-12 -10H-30Z M8 -16H30V-10H3Z"/>
    <path d="M-30 1H-9L-15 8H-34Z M8 1H30L34 8H16Z"/>
    <path v-if="bench?.status === 'repairing'" d="M-30 -8H30V-2H-30Z" fill="#bd925e"/>
    <path v-else d="M-15 -5L22 13L18 18L-19 0Z"/>
   </g>
   <foreignObject x="-47" y="20" width="94" height="28"><button class="bench-label" @click.stop="emit('inspect-bench')" :aria-label="bench?.status === 'repaired' ? '查看已修好的林间长椅' : '观察林间长椅'">{{ bench?.status === 'repaired' ? '长椅 · 可休憩' : bench?.status === 'repairing' ? `修缮中 · ${bench.progress}/${bench.required}` : '损坏的长椅' }}</button></foreignObject>
  </g>
  <g v-for="area in areas" :key="area.id"><foreignObject :x="area.x" :y="area.y" width="165" height="31"><button class="life-place-label" :class="{ active: selectedPlace === area.id }" :aria-label="`查看${area.name}`" :aria-pressed="selectedPlace === area.id" @click.stop="emit('select-place', area.id)">{{ area.name }} <span>{{ people.filter(n => n.displayPlace === area.id).length }} 位居民</span></button></foreignObject></g>
  <g v-for="person in people" :key="person.id" class="life-resident" :data-life-npc="person.id" :data-place="person.displayPlace" :data-moving="person.moving" :data-direction="person.direction" :data-pose="person.pose" :data-x="person.x" :data-y="person.y">
   <foreignObject :x="person.x - 30" :y="person.y - 61" width="100" height="100"><button class="life-person" :class="{ active: selected === person.id, walking: person.moving }" :aria-pressed="selected === person.id" :aria-label="`选择 ${person.name}：${person.displayAction}`" :title="`${person.name} · ${person.displayAction}`" @click.stop="emit('select-npc', person.id)"><span class="resident-shadow" aria-hidden="true"/><svg class="resident-sprite" :data-sprite="person.id" :viewBox="person.spriteViewBox" aria-hidden="true"><defs><clipPath :id="`sprite-clip-${person.id}`"><rect :x="person.column * 256" :y="[0,540,1020][person.pose]" width="256" :height="[540,480,516][person.pose]"/></clipPath></defs><image :clip-path="`url(#sprite-clip-${person.id})`" :href="`/assets/npc-${person.id}-walk.png`" width="1024" height="1536"/></svg><span class="life-name">{{ person.name }}<small v-if="person.moving">{{ person.displayAction }}</small></span></button></foreignObject>
  </g>
  <g class="resident-emotions" style="pointer-events:none"><template v-for="person in people" :key="person.id"><foreignObject v-if="expressions[person.id]" :x="person.x + 17" :y="person.y - 72" width="48" height="43"><EmotionBubble :cue="expressions[person.id]!"/></foreignObject></template></g>
 </svg></div>
</template>
<style scoped>
.life-map{height:100%;width:100%;background:radial-gradient(ellipse,#536049,#202e26);display:flex;align-items:center;padding:46px 6px 27px}.life-map>svg{width:100%;height:100%;display:block;overflow:visible}.life-place-label{width:100%;height:29px;border:1px solid #c7a66e;border-radius:3px;background:linear-gradient(100deg,#192c29ee,#24372ce8);color:#ebdfbe;font:600 14px 'Noto Serif SC',serif;display:flex;align-items:center;justify-content:space-between;padding:0 9px;box-shadow:0 3px 8px #0005}.life-place-label span{font:10px 'Microsoft YaHei',sans-serif;color:#d0d0b5}.life-place-label.active{background:linear-gradient(100deg,#594d31f5,#2c3c2ee8);border-color:#f1d497}.life-person:focus-visible,.life-place-label:focus-visible{outline:2px solid #ffdc88;outline-offset:-2px}
</style>
<style scoped>
/* 按居民、朝向和姿态裁切独立图集，统一脚底锚点，避免换帧时跳动。 */
.life-person{position:relative;width:60px;height:82px;display:flex;flex-direction:column;gap:0;align-items:center;justify-content:flex-start;padding:0;border:0;border-radius:5px;background:transparent;box-shadow:none;cursor:pointer}
.life-person.active{background:transparent;border:0;box-shadow:none}
.resident-sprite{position:relative;z-index:1;display:block;flex:none;width:38px;height:61px;overflow:hidden;filter:drop-shadow(0 1px 1px #14221cb3)}
.resident-shadow{position:absolute;top:57px;left:15px;width:30px;height:10px;border-radius:50%;background:#15231966;border:1px solid transparent}
.life-person.active .resident-shadow{background:#edcd7c55;border-color:#ffe0a0;box-shadow:0 0 5px #f4d88d}
.life-name{position:relative;z-index:2;margin-top:-3px;padding:1px 6px;border-radius:3px;border:1px solid #a8976c88;background:#182b25e8;color:#fff0ce;font:600 11px/14px 'Microsoft YaHei',sans-serif;text-shadow:0 1px 2px #000}
.life-person.active .life-name{border-color:#efce8b;color:#ffdf97}
.life-person:hover .resident-sprite{filter:drop-shadow(0 0 2px #ffe4a4)}
</style>

<style scoped>
.resident-route{pointer-events:none;filter:drop-shadow(0 1px 2px #25322b)}
.life-resident foreignObject{pointer-events:none}.life-person{pointer-events:auto}
.bench-label{background:#20362fe8;border:1px solid #c4a476;border-radius:3px;color:#f3dfb4;font-size:10px;padding:4px 5px;width:94px}
.life-name small{display:block;font-size:9px;white-space:nowrap;color:#ffe4ab;line-height:12px}

</style>
