/** 图片逐像素取色：对接 extract_controller（/extract） */
import type { PixelArt, Rgba } from "@/lib/pixelArt";
import { upload } from "@/utils/request";

/** 颜色列表条目 */
export type PaletteEntry = {
  rgba: Rgba;
  /** #RRGGBBAA */
  hex: string;
  count: number;
  /** 首次出现的扫描序号（行优先） */
  first_index: number;
};

/** 统计 */
export type ExtractStats = {
  source_mode: string;
  animated: boolean;
  width: number;
  height: number;
  written_pixels: number;
  total_pixels: number;
  unique_colors: number;
  semi_transparent_pixels: number;
};

/** 取色结果 */
export type ExtractResult = {
  art: PixelArt;
  palette: PaletteEntry[];
  stats: ExtractStats;
};

/** 上传图片取色；name 为空时用文件名，minAlpha 以下的像素不写入 pixels */
export function extractImage(file: File, name: string, minAlpha: number): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file);
  if (name.trim()) form.append("name", name.trim());
  form.append("min_alpha", String(minAlpha));
  return upload<ExtractResult>("/extract", form);
}
