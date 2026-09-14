// 根据后端路线计算人物展示位置、朝向与动作帧；移动结束后固定在终点。
import type { Movement, Point } from './api';
export type Facing = 'down' | 'left' | 'right' | 'up';
export interface Frame { point: Point; moving: boolean; destination: Movement['to_place_id']; direction: Facing; pose: number }
export function facing(dx: number, dy: number): Facing {
 return Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down');
}
export function frameAt(route: Movement, elapsed: number): Frame {
 const points = route.points;
 const lengths = points.slice(1).map((b,i)=>Math.hypot(b[0]-points[i]![0],b[1]-points[i]![1]));
 const total = lengths.reduce((a,b)=>a+b,0);
 let remaining = total * Math.min(1, Math.max(0, elapsed / Math.max(1,route.duration_ms)));
 for(let i=0;i<lengths.length;i++) {
  const length = lengths[i]!;
  if(remaining < length) {
   const a=points[i]!, b=points[i+1]!, t=remaining/length;
   return {point:[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t],moving:true,destination:route.to_place_id,direction:facing(b[0]-a[0],b[1]-a[1]),pose:[0,1,0,2][Math.floor(Math.max(0,elapsed)/160)%4]!};
  }
  remaining-=length;
 }
 let last = lengths.length - 1;
 while(last >= 0 && lengths[last] === 0) last--;
 return {point:points.at(-1) ?? [0,0],moving:false,destination:route.to_place_id,direction:last<0 ? 'down' : facing(points[last+1]![0]-points[last]![0],points[last+1]![1]-points[last]![1]),pose:0};
}
