"""human_review：interrupt 等待 /resume 传入审核决定。

注意：恢复时 LangGraph 会从头重跑本节点，所以 interrupt 之前不能有副作用（不发事件）。
review_waiting 事件由 run_runner 在检测到中断后发出。
"""

from __future__ import annotations

from langgraph.types import interrupt

from server.workflow.nodes.collect_variants import review_summary
from server.workflow.state import RunState


async def human_review(state: RunState) -> dict:
    decision = interrupt(review_summary(state))
    return {"review": decision}
