"""OpenAI 兼容（默认 DeepSeek）JSON 对话客户端；写法照搬 stock 的 llm_client，支持多轮对话与用量返回。

Key / 接口地址 / 模型名可在前端「设置」页修改：保存到 data/llm_settings.json（明文，仅本机），
优先于 .env；改完立即生效，不用重启。温度与超时仍只读 .env。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

from common.properties.llm_properties import LlmProperties

log = logging.getLogger(__name__)

# 脱敏显示时保留 Key 末尾的字符数
MASK_VISIBLE_TAIL_CHARS = 4


@dataclass
class LlmReply:
    content: str
    # stop / length / ...；length 表示被 max_tokens 截断
    finish_reason: str | None
    prompt_tokens: int
    # 含思考 token；思考模式下可能远大于可见 content 的长度
    completion_tokens: int
    # completion_tokens 中用于思考的部分；接口不返回时为 0
    reasoning_tokens: int = 0


@dataclass
class LlmSettingsSnapshot:
    """给前端看的当前配置：Key 只给脱敏值。"""

    configured: bool
    api_key_masked: str
    # page：页面保存的 Key；env：.env 里的 Key；none：都没有
    api_key_source: str
    base_url: str
    model: str


class LlmClient:
    """未配置 Key 时也能构造（configured=False），真正调用时才报错，保证功能二不受影响。"""

    def __init__(self, props: LlmProperties, settings_path: Path) -> None:
        self.props = props
        self.settings_path = settings_path
        self.temperature = props.llm_temperature
        # 页面保存的覆盖值；空字符串表示沿用 .env
        self._page_api_key = ""
        self._page_base_url = ""
        self._page_model = ""
        self._load_page_settings()
        self._rebuild()

    # —— 配置 ——

    @property
    def api_key(self) -> str:
        return self._page_api_key or self.props.llm_api_key.strip()

    @property
    def base_url(self) -> str:
        return self._page_base_url or self.props.llm_base_url

    @property
    def model(self) -> str:
        return self._page_model or self.props.llm_model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def snapshot(self) -> LlmSettingsSnapshot:
        source = "page" if self._page_api_key else ("env" if self.props.llm_api_key.strip() else "none")
        return LlmSettingsSnapshot(
            configured=self.configured,
            api_key_masked=_mask(self.api_key),
            api_key_source=source,
            base_url=self.base_url,
            model=self.model,
        )

    def update(self, *, api_key: str | None, clear_api_key: bool, base_url: str, model: str) -> LlmSettingsSnapshot:
        """api_key 为 None / 空表示不改 Key；clear_api_key 清掉页面 Key 回退 .env；地址与模型留空回退 .env。"""
        if clear_api_key:
            self._page_api_key = ""
        elif api_key and api_key.strip():
            self._page_api_key = api_key.strip()
        self._page_base_url = base_url.strip()
        self._page_model = model.strip()
        self._save_page_settings()
        self._rebuild()
        return self.snapshot()

    # —— 调用 ——

    async def chat_json(self, messages: list[dict[str, str]], *, max_tokens: int) -> LlmReply:
        """max_tokens 指可见 json 的上限；思考开启时自动再加 llm_thinking_token_budget。"""
        client = self._client
        if client is None:
            raise RuntimeError("未配置 LLM_API_KEY")
        extra_body: dict = {}
        thinking = self.props.llm_thinking.strip().lower()
        if thinking:
            extra_body["thinking"] = {"type": thinking}
        if self.props.thinking_enabled:
            extra_body["reasoning_effort"] = self.props.llm_reasoning_effort
            max_tokens += self.props.llm_thinking_token_budget
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            extra_body=extra_body or None,
        )
        choice = response.choices[0]
        usage = response.usage
        details = usage.completion_tokens_details if usage else None
        return LlmReply(
            content=(choice.message.content or "").strip(),
            finish_reason=choice.finish_reason,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            reasoning_tokens=(details.reasoning_tokens or 0) if details else 0,
        )

    # —— 内部 ——

    def _rebuild(self) -> None:
        # 进行中的请求仍持有旧客户端，换新实例不影响它们
        self._client = (
            AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.props.llm_timeout_seconds)
            if self.configured
            else None
        )

    def _load_page_settings(self) -> None:
        if not self.settings_path.is_file():
            return
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.warning("页面模型设置文件损坏，已忽略：%s", self.settings_path)
            return
        self._page_api_key = str(data.get("api_key") or "").strip()
        self._page_base_url = str(data.get("base_url") or "").strip()
        self._page_model = str(data.get("model") or "").strip()

    def _save_page_settings(self) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"api_key": self._page_api_key, "base_url": self._page_base_url, "model": self._page_model}
        self.settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _mask(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= MASK_VISIBLE_TAIL_CHARS * 2:
        return "*" * len(api_key)
    return f"{api_key[:3]}****{api_key[-MASK_VISIBLE_TAIL_CHARS:]}"
