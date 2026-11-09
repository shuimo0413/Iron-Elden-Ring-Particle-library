"""collect_variants：汇合各变体结果；结果已由 variants 的 reducer 合并，这里只做汇合点。"""

from __future__ import annotations

from server.workflow.state import RunState


async def collect_variants(state: RunState) -> dict:
    return {}


def review_summary(state: RunState) -> dict:
    """审核时展示的变体摘要（interrupt 的载荷，也写进 review_waiting 事件）。"""
    return {
        "variants": [
            {
                "variant_id": variant["variant_id"],
                "style_hint": variant.get("style_hint"),
                "status": variant["status"],
                "final_attempt": variant.get("final_attempt"),
                "error": variant.get("error"),
            }
            for variant in state.get("variants") or []
        ]
    }
