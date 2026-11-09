"""像素画规则检查：透明边、覆盖率、颜色数、对称（硬性），孤立像素、未用调色板键、描边（提示）。

硬性规则不过时生成可回传给模型的问题列表；提示类只写进报告。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from common.constant.canvas_size import CanvasSizeSpec

HARD = "hard"
HINT = "hint"
# 透明边越界坐标最多列出几个
MAX_LISTED_COORDINATES = 10
# 对称重合率下限（0–1）；调低更宽松，调高模型更难过
SYMMETRY_MIN_OVERLAP = 0.90
# 描边比例低于此值时在报告里提示「描边不明显」
OUTLINE_MIN_DARK_RATIO = 0.5
# 孤立像素占不透明像素比例超过此值时提示「噪点偏多」
ISOLATED_PIXEL_WARN_RATIO = 0.08

_NEIGHBORS_8 = tuple((dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0))
_NEIGHBORS_4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class CheckItem:
    rule: str
    level: str
    passed: bool
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtCheckReport:
    passed: bool
    items: list[CheckItem]
    problems: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "items": [asdict(item) for item in self.items], "problems": self.problems}


def check_art(
    standard_art: dict[str, Any],
    *,
    spec: CanvasSizeSpec,
    symmetry: str = "none",
    outline: str = "none",
    unused_palette_keys: list[str] | None = None,
) -> ArtCheckReport:
    width, height = standard_art["width"], standard_art["height"]
    grid: dict[tuple[int, int], tuple[int, ...]] = {
        (pixel["x"], pixel["y"]): tuple(pixel["rgba"]) for pixel in standard_art["pixels"] if pixel["rgba"][3] > 0
    }
    items = [
        _check_margin(grid, width, height, spec.margin_px),
        _check_coverage(grid, width, height, spec),
        _check_color_count(grid, spec.max_colors),
    ]
    if symmetry in ("mirror_x", "rotational"):
        items.append(_check_symmetry(grid, width, height, symmetry))
    if spec.isolated_pixel_check:
        items.append(_check_isolated(grid))
    if unused_palette_keys:
        items.append(
            CheckItem(
                "unused_palette",
                HINT,
                False,
                f"调色板有 {len(unused_palette_keys)} 个键未使用：{''.join(unused_palette_keys)}",
                {"keys": unused_palette_keys},
            )
        )
    if outline == "dark":
        items.append(_check_outline(grid))

    problems = [item.message for item in items if item.level == HARD and not item.passed]
    return ArtCheckReport(passed=not problems, items=items, problems=problems)


def _check_margin(grid, width: int, height: int, margin: int) -> CheckItem:
    if margin <= 0:
        return CheckItem("margin", HARD, True, "无透明边要求")
    offenders = sorted(
        (x, y) for (x, y) in grid if x < margin or y < margin or x >= width - margin or y >= height - margin
    )
    if not offenders:
        return CheckItem("margin", HARD, True, f"四周 {margin}px 透明边内无像素")
    listed = " ".join(f"({x},{y})" for x, y in offenders[:MAX_LISTED_COORDINATES])
    more = " 等" if len(offenders) > MAX_LISTED_COORDINATES else ""
    return CheckItem(
        "margin",
        HARD,
        False,
        f"四周 {margin}px 透明边内有 {len(offenders)} 个像素：{listed}{more}",
        {"count": len(offenders), "coordinates": [list(c) for c in offenders[:MAX_LISTED_COORDINATES]]},
    )


def _check_coverage(grid, width: int, height: int, spec: CanvasSizeSpec) -> CheckItem:
    coverage = len(grid) / (width * height)
    detail = {"coverage": round(coverage, 4), "min": spec.min_coverage, "max": spec.max_coverage}
    percent = f"{coverage:.1%}"
    if coverage < spec.min_coverage:
        return CheckItem(
            "coverage", HARD, False, f"不透明像素只占 {percent}，低于下限 {spec.min_coverage:.0%}，画面太空", detail
        )
    if coverage > spec.max_coverage:
        return CheckItem(
            "coverage", HARD, False, f"不透明像素占 {percent}，超过上限 {spec.max_coverage:.0%}，几乎铺满画布", detail
        )
    return CheckItem("coverage", HARD, True, f"覆盖率 {percent}", detail)


def _check_color_count(grid, max_colors: int) -> CheckItem:
    used = len(set(grid.values()))
    if used > max_colors:
        return CheckItem(
            "colors", HARD, False, f"实际用到 {used} 种颜色，超过上限 {max_colors}", {"used": used, "max": max_colors}
        )
    return CheckItem("colors", HARD, True, f"用到 {used} 种颜色", {"used": used, "max": max_colors})


def _check_symmetry(grid, width: int, height: int, symmetry: str) -> CheckItem:
    positions = set(grid)
    if not positions:
        return CheckItem("symmetry", HARD, False, "画面为空，无法判断对称")
    if symmetry == "mirror_x":
        transformed = {(width - 1 - x, y) for x, y in positions}
        label = "左右镜像"
    else:
        transformed = {(width - 1 - y, x) for x, y in positions}
        label = "90° 旋转"
    overlap = len(positions & transformed) / len(positions)
    detail = {"overlap": round(overlap, 4), "min": SYMMETRY_MIN_OVERLAP}
    if overlap < SYMMETRY_MIN_OVERLAP:
        return CheckItem(
            "symmetry",
            HARD,
            False,
            f"{label}后像素重合率 {overlap:.0%}，低于 {SYMMETRY_MIN_OVERLAP:.0%}，请让形状更对称",
            detail,
        )
    return CheckItem("symmetry", HARD, True, f"{label}重合率 {overlap:.0%}", detail)


def _check_isolated(grid) -> CheckItem:
    isolated = 0
    for (x, y), color in grid.items():
        if not any(grid.get((x + dx, y + dy)) == color for dx, dy in _NEIGHBORS_8):
            isolated += 1
    ratio = isolated / len(grid) if grid else 0.0
    noisy = ratio > ISOLATED_PIXEL_WARN_RATIO
    message = f"孤立像素 {isolated} 个（占 {ratio:.0%}）" + ("，噪点偏多" if noisy else "")
    return CheckItem("isolated", HINT, not noisy, message, {"count": isolated, "ratio": round(ratio, 4)})


def _check_outline(grid) -> CheckItem:
    """剪影边界像素中，明度低于内部平均明度的比例。"""
    boundary: list[float] = []
    interior: list[float] = []
    for (x, y), color in grid.items():
        # 越界的邻居也不在 grid 里，所以「邻居不在 grid」已覆盖画布边缘
        is_edge = any((x + dx, y + dy) not in grid for dx, dy in _NEIGHBORS_4)
        (boundary if is_edge else interior).append(_luminance(color))
    if not boundary or not interior:
        return CheckItem("outline", HINT, True, "形状太细，跳过描边检查")
    interior_mean = sum(interior) / len(interior)
    ratio = sum(1 for value in boundary if value < interior_mean) / len(boundary)
    passed = ratio >= OUTLINE_MIN_DARK_RATIO
    message = f"边界像素中 {ratio:.0%} 比内部平均更暗" + ("" if passed else "，暗色描边不明显")
    return CheckItem("outline", HINT, passed, message, {"dark_ratio": round(ratio, 4)})


def _luminance(color: tuple[int, ...]) -> float:
    red, green, blue = color[0], color[1], color[2]
    return 0.299 * red + 0.587 * green + 0.114 * blue
