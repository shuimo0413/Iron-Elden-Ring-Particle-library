"""工作流状态：主图 RunState、变体子图 VariantState、审核决定 ReviewDecision。

状态里只放 JSON 可序列化的 dict / list / 基本类型，checkpoint 落 SQLite 不依赖 pickle。
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def merge_by_variant_id(existing: list[dict] | None, updates: list[dict] | None) -> list[dict]:
    """按 variant_id 合并：打回重跑的变体覆盖旧结果，其余保持原顺序。"""
    merged = {item["variant_id"]: item for item in existing or []}
    for item in updates or []:
        merged[item["variant_id"]] = item
    return sorted(merged.values(), key=lambda item: item["variant_id"])


class ReviewDecision(TypedDict, total=False):
    action: str
    variant_id: str | None
    feedback: str | None
    edited_art: dict[str, Any] | None
    publish_name: str | None


class VariantResult(TypedDict, total=False):
    """一个变体跑完一轮后的结果，存进 RunState.variants。"""

    variant_id: str
    style_hint: str
    # done：至少出过一张图；failed：一张都没出
    status: str
    # 完整对话历史，打回时在此基础上继续
    messages: list[dict[str, str]]
    # 该变体已用到的最大尝试编号（打回后继续递增，产物目录不冲突）
    attempt_no: int
    # 最后一次出图的尝试摘要：attempt_no / passed / name / art_path / png_path / preview_path
    final_attempt: dict[str, Any] | None
    error: str | None


class RunState(TypedDict, total=False):
    run_id: int
    description: str
    options: dict[str, Any]
    max_attempts: int
    prompt: dict[str, Any] | None
    variants: Annotated[list[VariantResult], merge_by_variant_id]
    review: ReviewDecision | None
    published_name: str | None
    publish_warnings: list[str]


class VariantState(TypedDict, total=False):
    run_id: int
    variant_id: str
    style_hint: str
    options: dict[str, Any]
    prompt: dict[str, Any]
    messages: list[dict[str, str]]
    # 全局尝试编号（跨打回递增）与本轮已用次数
    attempt_no: int
    round_attempts: int
    max_attempts: int
    # 下一次调用的触发原因
    trigger: str
    # 下一次调用前要追加给模型的问题列表与设计者意见
    pending_problems: list[str]
    human_feedback: str | None
    # 本次调用的回复：content / finish_reason / prompt_tokens / completion_tokens / error / 产物路径
    last_reply: dict[str, Any]
    # 本次解析结果：ok / compact / standard_art / warnings / problems / unused_palette_keys / 产物路径
    parse: dict[str, Any]
    # 本次规则检查报告
    check: dict[str, Any]
    final_attempt: dict[str, Any] | None
    # 子图输出：只有这个键回写主图
    variants: list[VariantResult]


class VariantOutput(TypedDict):
    variants: list[VariantResult]
