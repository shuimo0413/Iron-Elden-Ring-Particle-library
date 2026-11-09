"""节点向外发自定义流事件：run_runner 收到后交给 service 落库。

两种载荷：
- {"kind": "event", "type", "variant_id", "payload"}：写 particle_run_event
- {"kind": "attempt", "record": {...}}：写 particle_attempt
"""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer

EVENT_KIND = "event"
ATTEMPT_KIND = "attempt"


def emit_event(event_type: str, payload: dict[str, Any] | None = None, variant_id: str | None = None) -> None:
    get_stream_writer()({"kind": EVENT_KIND, "type": event_type, "variant_id": variant_id, "payload": payload or {}})


def emit_attempt(record: dict[str, Any]) -> None:
    get_stream_writer()({"kind": ATTEMPT_KIND, "record": record})
