"""render_png：每次解析成功都出图（1:1 + 放大预览），记一次尝试；检查不过时准备回传问题。

即使检查不过也出图：次数用完时带着检查报告交给人决定，过程中每次尝试也都能回看。
"""

from __future__ import annotations

from common.constant.canvas_size import get_canvas_spec
from common.constant.run_event_type import RunEventType
from common.constant.run_status import AttemptTrigger
from server.workflow.deps import WorkflowDeps
from server.workflow.state import VariantState
from server.workflow.stream_emit import emit_attempt, emit_event


def make_render_png(deps: WorkflowDeps):
    async def render_png(state: VariantState) -> dict:
        run_id, variant_id, attempt_no = state["run_id"], state["variant_id"], state["attempt_no"]
        parse, check, reply = state["parse"], state["check"], state["last_reply"]
        spec = get_canvas_spec(int(state["options"]["size"]))

        art_path = deps.artifacts.absolute(parse["art_path"])
        attempt_dir = deps.artifacts.attempt_dir(run_id, variant_id, attempt_no)
        png = deps.library.render_png(art_path, attempt_dir / "preview_x1.png", scale=1)
        preview = deps.library.render_png(art_path, attempt_dir / "preview_scaled.png", scale=spec.preview_scale)

        final_attempt = {
            "attempt_no": attempt_no,
            "passed": check["passed"],
            "name": parse["standard_art"]["name"],
            "art_path": parse["art_path"],
            "png_path": deps.artifacts.relative(png),
            "preview_path": deps.artifacts.relative(preview),
        }
        check_report = {**check, "warnings": parse["warnings"]}
        emit_attempt(
            {
                "run_id": run_id,
                "variant_id": variant_id,
                "attempt_no": attempt_no,
                "trigger": state.get("trigger"),
                "raw_response_path": reply.get("raw_response_path"),
                "compact_path": parse.get("compact_path"),
                "art_path": parse["art_path"],
                "png_path": final_attempt["png_path"],
                "preview_path": final_attempt["preview_path"],
                "check_report": check_report,
                "passed": check["passed"],
                "prompt_tokens": reply.get("prompt_tokens", 0),
                "completion_tokens": reply.get("completion_tokens", 0),
            }
        )
        emit_event(
            RunEventType.ATTEMPT_READY,
            {
                "attempt_no": attempt_no,
                "passed": check["passed"],
                "png_path": final_attempt["png_path"],
                "preview_path": final_attempt["preview_path"],
                "problems": check["problems"],
                "warnings": parse["warnings"],
            },
            variant_id,
        )
        update: dict = {"final_attempt": final_attempt}
        if not check["passed"]:
            update["pending_problems"] = check["problems"]
            update["trigger"] = AttemptTrigger.CHECK_RETRY.value
        return update

    return render_png
