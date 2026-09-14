// 解析POST请求返回的SSE事件，处理跨块UTF-8、心跳、错误和唯一最终结果。
import { API_BASE_URL } from './api';

export interface StreamEvent {type:string; text?:string; message?:string; npc_id?:string; source?:string; fallback_reason?:string; data?:unknown}

export async function readEvents<T>(body: ReadableStream<Uint8Array>, onEvent:(event:StreamEvent)=>void):Promise<T> {
  const reader=body.getReader();
  const decoder=new TextDecoder();
  let buffer='';

  try {
    while(true){
      const {value,done}=await reader.read();
      buffer+=decoder.decode(value,{stream:!done});
      let boundary;

      while((boundary=buffer.indexOf('\n\n'))>=0){
        const packet=buffer.slice(0,boundary);
        buffer=buffer.slice(boundary+2);
        const data=packet
          .split('\n')
          .filter(line=>line.startsWith('data:'))
          .map(line=>line.slice(5).trimStart())
          .join('\n');

        if(!data)continue;

        const event=JSON.parse(data) as StreamEvent;
        if(event.type==='error')throw new Error(event.message||'操作失败');
        onEvent(event);
        if(event.type==='result')return event.data as T;
      }

      if(done)throw new Error('连接已中断，正在核对已提交的世界状态，请勿重复点击');
    }
  } finally {
    await reader.cancel().catch(()=>{});
    reader.releaseLock();
  }
}

export async function streamApi<T>(path:string,payload:unknown,onEvent:(event:StreamEvent)=>void):Promise<T>{
  const response=await fetch(`${API_BASE_URL}/api${path}/stream`,{
    method:'POST',
    headers:{
      'Content-Type':'application/json',
      Accept:'text/event-stream',
    },
    body:JSON.stringify(payload),
    signal:AbortSignal.timeout(125000),
  });

  if(!response.ok||!response.body)throw new Error('流式请求失败，请检查连接');
  return readEvents<T>(response.body,onEvent);
}
