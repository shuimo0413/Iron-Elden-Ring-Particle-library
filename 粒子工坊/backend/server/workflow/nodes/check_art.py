"""check_art：对解析成功的像素画做规则检查；硬性不过时发 check_failed。"""

from __future__ import annotations

from common.constant.canvas_size import get_canvas_spec
from common.constant.run_event_type import RunEventType
from server.calc import art_check_calc
from server.workflow.state import VariantState
from server.workflow.stream_emit import emit_event


async def check_art(state: VariantState) -> dict:
    options = state["options"]
    parse = state["parse"]
    report = art_check_calc.check_art(
        parse["standard_art"],
        spec=get_canvas_spec(int(options["size"])),
        symmetry=options.get("symmetry", "none"),
        outline=options.get("outline", "none"),
        unused_palette_keys=parse.get("unused_palette_keys"),
    ).to_dict()
    if not report["passed"]:
        emit_event(
            RunEventType.CHECK_FAILED,
            {"attempt_no": state["attempt_no"], "problems": report["problems"]},
            state["variant_id"],
        )
    return {"check": report}
