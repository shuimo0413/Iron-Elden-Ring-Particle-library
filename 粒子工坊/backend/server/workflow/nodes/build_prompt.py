"""build_prompt：按钮 + 描述 → 首轮提示词，并发出 prompt_built 事件。"""

from __future__ import annotations

from dataclasses import asdict

from common.constant.run_event_type import RunEventType
from server.calc import prompt_calc
from server.workflow.state import RunState
from server.workflow.stream_emit import emit_event


async def build_prompt(state: RunState) -> dict:
    bundle = prompt_calc.build_prompt(state["description"], state["options"])
    prompt = asdict(bundle)
    emit_event(RunEventType.PROMPT_BUILT, prompt)
    return {"prompt": prompt}
