/** 按钮清单与提示词预览：对接 option_controller（/options、/prompt/preview） */
import { request } from "@/utils/request";

/** 单个按钮选项 */
export type OptionItem = {
  value: string;
  label: string;
  /** 色调专用：暗到亮锚点 [[R,G,B], ...] */
  anchors: number[][];
};

/** 画布尺寸参数 */
export type CanvasSize = {
  size: number;
  margin_px: number;
  max_colors: number;
  min_coverage: number;
  max_coverage: number;
  preview_scale: number;
};

/** 生成选项（请求体 options） */
export type RunOptions = {
  size: number;
  category: string;
  palette: string;
  outline: string;
  symmetry: string;
  variants: number;
};

/** 按钮清单 */
export type OptionsPayload = {
  sizes: CanvasSize[];
  categories: OptionItem[];
  palettes: OptionItem[];
  outlines: OptionItem[];
  symmetries: OptionItem[];
  variant_counts: number[];
  defaults: RunOptions;
  /** {"category": {"sigil": {"size": 64, "symmetry": "rotational"}}} */
  recommendations: Record<string, Record<string, Partial<Record<keyof RunOptions, string | number>>>>;
  llm_configured: boolean;
};

/** 新建任务 / 预览提示词的请求体 */
export type RunCreateBody = {
  description: string;
  options: RunOptions;
};

/** 提示词预览 */
export type PromptPreview = {
  system: string;
  user: string;
  notes: string[];
};

/** 获取按钮清单 */
export const getOptions = () => request<OptionsPayload>("/options");

/** 预览拼好的提示词（不调模型） */
export const previewPrompt = (body: RunCreateBody) => request<PromptPreview>("/prompt/preview", "POST", body);
