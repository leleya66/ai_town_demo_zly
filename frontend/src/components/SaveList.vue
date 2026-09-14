<!-- 管理手动存档列表与删除确认；容量由后端强制执行，加载和保存复用世界命令。 -->
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../api';
const props = defineProps<{ busy: boolean; save: () => Promise<boolean>; load: (id: string) => Promise<void> }>();
const saves = ref<{id:string;turn:number;saved_at:string}[]>([]);
const error = ref(''); const loading = ref(false); const confirmId = ref<string | null>(null);
async function refresh() {
 loading.value = true;
 try { saves.value = await api('/saves'); error.value = ''; }
 catch (e) { error.value = e instanceof Error ? e.message : '存档读取失败'; }
 finally { loading.value = false; }
}
async function saveCurrent() {
 if (await props.save()) await refresh();
 else { await refresh(); error.value = saves.value.length >= 10 ? '存档已满，请先删除旧存档。' : '保存失败，请检查磁盘空间或稍后重试。'; }
}
async function remove(id: string) {
 loading.value = true;
 try { await api(`/saves/${encodeURIComponent(id)}`, undefined, 'DELETE'); confirmId.value = null; await refresh(); }
 catch (e) { error.value = e instanceof Error ? e.message : '删除失败'; }
 finally { loading.value = false; }
}
onMounted(refresh);
</script>
<template>
 <section class="save-list" aria-label="手动存档列表">
  <p>手动存档 · 已使用 {{ saves.length }} / 10。满额后请先删除旧存档。</p>
  <button :disabled="busy || loading || saves.length >= 10" @click="saveCurrent">存档当前进度</button>
  <p v-if="loading" role="status">正在更新存档列表…</p>
  <p v-if="error" role="alert">{{ error }} <button @click="refresh">重试</button></p>
  <p v-else-if="!loading && !saves.length">暂无存档。</p>
  <article v-for="save in saves" :key="save.id" class="save-entry">
   <p>第 {{ save.turn }} 回合 · {{ new Date(save.saved_at).toLocaleString() }}</p>
   <button :disabled="busy || loading" @click="load(save.id)">加载此存档</button>
   <button :disabled="busy || loading" @click="confirmId = save.id">删除存档</button>
   <div v-if="confirmId === save.id" role="group" aria-label="删除确认">
    <p>确认删除上方第 {{ save.turn }} 回合快照？无法撤销，当前游戏进度不受影响。</p>
    <button :disabled="busy || loading" @click="remove(save.id)">确认删除</button>
    <button :disabled="loading" @click="confirmId = null">取消</button>
   </div>
  </article>
 </section>
</template>
<style scoped>
.save-list{line-height:1.8;padding:0 22px 20px}.save-list button{padding:7px 12px;margin:4px;border:1px solid #ad935e;border-radius:4px}.save-entry{padding:10px 0;border-top:1px solid #ad935e55}.save-entry p{margin:5px 0}.save-entry [role=group]{background:#49362e44;padding:10px}
</style>
