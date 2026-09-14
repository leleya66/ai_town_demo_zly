// 验证展示元数据与空加载状态，防止前端重新引入独立游戏结算。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {emptyWorld, places, metrics} from '../src/world.ts';

test('connection placeholder does not invent residents or game history',()=>{
 const world=emptyWorld();
 assert.deepEqual(world.npcs,[]);assert.deepEqual(world.events,[]);assert.deepEqual(world.tasks,[]);
 const another=emptyWorld();assert.notEqual(world.tasks,another.tasks);
});
test('scene metadata provides four display anchors without independent numeric rules',()=>{
 assert.equal(Object.keys(places).length,4);
 for(const place of Object.values(places)){
  assert.ok(place.name && place.image);assert.ok(place.x>=0&&place.x<=100&&place.y>=0&&place.y<=100);
  assert.equal('effects' in place,false);
 }
 assert.deepEqual(metrics.map(m=>m.key),['energy','mood','social']);
});
