// 配置 Vue 构建插件和本地 API 代理，前端请求统一交给 FastAPI 服务。
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({ plugins: [vue()], server: { proxy: { '/api': 'http://127.0.0.1:8000' } } });
