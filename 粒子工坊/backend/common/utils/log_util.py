"""日志辅助：把 DTO / dict 打成可读结构，脱敏密钥字段，并截断过长内容（如手改像素数组）。"""

from __future__ import annotations

from typing import Any

_SENSITIVE_KEYS = frozenset({"api_key", "llm_api_key", "token", "authorization", "secret"})
# 列表超过这个长度只打印条数，避免像素数组刷屏
_MAX_LIST_ITEMS = 20


def to_log(obj: Any) -> Any:
    """供 log.info('…%s', to_log(dto)) 使用，风格对齐 Spring 打印入参。"""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        try:
            data = obj.model_dump()
        except Exception:
            return repr(obj)
        return _redact(data)
    if isinstance(obj, dict):
        return _redact(obj)
    if isinstance(obj, (list, tuple)):
        if len(obj) > _MAX_LIST_ITEMS:
            return f"<{len(obj)} items>"
        return [to_log(x) for x in obj]
    return obj


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if str(key).lower() in _SENSITIVE_KEYS:
            out[key] = "***"
        else:
            out[key] = to_log(value)
    return out
