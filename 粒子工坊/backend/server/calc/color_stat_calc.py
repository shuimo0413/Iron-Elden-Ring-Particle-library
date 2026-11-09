"""取色的颜色统计：每种 RGBA 的出现次数与首次出现位置、半透明像素数。"""

from __future__ import annotations

from dataclasses import dataclass

Rgba = tuple[int, int, int, int]


@dataclass
class ColorCount:
    rgba: Rgba
    hex: str
    count: int
    first_index: int


def rgba_to_hex(rgba: Rgba) -> str:
    """(R,G,B,A) → #RRGGBBAA（大写）。"""
    return "#" + "".join(f"{channel:02X}" for channel in rgba)


def build_palette(grid: list[list[Rgba]], *, min_alpha: int) -> list[ColorCount]:
    """统计 alpha ≥ min_alpha 的颜色；按出现次数从多到少排序，次数相同按首次出现。"""
    counts: dict[Rgba, int] = {}
    first_seen: dict[Rgba, int] = {}
    scan_index = 0
    for row in grid:
        for rgba in row:
            if rgba[3] >= min_alpha:
                if rgba not in counts:
                    counts[rgba] = 0
                    first_seen[rgba] = scan_index
                counts[rgba] += 1
            scan_index += 1
    entries = [ColorCount(rgba, rgba_to_hex(rgba), counts[rgba], first_seen[rgba]) for rgba in counts]
    entries.sort(key=lambda entry: (-entry.count, entry.first_index))
    return entries


def count_semi_transparent(grid: list[list[Rgba]], *, min_alpha: int) -> int:
    """写出的像素中 0 < A < 255 的数量。"""
    return sum(1 for row in grid for rgba in row if rgba[3] >= min_alpha and 0 < rgba[3] < 255)
