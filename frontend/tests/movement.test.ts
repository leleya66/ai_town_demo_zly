// 验证道路插值、方向及动作帧；测试不向用户现有世界提交操作。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {frameAt, facing} from '../src/movement.ts';
import type {Movement} from '../src/api.ts';
const route: Movement={npc_id:'wise',from_place_id:'library',to_place_id:'forest',points:[[195,155],[195,270],[200,270],[200,400]],duration_ms:2500};
test('movement follows the polyline by distance, without cutting the corner',()=>{
 assert.deepEqual(frameAt(route,0).point,[195,155]);
 assert.deepEqual(frameAt(route,1150).point,[195,270]);
 assert.deepEqual(frameAt(route,1200).point,[200,270]);
 assert.deepEqual(frameAt(route,1850).point,[200,335]);
 assert.equal(frameAt(route,1850).moving,true);
});
test('arrival and long background-tab delays clamp at final waypoint',()=>{
 assert.deepEqual(frameAt(route,2500).point,[200,400]);
 assert.equal(frameAt(route,2500).moving,false);
 assert.deepEqual(frameAt(route,60000).point,[200,400]);
 assert.deepEqual(frameAt(route,-5).point,[195,155]);
});
test('stationary residents do not animate or divide by zero',()=>{
 const frame=frameAt({...route,points:[[200,400]],duration_ms:0},0);
 assert.deepEqual(frame.point,[200,400]);assert.equal(frame.moving,false);
});
test('four directions follow the active road segment and arrival keeps its facing',()=>{
 assert.equal(frameAt(route,100).direction,'down');
 assert.equal(frameAt(route,1160).direction,'right');
 assert.equal(frameAt(route,2500).direction,'down');
 const reverse={...route,points:[...route.points].reverse()};
 assert.equal(frameAt(reverse,100).direction,'up');
 assert.equal(frameAt(reverse,1320).direction,'left');
 assert.equal(frameAt(reverse,2500).direction,'up');
 assert.equal(facing(-10,2),'left');assert.equal(facing(2,-10),'up');
});
test('walking alternates actual poses, while arrival and stationary frames are idle',()=>{
 assert.deepEqual([0,160,320,480,640].map(t=>frameAt(route,t).pose),[0,1,0,2,0]);
 assert.equal(frameAt(route,2500).pose,0);
 assert.equal(frameAt({...route,points:[[0,0]],duration_ms:0},480).pose,0);
});
