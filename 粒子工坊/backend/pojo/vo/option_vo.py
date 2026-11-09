"""按钮清单出参：各按钮组选项、尺寸参数、色调锚点、推荐联动、默认值。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OptionItemVO(BaseModel):
    value: str
    label: str
    # 色调专用：暗到亮锚点 [[R,G,B], ...]
    anchors: list[list[int]] = Field(default_factory=list)


class CanvasSizeVO(BaseModel):
    size: int
    margin_px: int
    max_colors: int
    min_coverage: float
    max_coverage: float
    preview_scale: int


class OptionsVO(BaseModel):
    sizes: list[CanvasSizeVO]
    categories: list[OptionItemVO]
    palettes: list[OptionItemVO]
    outlines: list[OptionItemVO]
    symmetries: list[OptionItemVO]
    variant_counts: list[int]
    defaults: dict[str, Any]
    # {"category": {"sigil": {"size": 64, "symmetry": "rotational"}}}
    recommendations: dict[str, dict[str, dict[str, Any]]]
    llm_configured: bool
