# FastAPI 后端

当前主线后端入口为 `backend.main:app`。后端负责世界状态、四条专属事件、邀请/回应/赴约、NPC 感知与自主决策、LLM/Mock 选择、统一 Simulation 结算、贡献榜、幂等、revision 与 SQLite 手动存档。

请从项目根目录启动：

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

无 API Key 时可使用 Mock 模式完整体验。真实模型配置见根目录 `.env.example`。不要在前端或仓库中提交真实密钥。

后端完整架构、AI/Mock 边界、四事件规则、一致性与生产化取舍见 [根目录 README 的技术设计章节](../README.md#10-技术设计)，完整启动与演示入口见 [`../README.md`](../README.md)。

测试：

```powershell
$env:LLM_ENABLED='false'
.venv\Scripts\python.exe -m unittest discover -s backend -t . -p "test_*.py"
```
