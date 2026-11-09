"""取色出参：标准像素 JSON、颜色列表、统计。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PaletteEntryVO(BaseModel):
    rgba: list[int]
    # #RRGGBBAA
    hex: str
    count: int
    # 首次出现的扫描序号（行优先），前端可按它切换为「首次出现顺序」
    first_index: int


class ExtractStatsVO(BaseModel):
    source_mode: str
    animated: bool
    width: int
    height: int
    written_pixels: int
    total_pixels: int
    unique_colors: int
    semi_transparent_pixels: int


class ExtractVO(BaseModel):
    # {name, width, height, pixels:[{x, y, rgba}]}，与 render_pixel_art.py / origin_json 一致
    art: dict[str, Any]
    palette: list[PaletteEntryVO] = Field(default_factory=list)
    stats: ExtractStatsVO
