"""call_model：拼好本轮对话 → 调模型（JSON 模式）→ 留档 prompt.txt / response.json。

模型调用异常不抛出：记进 last_reply.error，由 parse_art 判为失败并计入次数。
"""

from __future__ import annotations

import logging

from common.constant.canvas_size import get_canvas_spec
from common.constant.run_event_type import RunEventType
from server.calc import prompt_calc
from server.workflow.deps import WorkflowDeps
from server.workflow.state import VariantState
from server.workflow.stream_emit import emit_event

log = logging.getLogger(__name__)


def make_call_model(deps: WorkflowDeps):
    async def call_model(state: VariantState) -> dict:
        messages = _next_messages(state)
        attempt_no = state.get("attempt_no", 0) + 1
        run_id, variant_id = state["run_id"], state["variant_id"]
        spec = get_canvas_spec(int(state["options"]["size"]))

        deps.artifacts.write_text(
            run_id, variant_id, attempt_no, "prompt.txt", prompt_calc.render_messages_text(messages)
        )
        reply: dict = {
            "content": "",
            "finish_reason": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "error": None,
        }
        try:
            result = await deps.llm.chat_json(messages, max_tokens=spec.max_tokens)
            reply.update(
                content=result.content,
                finish_reason=result.finish_reason,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                reasoning_tokens=result.reasoning_tokens,
            )
        except Exception as exc:  # noqa: BLE001  任何调用失败都计为一次失败尝试
            log.warning("模型调用失败 run=%s variant=%s attempt=%s: %s", run_id, variant_id, attempt_no, exc)
            reply["error"] = f"{type(exc).__name__}: {exc}"
        response_path = deps.artifacts.write_json(run_id, variant_id, attempt_no, "response.json", dict(reply))
        reply["raw_response_path"] = response_path

        emit_event(
            RunEventType.MODEL_CALLED,
            {
                "attempt_no": attempt_no,
                "trigger": state.get("trigger"),
                "prompt_tokens": reply["prompt_tokens"],
                "completion_tokens": reply["completion_tokens"],
                "finish_reason": reply["finish_reason"],
                "error": reply["error"],
            },
            variant_id,
        )
        if reply["content"]:
            messages = [*messages, {"role": "assistant", "content": reply["content"]}]
        return {
            "messages": messages,
            "attempt_no": attempt_no,
            "round_attempts": state.get("round_attempts", 0) + 1,
            "last_reply": reply,
            "pending_problems": [],
            "human_feedback": None,
        }

    return call_model


def _next_messages(state: VariantState) -> list[dict[str, str]]:
    """首轮：system + user（带风格倾向）；之后：在历史末尾追加问题 / 设计者意见。"""
    messages = list(state.get("messages") or [])
    if not messages:
        prompt = state["prompt"]
        user = prompt_calc.apply_style_hint(prompt["user"], state.get("style_hint"))
        return [{"role": "system", "content": prompt["system"]}, {"role": "user", "content": user}]
    problems = state.get("pending_problems") or []
    feedback = state.get("human_feedback")
    if problems or feedback:
        messages.append({"role": "user", "content": prompt_calc.build_retry_message(problems, feedback)})
    return messages
