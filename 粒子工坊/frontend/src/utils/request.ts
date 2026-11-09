/** 请求封装：唯一的 HTTP 入口，只认后端返回体 code（0 成功 / 非 0 失败）；无登录、无 token */

const BASE_URL = "/api/v1";

type ApiBody<T> = { code: number; message: string; data: T };

/** 业务失败：后端返回 code !== 0，或网络 / 解析异常。data 为后端随失败一并返回的数据（可能为空）。 */
export class BizError<T = unknown> extends Error {
  data: T | null;

  constructor(message: string, data: T | null = null) {
    super(message);
    this.name = "BizError";
    this.data = data;
  }
}

type Method = "GET" | "POST" | "PUT" | "DELETE";

/**
 * 唯一的 JSON 请求入口：只认返回体 code，不判断 HTTP 状态码。
 * GET 的 data 作为 query，其它方法作为 JSON body。
 */
export async function request<T>(url: string, method: Method = "GET", data?: unknown): Promise<T> {
  let fullUrl = `${BASE_URL}${url}`;
  const headers: Record<string, string> = {};
  let body: string | undefined;
  if (method === "GET") {
    const query = toQuery(data);
    if (query) fullUrl += `${fullUrl.includes("?") ? "&" : "?"}${query}`;
  } else if (data !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(data);
  }
  return send<T>(fullUrl, { method, headers, body });
}

/** multipart 上传（取色），返回体处理与 request 一致；不设 Content-Type，交给浏览器带 boundary */
export async function upload<T>(url: string, form: FormData): Promise<T> {
  return send<T>(`${BASE_URL}${url}`, { method: "POST", body: form });
}

async function send<T>(fullUrl: string, init: RequestInit): Promise<T> {
  let res: ApiBody<T>;
  try {
    const r = await fetch(fullUrl, init);
    res = (await r.json()) as ApiBody<T>;
  } catch {
    throw new BizError<T>("网络异常，请确认后端已启动");
  }
  if (!res || typeof res.code !== "number") throw new BizError<T>("响应格式异常");
  if (res.code !== 0) throw new BizError<T>(res.message || "操作失败", res.data ?? null);
  return res.data;
}

function toQuery(data: unknown): string {
  if (!data || typeof data !== "object") return "";
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
    if (v === undefined || v === null || v === "") continue;
    q.set(k, String(v));
  }
  return q.toString();
}

/** 取异常的提示文案，没有时用 fallback */
export function errorMessage(e: unknown, fallback = "操作失败"): string {
  return e instanceof Error && e.message ? e.message : fallback;
}
