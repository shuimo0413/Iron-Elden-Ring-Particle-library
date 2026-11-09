"""finish_variant：一轮结束，把变体结果写回主图 variants，并发 variant_done / variant_failed。"""

from __future__ import annotations

from common.constant.run_event_type import RunEventType
from server.workflow.state import VariantResult, VariantState
from server.workflow.stream_emit import emit_event

VARIANT_DONE = "done"
VARIANT_FAILED = "failed"


async def finish_variant(state: VariantState) -> dict:
    final_attempt = state.get("final_attempt")
    variant_id = state["variant_id"]
    error = None
    if final_attempt:
        emit_event(
            RunEventType.VARIANT_DONE,
            {"final_attempt_no": final_attempt["attempt_no"], "passed": final_attempt["passed"]},
            variant_id,
        )
    else:
        problems = (state.get("parse") or {}).get("problems") or []
        error = "；".join(problems) or "模型调用次数用完仍未解析出图"
        emit_event(RunEventType.VARIANT_FAILED, {"error": error}, variant_id)
    result: VariantResult = {
        "variant_id": variant_id,
        "style_hint": state.get("style_hint", ""),
        "status": VARIANT_DONE if final_attempt else VARIANT_FAILED,
        "messages": state.get("messages") or [],
        "attempt_no": state.get("attempt_no", 0),
        "final_attempt": final_attempt,
        "error": error,
    }
    return {"variants": [result]}
