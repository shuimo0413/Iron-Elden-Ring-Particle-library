/** 展示格式化：时间、任务状态、事件类型、文件下载 */

/** 后端时间是本机本地时间（无时区），直接按本地显示 */
export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString("zh-CN", { hour12: false });
}

/** 任务状态 → 中文与 Tag 颜色 */
export const RUN_STATUS_META: Record<string, { label: string; color: string }> = {
  running: { label: "运行中", color: "processing" },
  reviewing: { label: "待审核", color: "warning" },
  published: { label: "已入库", color: "success" },
  rejected: { label: "已放弃", color: "default" },
  failed: { label: "失败", color: "error" },
  cancelled: { label: "已取消", color: "default" },
  interrupted: { label: "已中断", color: "default" },
};

/** 事件类型 → 时间线文案 */
export const EVENT_LABEL: Record<string, string> = {
  prompt_built: "提示词已拼好",
  model_called: "模型调用完成",
  parse_failed: "解析失败",
  check_failed: "规则检查不过",
  attempt_ready: "出图",
  variant_done: "变体完成",
  variant_failed: "变体失败",
  review_waiting: "等待审核",
  review_submitted: "提交审核",
  published: "已入库",
  run_rejected: "已放弃",
  run_failed: "任务失败",
  run_cancelled: "任务取消",
  run_interrupted: "任务中断",
};

/** 尝试触发原因 → 中文 */
export const TRIGGER_LABEL: Record<string, string> = {
  initial: "首轮",
  parse_retry: "解析重试",
  check_retry: "检查重试",
  human_revise: "打回重画",
};

/** 把文本存成文件下载 */
export function downloadText(filename: string, text: string, mime = "application/json"): void {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
