/** 粒子库浏览：对接 library_controller（/library） */
import type { PixelArt } from "@/lib/pixelArt";
import { request } from "@/utils/request";

/** 粒子列表条目 */
export type ParticleItem = {
  name: string;
  /** 文件名第一个下划线前的前缀 */
  series: string;
  width: number;
  height: number;
  png_url: string;
  has_json: boolean;
  modified_at: number;
};

/** 单个粒子详情 */
export type ParticleDetail = ParticleItem & { art: PixelArt };

/** 总览图重建结果 */
export type Showcase = { url: string; particle_count: number };

/** 粒子列表 */
export const listParticles = (params: { q?: string; series?: string }) =>
  request<ParticleItem[]>("/library", "GET", params);

/** 单个粒子 */
export const getParticle = (name: string) => request<ParticleDetail>(`/library/${encodeURIComponent(name)}`);

/** 手动重建总览图 */
export const rebuildShowcase = () => request<Showcase>("/library/showcase", "POST");

/** 总览图地址（带时间戳防缓存） */
export const showcaseUrl = () => `/api/v1/files/showcase.png?t=${Date.now()}`;
