# Vue 3 + TypeScript 前端

当前正式前端入口为 `src/main.ts -> App.vue`，世界通信集中在 `composables/useWorld.ts`，移动回放在 `composables/usePlayback.ts`。页面展示四名居民、地图、四条专属事件、邀请与回应、自然语言对话、AI/Mock 状态、贡献排行、存档和六回合结局。

前端只负责交互与回放；活动是否合法、邀请是否完成、属性变化和计分均由 FastAPI 后端决定。

启动：

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5174 --strictPort
```

浏览器访问 `http://127.0.0.1:5174/`。Vite 将 `/api` 代理到 `http://127.0.0.1:8000`。

验证：

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

完整架构、AI 与 Mock 差异以及四事件设计见 [根目录 README 的技术设计章节](../README.md#10-技术设计)。
