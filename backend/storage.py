"""使用 SQLite 保存和读取独立世界快照，提供历史存档列表；不决定游戏行为。"""
from uuid import uuid4
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

MAX_SAVES = 10


class SaveLimitReached(Exception):
    """容量已满；不覆盖或删除任何已有快照。"""


DB_PATH = Path(os.environ.get('TOWN_SAVE_DB', Path(__file__).parent / 'data' / 'saves.sqlite3'))


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS saves (id TEXT PRIMARY KEY, saved_at TEXT NOT NULL, snapshot TEXT NOT NULL)')
            yield db
    finally:
        db.close()


def save(world):
    """每次保存写入独立快照；事务失败时由调用方报告错误。"""
    with connect() as db:
        # 写锁覆盖计数和插入，两个并发保存也不能突破容量。
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT COUNT(*) FROM saves').fetchone()[0] >= MAX_SAVES:
            raise SaveLimitReached()
        db.execute('INSERT INTO saves VALUES (?, ?, ?)', (str(uuid4()), datetime.now(timezone.utc).isoformat(), json.dumps(world, ensure_ascii=False)))


def read(world_id):
    """兼容按快照ID加载或按世界ID读取最近存档的现有接口。"""
    with connect() as db:
        row = db.execute("SELECT snapshot FROM saves WHERE id = ? OR json_extract(snapshot, '$.world_id') = ? ORDER BY saved_at DESC LIMIT 1", (world_id, world_id)).fetchone()
    return json.loads(row[0]) if row else None


def listing():
    with connect() as db:
        rows = db.execute('SELECT id, saved_at, snapshot FROM saves ORDER BY saved_at DESC').fetchall()
    return [dict(id=key, saved_at=stamp, turn=json.loads(snapshot)['turn']) for key, stamp, snapshot in rows]


def delete(save_id):
    """只删除准确的快照ID；重复删除幂等，不影响内存世界。"""
    with connect() as db:
        db.execute("DELETE FROM saves WHERE id = ?", (save_id,))
