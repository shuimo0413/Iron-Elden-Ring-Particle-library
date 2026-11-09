"""图装配：主图（build_prompt → 变体并行 → 汇合 → 人工审核 → 入库）与变体子图（调模型 ↔ 解析 / 检查 / 出图）。

主图
  build_prompt ─Send×N→ variant_loop ─→ collect_variants ─→ human_review
  human_review ─批准→ publish → END
               ─打回→ Send(variant_loop, 选中变体) → collect_variants → human_review
               ─放弃→ END
  collect_variants 在所有变体都失败时直接 END。

变体子图 variant_loop
  call_model → parse_art ─成功→ check_art → render_png ─通过 / 次数用完→ finish_variant
                         ─失败且有次数→ call_model           ─不过且有次数→ call_model
                         ─失败且次数用完→ finish_variant
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from common.constant.particle_option import STYLE_HINTS
from common.constant.run_status import AttemptTrigger, ReviewAction
from server.workflow.deps import WorkflowDeps
from server.workflow.nodes.build_prompt import build_prompt
from server.workflow.nodes.call_model import make_call_model
from server.workflow.nodes.check_art import check_art
from server.workflow.nodes.collect_variants import collect_variants
from server.workflow.nodes.finish_variant import VARIANT_DONE, finish_variant
from server.workflow.nodes.human_review import human_review
from server.workflow.nodes.parse_art import make_parse_art
from server.workflow.nodes.publish import make_publish
from server.workflow.nodes.render_png import make_render_png
from server.workflow.state import RunState, VariantOutput, VariantState

VARIANT_LOOP = "variant_loop"


def build_variant_graph(deps: WorkflowDeps):
    graph = StateGraph(VariantState, output_schema=VariantOutput)
    graph.add_node("call_model", make_call_model(deps))
    graph.add_node("parse_art", make_parse_art(deps))
    graph.add_node("check_art", check_art)
    graph.add_node("render_png", make_render_png(deps))
    graph.add_node("finish_variant", finish_variant)

    graph.add_edge(START, "call_model")
    graph.add_edge("call_model", "parse_art")
    graph.add_conditional_edges("parse_art", _after_parse, ["check_art", "call_model", "finish_variant"])
    graph.add_edge("check_art", "render_png")
    graph.add_conditional_edges("render_png", _after_render, ["call_model", "finish_variant"])
    graph.add_edge("finish_variant", END)
    return graph.compile()


def build_graph(deps: WorkflowDeps, checkpointer=None):
    """主图；checkpointer 为 None 时只在内存里跑（测试 / 命令行用）。"""
    graph = StateGraph(RunState)
    graph.add_node("build_prompt", build_prompt)
    graph.add_node(VARIANT_LOOP, build_variant_graph(deps))
    graph.add_node("collect_variants", collect_variants)
    graph.add_node("human_review", human_review)
    graph.add_node("publish", make_publish(deps))

    graph.add_edge(START, "build_prompt")
    graph.add_conditional_edges("build_prompt", _fan_out_variants, [VARIANT_LOOP])
    graph.add_edge(VARIANT_LOOP, "collect_variants")
    graph.add_conditional_edges("collect_variants", _after_collect, ["human_review", END])
    graph.add_conditional_edges("human_review", _after_review, [VARIANT_LOOP, "publish", END])
    graph.add_edge("publish", END)
    return graph.compile(checkpointer=checkpointer)


def _has_rounds_left(state: VariantState) -> bool:
    return state.get("round_attempts", 0) < state["max_attempts"]


def _after_parse(state: VariantState) -> str:
    if state["parse"]["ok"]:
        return "check_art"
    return "call_model" if _has_rounds_left(state) else "finish_variant"


def _after_render(state: VariantState) -> str:
    if state["check"]["passed"] or not _has_rounds_left(state):
        return "finish_variant"
    return "call_model"


def _variant_input(state: RunState, variant_id: str, style_hint: str) -> VariantState:
    return {
        "run_id": state["run_id"],
        "variant_id": variant_id,
        "style_hint": style_hint,
        "options": state["options"],
        "prompt": state["prompt"],
        "messages": [],
        "attempt_no": 0,
        "round_attempts": 0,
        "max_attempts": state["max_attempts"],
        "trigger": AttemptTrigger.INITIAL.value,
        "pending_problems": [],
        "human_feedback": None,
        "final_attempt": None,
    }


def _fan_out_variants(state: RunState) -> list[Send]:
    count = int(state["options"]["variants"])
    # 只有一个变体时不加风格倾向，完全按描述画
    hints = [""] if count == 1 else [STYLE_HINTS[index % len(STYLE_HINTS)] for index in range(count)]
    return [Send(VARIANT_LOOP, _variant_input(state, f"v{index + 1}", hint)) for index, hint in enumerate(hints)]


def _after_collect(state: RunState) -> str:
    if any(variant["status"] == VARIANT_DONE for variant in state.get("variants") or []):
        return "human_review"
    return END


def _after_review(state: RunState):
    review = state.get("review") or {}
    action = review.get("action")
    if action == ReviewAction.APPROVE:
        return "publish"
    if action == ReviewAction.REVISE:
        variant = next(item for item in state["variants"] if item["variant_id"] == review["variant_id"])
        revise_input: VariantState = {
            **_variant_input(state, variant["variant_id"], variant.get("style_hint", "")),
            "messages": variant.get("messages") or [],
            "attempt_no": variant.get("attempt_no", 0),
            "trigger": AttemptTrigger.HUMAN_REVISE.value,
            "human_feedback": review.get("feedback"),
            "final_attempt": variant.get("final_attempt"),
        }
        return [Send(VARIANT_LOOP, revise_input)]
    return END
