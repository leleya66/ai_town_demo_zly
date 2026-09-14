"""将事务进度和未确认回复通过 SSE 推送；断线不重复执行，最终结果仍由世界事务原子提交。"""
import json
import re
from contextvars import ContextVar
from queue import Queue, Empty
from threading import Thread, Event
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

observer = ContextVar('stream_observer', default=None)


def emit(kind, **data):
    callback = observer.get()
    if callback:
        callback(dict(type=kind, **data))


def reply_prefix(text):
    """只解析reply字符串已到达的部分，绝不向界面发送JSON、转义残片或模型推理。"""
    match = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)', text)
    if not match:
        return ''
    value = match.group(1)
    # 一个网络块可能停在Unicode转义中间；最多退让一个转义长度。
    for trim in range(min(7, len(value)+1)):
        try:
            decoded = json.loads('"'+(value[:-trim] if trim else value)+'"')
            decoded.encode('utf-8')  # 半个emoji代理对不能作为UTF-8事件发送。
            return decoded
        except ValueError:
            continue
    return ''


def response(operation):
    queue = Queue()
    disconnected = Event()

    def publish(event):
        if not disconnected.is_set():
            queue.put(event)

    def run():
        token = observer.set(publish)
        try:
            publish(dict(type='progress', message='已收到，正在读取世界状态'))
            result = operation()
            publish(dict(type='result', data=result))
        except HTTPException as exc:
            publish(dict(type='error', message=str(exc.detail), status=exc.status_code))
        except Exception:
            publish(dict(type='error', message='本次操作失败，未提交新的世界状态', status=500))
        finally:
            observer.reset(token)
            publish(None)

    def events():
        Thread(target=run, daemon=True).start()
        try:
            while True:
                try:
                    event = queue.get(timeout=10)
                except Empty:
                    yield ': heartbeat\n\n'
                    continue
                if event is None:
                    return
                yield 'data: '+json.dumps(event, ensure_ascii=False)+'\n\n'
        finally:
            # 已接受的事务继续完成；客户端以相同request_id重试可取回唯一结果。
            disconnected.set()

    return StreamingResponse(events(), media_type='text/event-stream',
                             headers={'Cache-Control':'no-cache', 'X-Accel-Buffering':'no'})
