// 管理后端路线的动画回放与临时表情；只改变展示状态，不结算游戏数据。
import { ref, onBeforeUnmount } from 'vue';
import { frameAt, type Frame } from '../movement';
import type { BackendWorld, Expression, Movement } from '../api';
import type { NpcId } from '../world';

export function usePlayback(onStart: () => void) {
 const replaying = ref(false);
 const playbackRoutes = ref<Movement[]>([]);
 const playbackFrames = ref<Partial<Record<NpcId, Frame>>>({});
 const expressions = ref<Partial<Record<NpcId, Expression>>>({});
 const expressionTimers = new Map<NpcId, ReturnType<typeof setTimeout>>();
 const seenExpressions = new Set<string>();
 function clearExpressions() {
  expressionTimers.forEach(clearTimeout); expressionTimers.clear(); expressions.value = {};
 }
 // 同一交流事件只显示一次，新气泡覆盖该居民的旧气泡并定时清理。
 function showExpressions(cues: Expression[] = []) {
  for (const cue of cues) {
   if (seenExpressions.has(cue.id)) continue;
   seenExpressions.add(cue.id);
   if (seenExpressions.size > 200) seenExpressions.delete(seenExpressions.values().next().value!);
   clearTimeout(expressionTimers.get(cue.npc_id)); expressions.value[cue.npc_id] = cue;
   expressionTimers.set(cue.npc_id,setTimeout(()=>{ delete expressions.value[cue.npc_id]; expressionTimers.delete(cue.npc_id); },5000));
  }
 }
 onBeforeUnmount(clearExpressions);
 let finishPlayback: (()=>void) | null = null;
 function skipPlayback() { finishPlayback?.(); }
 // 按后端时长回放路线；跳过动画不发送第二次结算请求。
 async function playTurn(value: BackendWorld) {
  const routes = value.last_movements;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const duration = Math.max(0, ...routes.map(r=>r.duration_ms));
  if (duration === 0) return;
  onStart(); replaying.value = true; playbackRoutes.value = routes;
  await new Promise<void>(resolve => {
   const started = performance.now(); let animation = 0;
   const finish = () => { cancelAnimationFrame(animation); replaying.value=false; playbackFrames.value={}; playbackRoutes.value=[]; finishPlayback=null; resolve(); };
   finishPlayback = finish;
   const draw = (now: number) => {
    const elapsed=now-started;
    playbackFrames.value=Object.fromEntries(routes.map(route=>[route.npc_id,frameAt(route,elapsed)]));
    if(elapsed>=duration+350) finish(); else animation=requestAnimationFrame(draw);
   };
   draw(started);
  });
 }
 onBeforeUnmount(skipPlayback);
 return {replaying, playbackRoutes, playbackFrames, expressions, clearExpressions, showExpressions, playTurn, skipPlayback};
}
