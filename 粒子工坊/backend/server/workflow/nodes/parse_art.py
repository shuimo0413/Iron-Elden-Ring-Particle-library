"""parse_art：校验 / 有限修复紧凑 JSON 并转标准像素 JSON；失败时记一次尝试并准备回传问题。"""

from __future__ import annotations

from common.constant.canvas_size import get_canvas_spec
from common.constant.run_event_type import RunEventType
from common.constant.run_status import AttemptTrigger
from server.calc import compact_art_calc
from server.workflow.deps import WorkflowDeps
from server.workflow.state import VariantState
from server.workflow.stream_emit import emit_attempt, emit_event


def make_parse_art(deps: WorkflowDeps):
    async def parse_art(state: VariantState) -> dict:
        reply = state["last_reply"]
        run_id, variant_id, attempt_no = state["run_id"], state["variant_id"], state["attempt_no"]
        size = int(state["options"]["size"])

        if reply.get("error"):
            parse = {"ok": False, "problems": [f"模型调用失败：{reply['error']}"], "warnings": []}
            # 调用本身失败时模型没有输出，重试不追加问题消息
            retry_problems: list[str] = []
        else:
            result = compact_art_calc.parse_compact_art(
                reply["content"],
                size=size,
                max_colors=get_canvas_spec(size).max_colors,
                finish_reason=reply.get("finish_reason"),
                reasoning_tokens=reply.get("reasoning_tokens", 0),
                existing_names=frozenset(deps.library.list_names()),
                fallback_name=f"particle_{run_id}_{variant_id}",
            )
            parse = {
                "ok": result.ok,
                "compact": result.compact,
                "standard_art": result.standard_art,
                "warnings": result.warnings,
                "problems": result.problems,
                "unused_palette_keys": result.unused_palette_keys,
            }
            retry_problems = result.problems
            if result.ok:
                parse["compact_path"] = deps.artifacts.write_json(
                    run_id, variant_id, attempt_no, "compact.json", result.compact
                )
                parse["art_path"] = deps.artifacts.write_json(
                    run_id, variant_id, attempt_no, "art.json", result.standard_art
                )

        if parse["ok"]:
            return {"parse": parse}

        emit_event(RunEventType.PARSE_FAILED, {"attempt_no": attempt_no, "problems": parse["problems"]}, variant_id)
        emit_attempt(
            {
                "run_id": run_id,
                "variant_id": variant_id,
                "attempt_no": attempt_no,
                "trigger": state.get("trigger"),
                "raw_response_path": reply.get("raw_response_path"),
                "check_report": {"warnings": parse["warnings"], "problems": parse["problems"], "items": []},
                "passed": False,
                "error_message": "；".join(parse["problems"]),
                "prompt_tokens": reply.get("prompt_tokens", 0),
                "completion_tokens": reply.get("completion_tokens", 0),
            }
        )
        return {"parse": parse, "pending_problems": retry_problems, "trigger": AttemptTrigger.PARSE_RETRY.value}

    return parse_art
