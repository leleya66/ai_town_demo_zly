// 管理世界连接、请求互斥和后端结果应用；所有游戏写操作均通过 API 完成。
import { ref, onMounted } from 'vue';
import { api, type BackendWorld, type Reply } from '../api';
import { emptyWorld } from '../world';
import { usePlayback } from './usePlayback';
import { streamApi, type StreamEvent } from '../stream';

export function useWorld(onMovement: () => void, onWorldUpdated: (world: BackendWorld) => void, notify: (text: string) => void) {
  const playback = usePlayback(onMovement);
  const { clearExpressions, showExpressions, playTurn } = playback;
 const world = ref(emptyWorld());
 const backendWorld = ref<BackendWorld | null>(null);
 const busy = ref(false); const connectionError = ref(''); const suggestionReply = ref<Reply | null>(null);
 const streamStatus=ref(''); const streamDraft=ref(''); const streamInput=ref('');
 function applyWorld(value: BackendWorld) { backendWorld.value = value; world.value = value; }
 async function connect() {
  clearExpressions();
  busy.value = true; connectionError.value = '';
  try {
   const explicitId = new URLSearchParams(location.search).get('world');
   const id = explicitId || sessionStorage.getItem('town-world-id');
   let value: BackendWorld;
   if (id) { try { value = await api<BackendWorld>(`/worlds/${id}`); } catch (error) { if (explicitId) throw error; value = await api<BackendWorld>('/worlds', {}); } }
   else value = await api<BackendWorld>('/worlds', {});
   applyWorld(value); sessionStorage.setItem('town-world-id', value.world_id);
  } catch { connectionError.value = '后端未连接，请启动 FastAPI 服务后重试。'; }
  finally { busy.value = false; }
 }
 onMounted(connect);
 // SSE草稿不改变世界；最终结果先展示，再并行回放路线，写操作仍互斥。
 async function command(route: string, payload: Record<string, unknown> = {}) {
  if (busy.value || !backendWorld.value) return;
  busy.value = true;
  streamDraft.value='';streamInput.value=payload.type==='message'?String(payload.text||''):'';
  streamStatus.value='已发送，等待服务响应';
  const completed=new Set<string>();
  function onEvent(event:StreamEvent){
   if(event.type==='progress')streamStatus.value=event.message||'';
   if(event.type==='draft'){streamDraft.value=event.text||'';streamStatus.value='正在生成回复';}
   if(event.type==='decision'){completed.add(event.npc_id!);streamStatus.value=`居民选择已返回 ${completed.size}/4 · ${event.npc_id} ${event.source==='ai'?'AI选择':'规则降级'}`;}
  }
  try {
   const path=`/worlds/${backendWorld.value.world_id}/${route}`;
   const body={ ...payload, request_id: crypto.randomUUID(), expected_revision: backendWorld.value.revision };
   const data = await (route==='turns'||payload.type==='message' ? streamApi<{world: BackendWorld; result: Reply}>(path,body,onEvent) : api<{world: BackendWorld; result: Reply}>(path,body));
   if (payload.type === 'load' || payload.type === 'reset' || payload.type === 'save_restart') clearExpressions();
   applyWorld(data.world); onWorldUpdated(data.world);
   streamDraft.value=''; streamStatus.value='';
   if (route === 'turns') { clearExpressions(); await playTurn(data.world); }
   showExpressions(data.result.expressions);
   if (data.result.outcome) suggestionReply.value = data.result;
   return data.result;
  } catch (error) {
   notify(error instanceof Error ? error.message : '操作失败，请重试。');
   try { applyWorld(await api<BackendWorld>(`/worlds/${backendWorld.value.world_id}`)); } catch { connectionError.value = '后端连接中断，请重新连接。'; }
  } finally { busy.value = false; streamStatus.value='';streamDraft.value='';streamInput.value=''; }
 }
 async function suggest(payload: Record<string, unknown>) { suggestionReply.value = null; await command('actions', payload); }
 return { world, backendWorld, busy, connectionError, suggestionReply, streamStatus, streamDraft, streamInput, connect, command, suggest, ...playback };
}
