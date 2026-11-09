/** 模型设置：对接 llm_settings_controller（/settings/llm） */
import { request } from "@/utils/request";

/** 当前生效的模型设置（Key 脱敏） */
export type LlmSettings = {
  configured: boolean;
  /** 如 sk-****abcd；未配置时为空 */
  api_key_masked: string;
  /** page：页面保存的 Key；env：.env 里的 Key；none：都没有 */
  api_key_source: "page" | "env" | "none";
  base_url: string;
  model: string;
};

/** 保存请求体：api_key 不传或为空表示不改 Key */
export type LlmSettingsBody = {
  api_key?: string | null;
  clear_api_key?: boolean;
  base_url: string;
  model: string;
};

/** 读取模型设置 */
export const getLlmSettings = () => request<LlmSettings>("/settings/llm");

/** 保存模型设置，立即生效 */
export const saveLlmSettings = (body: LlmSettingsBody) => request<LlmSettings>("/settings/llm", "PUT", body);
