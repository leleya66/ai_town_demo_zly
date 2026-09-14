"""FastAPI 入口：声明接口并把请求交给世界服务、建议决策和回合结算模块。"""
import os
import sqlite3
from copy import deepcopy
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import storage
from backend.models import Command, Suggestion, LegacyCommand, AiMode, Support
from backend.festival import support
from backend.ai_mode import set_mode
from backend.world import fresh_world, fail
from backend.service import worlds, lock, get_store, mutate, enrich
from backend.decisions import submit_suggestion
from backend.simulation import advance_world
from backend.commands import execute_command
from backend.streaming import response as stream_response


app = FastAPI(title='AI 小镇 · 规则建议与回合 API')

# 本地开发默认允许 Vite；Render/生产环境通过 CORS_ORIGINS 增加正式前端域名。
# 例如：CORS_ORIGINS=https://ai-town-web-zly.onrender.com
cors_origins = [
    origin.strip().rstrip('/')
    for origin in os.getenv(
        'CORS_ORIGINS',
        'http://127.0.0.1:5174,http://localhost:5174',
    ).split(',')
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.post('/api/worlds/{world_id}/commands/stream')
def command_stream(world_id: str, cmd: LegacyCommand):
    return stream_response(lambda: mutate(world_id, cmd, lambda w: execute_command(w, cmd), 'legacy'))


@app.post('/api/worlds/{world_id}/turns/stream')
def turn_stream(world_id: str, cmd: Command):
    return stream_response(lambda: mutate(world_id, cmd, advance_world, 'turn'))


@app.get('/api/health')
def health():
    return {'status': 'ok', 'mode': 'rules'}


@app.get('/api/saves')
def list_saves():
    return storage.listing()


@app.post('/api/worlds', status_code=201)
def create_world():
    with lock:
        world_id = str(uuid4())
        worlds[world_id] = dict(world=fresh_world(world_id), requests={})
        enrich(worlds[world_id]['world'])
        return deepcopy(worlds[world_id]['world'])


@app.get('/api/worlds/{world_id}')
def read_world(world_id: str):
    with lock:
        return deepcopy(get_store(world_id)['world'])


@app.post('/api/worlds/{world_id}/actions')
def suggest(world_id: str, cmd: Suggestion):
    return mutate(world_id, cmd, lambda w: submit_suggestion(w, cmd), 'suggest')


@app.post('/api/worlds/{world_id}/turns')
def turn(world_id: str, cmd: Command):
    return mutate(world_id, cmd, advance_world, 'turn')


@app.post('/api/worlds/{world_id}/ai-mode')
def ai_mode(world_id: str, cmd: AiMode):
    return mutate(world_id, cmd, lambda world: set_mode(world, cmd.enabled), 'ai_mode')


@app.post('/api/worlds/{world_id}/support')
def choose_support(world_id: str, cmd: Support):
    return mutate(world_id, cmd, lambda world: support(world, cmd.npc_id), 'support')


@app.post('/api/worlds/{world_id}/comparisons')
def compare(world_id: str, cmd: Command):
    # 从同一快照复制独立世界；不重置原世界、不读取或覆盖存档。重复请求返回原对照ID。
    def fork(world):
        ids = {}
        for mode in ('mock', 'ai'):
            key = str(uuid4())
            branch = deepcopy(world)
            branch.update(world_id=key, revision=0, ai_enabled=mode == 'ai')
            enrich(branch)
            worlds[key] = dict(world=branch, requests={})
            ids[mode] = key
        return dict(message='已创建同起点的两个独立世界；原世界保留。', comparison=ids)

    return mutate(world_id, cmd, fork, 'comparison')


@app.post('/api/worlds/{world_id}/commands')
def command(world_id: str, cmd: LegacyCommand):
    return mutate(world_id, cmd, lambda world: execute_command(world, cmd), 'legacy')


@app.delete('/api/saves/{save_id}')
def delete_save(save_id: str):
    try:
        storage.delete(save_id)
    except (OSError, sqlite3.Error):
        fail(503, '删除失败，请稍后重试。')
    return {'message': '存档已删除。'}
