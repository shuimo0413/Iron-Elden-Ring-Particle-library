"""生成任务入参：按钮选项、新建任务、审核恢复、历史查询。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from common.constant.canvas_size import DEFAULT_CANVAS_SIZE, SUPPORTED_CANVAS_SIZES
from common.constant.particle_option import (
    AUTO,
    CATEGORY_OPTIONS,
    OUTLINE_OPTIONS,
    PALETTE_OPTIONS,
    SYMMETRY_OPTIONS,
    VARIANT_COUNT_OPTIONS,
    option_values,
)
from common.constant.run_status import ReviewAction


class RunOptionsDTO(BaseModel):
    """按钮选项；取值范围以 common.constant.particle_option 为准。"""

    size: int = DEFAULT_CANVAS_SIZE
    category: str = AUTO
    palette: str = AUTO
    outline: str = "dark"
    symmetry: str = "none"
    variants: int = 2

    @field_validator("size")
    @classmethod
    def _check_size(cls, value: int) -> int:
        if value not in SUPPORTED_CANVAS_SIZES:
            raise ValueError(f"尺寸只能是 {SUPPORTED_CANVAS_SIZES}")
        return value

    @field_validator("category")
    @classmethod
    def _check_category(cls, value: str) -> str:
        return _check_in(value, option_values(CATEGORY_OPTIONS), "类别")

    @field_validator("palette")
    @classmethod
    def _check_palette(cls, value: str) -> str:
        return _check_in(value, option_values(PALETTE_OPTIONS), "色调")

    @field_validator("outline")
    @classmethod
    def _check_outline(cls, value: str) -> str:
        return _check_in(value, option_values(OUTLINE_OPTIONS), "描边")

    @field_validator("symmetry")
    @classmethod
    def _check_symmetry(cls, value: str) -> str:
        return _check_in(value, option_values(SYMMETRY_OPTIONS), "对称")

    @field_validator("variants")
    @classmethod
    def _check_variants(cls, value: int) -> int:
        if value not in VARIANT_COUNT_OPTIONS:
            raise ValueError(f"变体数只能是 {VARIANT_COUNT_OPTIONS}")
        return value


def _check_in(value: str, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ValueError(f"{label}只能是 {sorted(allowed)}")
    return value


class RunCreateDTO(BaseModel):
    description: str = Field(min_length=1, max_length=500, description="一句话描述想要的粒子")
    options: RunOptionsDTO = Field(default_factory=RunOptionsDTO)

    @field_validator("description")
    @classmethod
    def _strip_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("描述不能为空")
        return stripped


class RunResumeDTO(BaseModel):
    """审核：批准（可带手改像素与入库名）/ 打回附意见 / 放弃。"""

    action: Literal["approve", "revise", "reject"]
    variant_id: str | None = None
    feedback: str | None = Field(default=None, max_length=500)
    # 手改后的标准像素 JSON {name, width, height, pixels}；为空则用变体最终出图
    edited_art: dict[str, Any] | None = None
    # 入库文件名；为空则用模型给的 name（规范化后）
    publish_name: str | None = Field(default=None, max_length=64)

    @property
    def review_action(self) -> ReviewAction:
        return ReviewAction(self.action)


class RunQueryDTO(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: str | None = None
