// 验证SSE在任意网络切块下只产生一次最终结果，错误/断线不能当成成功。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readEvents } from '../src/stream.ts';
function bytes(text:string){const data=new TextEncoder().encode(text);return new ReadableStream<Uint8Array>({start(c){for(const b of data)c.enqueue(new Uint8Array([b]));c.close();}});}
test('SSE handles split Chinese, draft and final state',async()=>{
 const events:string[]=[];
 const result=await readEvents(bytes(': heartbeat\n\ndata: {"type":"draft","text":"你好"}\n\ndata: {"type":"result","data":{"revision":1}}\n\n'),e=>events.push(e.type));
 assert.deepEqual(result,{revision:1});assert.deepEqual(events,['draft','result']);
});
test('SSE error and missing final result reject',async()=>{
 await assert.rejects(readEvents(bytes('data: {"type":"error","message":"旧版本"}\n\n'),()=>{}),/旧版本/);
 await assert.rejects(readEvents(bytes('data: {"type":"draft","text":"未确认"}\n\n'),()=>{}),/中断/);
});
