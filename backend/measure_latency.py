"""在独立世界测量对话、回合接口耗时与动画时长；断言真实来源，不读写手动存档或输出密钥。"""
import json
import time
from pathlib import Path
from uuid import uuid4
import httpx


def main():
    rows = []
    with httpx.Client(base_url='http://127.0.0.1:8000/api', timeout=125, trust_env=False) as client:
        for enabled in (False, True, True):
            response = client.post('/worlds'); response.raise_for_status()
            world = response.json()

            def command(route, **payload):
                nonlocal world
                start = time.perf_counter()
                body={**payload, 'request_id':str(uuid4()), 'expected_revision':world['revision']}
                path=f"/worlds/{world['world_id']}/{route}"
                timing={};data=None
                if route=='turns' or payload.get('type')=='message':
                    with client.stream('POST',path+'/stream',json=body) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line.startswith('data: '):continue
                            event=json.loads(line[6:])
                            timing.setdefault('first_feedback_seconds',round(time.perf_counter()-start,3))
                            if event['type']=='draft':timing.setdefault('first_text_seconds',round(time.perf_counter()-start,3))
                            if event['type']=='error':raise RuntimeError(event['message'])
                            if event['type']=='result':data=event['data']
                    assert data is not None, 'SSE没有最终结果'
                else:
                    response=client.post(path,json=body);response.raise_for_status();data=response.json()
                world = data['world']
                return round(time.perf_counter()-start, 3), data['result'],timing

            command('ai-mode', enabled=enabled)
            seconds, result, timing = command('commands', type='message', npc_id='wise', text='不用去休息，我想请你准备一次读书分享。')
            trace = result['dialogue']
            assert trace['source'] in ('ai', 'rules')
            if enabled and trace['source']=='rules':
                assert trace['fallback_reason']
            rows.append(dict(mode='ai' if enabled else 'mock', operation='dialogue', seconds=seconds,
                             source=trace['source'], fallback=trace['fallback_reason'],**timing))
            seconds, result, timing = command('turns')
            assert len(world['last_decisions']) == 4
            rows.append(dict(mode='ai' if enabled else 'mock', operation='turn', seconds=seconds,
                             ai_count=sum(d['source']=='ai' for d in world['last_decisions']),
                             animation_seconds=max(m['duration_ms'] for m in result['movements'])/1000,**timing))
            print(json.dumps(rows[-2:], ensure_ascii=False), flush=True)
    output = Path('test-results/latency-report.json')
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
