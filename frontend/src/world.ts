// 定义前端展示类型、地点美术信息与空加载状态；不保存游戏数值规则或执行结算。
export type PlaceId = 'forest' | 'library' | 'plaza' | 'workshop';
export type NpcId = 'joe' | 'wise' | 'calm' | 'stead';
export type Metric = 'energy' | 'mood' | 'social';
export interface Message { role: 'npc' | 'user'; text: string; turn: number }
export interface Npc { id: NpcId; name: string; personality: string; subtitle: string; place: PlaceId; energy: number; mood: number; social: number; action: string; reason: string; memory: string[]; messages: Message[]; rest: boolean }
export interface World { version: 1; turn: number; ecology?: string; npcs: Npc[]; events: { turn: number; npc: NpcId; text: string }[]; tasks: boolean[] }
export const metrics: { key: Metric; label: string }[] = [{ key: 'energy', label: '精力' }, { key: 'mood', label: '情绪' }, { key: 'social', label: '社交意愿' }];
export const places: Record<PlaceId, { name: string; subtitle: string; desc: string; actions: string[]; limits: string[]; x: number; y: number; image: string }> = {
 forest: { name: '林间', subtitle: '放松 · 自然 · 日常', desc: '沿着树影斑驳的小径缓缓走去，风声和鸟鸣会接住未说出口的心事。这里适合独处，也容得下安静的陪伴。', actions: ['林间散步', '静坐休憩', '观察自然'], limits: ['密集社交', '喧闹活动'], x: 20, y: 28, image: 'forest' },
 library: { name: '图书馆', subtitle: '阅读 · 思考 · 沉淀', desc: '旧书页散发着淡淡的木香。有人寻找答案，有人只是想安静地度过一个下午。请放轻脚步，留一点空间给思考。', actions: ['阅读典籍', '伏案记录', '安静休整'], limits: ['大声闲聊', '聚众喧哗'], x: 58, y: 34, image: 'library' },
 plaza: { name: '中心广场', subtitle: '社交 · 活动 · 市井', desc: '这里是小镇的核心区域，商贩、旅人、居民汇聚于此。人们在这里聊天、交易、分享消息，生活的烟火气从不消散。', actions: ['闲聊', '结伴观望', '主动搭话', '人群互动'], limits: ['深度思考', '沉浸式阅读'], x: 41, y: 58, image: 'plaza' },
 workshop: { name: '老旧工坊', subtitle: '劳作 · 专注 · 效率', desc: '木屑落在午后的光里，锤子的轻响为小镇打着节拍。一把修好的椅子、一件趁手的工具，都是认真生活的证明。', actions: ['修缮物件', '整理器具', '专注打磨'], limits: ['频繁打扰', '无意义闲聊'], x: 78, y: 78, image: 'workshop' },
};
// 连接前仅保留空容器；居民初始数值和规则必须由后端提供。
export function emptyWorld(): World {
 return {version: 1, turn: 0, npcs: [], events: [], tasks: []};
}
