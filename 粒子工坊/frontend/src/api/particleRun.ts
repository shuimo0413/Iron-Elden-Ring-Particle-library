/** 生成任务：对接 particle_run_controller（/particle-runs） */
import type { RunCreateBody, RunOptions } from "@/api/option";
import type { PixelArt } from "@/lib/pixelArt";
import { request } from "@/utils/request";

/** 任务状态 */
export type RunStatus = "running" | "reviewing" | "published" | "rejected" | "failed" | "cancelled" | "interrupted";

/** 任务摘要 */
export type Run = {
  id: number;
  thread_id: string;
  description: string;
  options: RunOptions;
  status: RunStatus;
  selected_variant_id: string | null;
  published_name: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
};

/** 规则检查条目 */
export type CheckItem = {
  rule: string;
  /** hard 硬性 / hint 提示 */
  level: "hard" | "hint";
  passed: boolean;
  message: string;
  detail: Record<string, unknown>;
};

/** 检查报告：解析警告 + 规则检查 + 回传给模型的问题 */
export type CheckReport = {
  passed?: boolean;
  items?: CheckItem[];
  problems?: string[];
  warnings?: string[];
};

/** 一次模型调用 */
export type Attempt = {
  id: number;
  variant_id: string;
  attempt_no: number;
  trigger: string;
  passed: boolean;
  error_message: string | null;
  check_report: CheckReport;
  prompt_tokens: number;
  completion_tokens: number;
  raw_response_url: string | null;
  compact_url: string | null;
  art_url: string | null;
  png_url: string | null;
  preview_url: string | null;
  created_at: string;
};

/** 变体：全部尝试 + 最后一次出图的尝试编号 */
export type Variant = {
  variant_id: string;
  final_attempt_no: number | null;
  attempts: Attempt[];
};

/** 用量 */
export type Usage = {
  prompt_tokens: number;
  completion_tokens: number;
  model_calls: number;
};

/** 任务详情 */
export type RunDetail = {
  run: Run;
  prompt_text: string;
  prompt_notes: string[];
  variants: Variant[];
  usage: Usage;
  last_seq: number;
};

/** 轮询事件 */
export type RunEvent = {
  seq: number;
  type: string;
  variant_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

/** 分页结果 */
export type PageResult<T> = {
  total: number;
  page: number;
  page_size: number;
  items: T[];
};

/** 审核请求体 */
export type ResumeBody =
  | { action: "approve"; variant_id: string; edited_art?: PixelArt | null; publish_name?: string | null }
  | { action: "revise"; variant_id: string; feedback: string }
  | { action: "reject" };

/** 新建任务 */
export const createRun = (body: RunCreateBody) => request<Run>("/particle-runs", "POST", body);

/** 分页历史 */
export const listRuns = (params: { page: number; page_size: number; status?: string }) =>
  request<PageResult<Run>>("/particle-runs", "GET", params);

/** 任务详情 */
export const getRunDetail = (id: number) => request<RunDetail>(`/particle-runs/${id}`);

/** 轮询增量事件 */
export const listRunEvents = (id: number, afterSeq: number) =>
  request<RunEvent[]>(`/particle-runs/${id}/events`, "GET", { after_seq: afterSeq });

/** 审核：批准 / 打回 / 放弃 */
export const resumeRun = (id: number, body: ResumeBody) => request<Run>(`/particle-runs/${id}/resume`, "POST", body);

/** 取消运行中的任务 */
export const cancelRun = (id: number) => request<Run>(`/particle-runs/${id}/cancel`, "POST");

/** 读任务产物里的 JSON 文件（art.json 等静态文件，不走 Result 返回体） */
export async function fetchArtifactJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`读取产物失败（HTTP ${response.status}）`);
  return (await response.json()) as T;
}
