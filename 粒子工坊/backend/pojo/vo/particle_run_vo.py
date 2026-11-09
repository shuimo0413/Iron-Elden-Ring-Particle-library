"""生成任务出参：任务摘要、尝试、变体、详情、事件。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunVO(BaseModel):
    id: int
    thread_id: str
    description: str
    options: dict[str, Any]
    status: str
    selected_variant_id: str | None = None
    published_name: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


class AttemptVO(BaseModel):
    id: int
    variant_id: str
    attempt_no: int
    trigger: str
    passed: bool
    error_message: str | None = None
    check_report: dict[str, Any] = Field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # 产物地址（带接口前缀，可直接给 <img> / fetch 用）
    raw_response_url: str | None = None
    compact_url: str | None = None
    art_url: str | None = None
    png_url: str | None = None
    preview_url: str | None = None
    created_at: datetime


class VariantVO(BaseModel):
    variant_id: str
    # 最后一次出图的尝试（审核时展示的就是它）
    final_attempt_no: int | None = None
    attempts: list[AttemptVO] = Field(default_factory=list)


class UsageVO(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_calls: int = 0


class RunDetailVO(BaseModel):
    run: RunVO
    prompt_text: str
    prompt_notes: list[str] = Field(default_factory=list)
    variants: list[VariantVO] = Field(default_factory=list)
    usage: UsageVO = Field(default_factory=UsageVO)
    last_seq: int = 0


class RunEventVO(BaseModel):
    seq: int
    type: str
    variant_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
