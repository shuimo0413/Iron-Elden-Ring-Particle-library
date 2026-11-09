"""画布尺寸参数表：每种尺寸的透明边、颜色上限、覆盖率、预览放大倍数、max_tokens、画法指南。

调参说明：
- margin_px：四周透明边宽度（像素），防止粒子图集相邻贴图渗色；调大则可画区域变小。
- max_colors：调色板颜色上限；调大则模型更容易画出脏渐变，调小则画面更扁平。
- min_coverage / max_coverage：不透明像素占比（0–1）；下限防止画面几乎空白，上限防止铺满整个方块。
- preview_scale：放大预览倍数，统一放大到 512px 方便对比。
- max_tokens：单次模型调用中可见 json 的输出上限；紧凑格式下 32×32 约 1–2K token，64×64 约 3–5K token。
  思考模式的 token 另由 LLM_THINKING_TOKEN_BUDGET 追加，不要往这里加。
- isolated_pixel_check：是否统计孤立像素（8×8 每个像素都是特征，关闭）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanvasSizeSpec:
    size: int
    margin_px: int
    max_colors: int
    min_coverage: float
    max_coverage: float
    preview_scale: int
    max_tokens: int
    isolated_pixel_check: bool
    guide: str


CANVAS_SIZES: dict[int, CanvasSizeSpec] = {
    64: CanvasSizeSpec(
        size=64,
        margin_px=2,
        max_colors=24,
        min_coverage=0.03,
        max_coverage=0.75,
        preview_scale=8,
        max_tokens=8000,
        isolated_pixel_check=True,
        guide=(
            "64×64 画布可以容纳多层结构（如外环 + 刻度带 + 内环 + 中心图案）。"
            "每层用 2–3 档明暗区分，层与层之间留 1–2px 透明或暗色间隔，保证缩小后仍能读出层次。"
            "圆形轮廓要用像素级阶梯画顺，避免锯齿忽粗忽细。"
        ),
    ),
    32: CanvasSizeSpec(
        size=32,
        margin_px=1,
        max_colors=16,
        min_coverage=0.03,
        max_coverage=0.75,
        preview_scale=16,
        max_tokens=4000,
        isolated_pixel_check=True,
        guide=(
            "32×32 用 4–6 档明暗表现体积，主体居中，受光面在左上。"
            "只给剪影外轮廓描一圈暗色，内部不要再描线。高光集中在一两处，不要满屏撒亮点。"
        ),
    ),
    16: CanvasSizeSpec(
        size=16,
        margin_px=1,
        max_colors=10,
        min_coverage=0.05,
        max_coverage=0.85,
        preview_scale=32,
        max_tokens=2000,
        isolated_pixel_check=True,
        guide=(
            "16×16 只用 3–4 档明暗，形状要一眼可读。少用半透明（alpha 低于 255 的颜色最多 2 种），"
            "细节宁少勿多，每个像素都要有用。"
        ),
    ),
    8: CanvasSizeSpec(
        size=8,
        margin_px=0,
        max_colors=6,
        min_coverage=0.10,
        max_coverage=0.90,
        preview_scale=64,
        max_tokens=1000,
        isolated_pixel_check=False,
        guide=(
            "8×8 每个像素都是一个特征：不要渐变、不要柔光，用 2–3 种颜色画出最简剪影，"
            "像图标一样干净。"
        ),
    ),
}

SUPPORTED_CANVAS_SIZES: tuple[int, ...] = (64, 32, 16, 8)
DEFAULT_CANVAS_SIZE = 32


def get_canvas_spec(size: int) -> CanvasSizeSpec:
    """按尺寸取参数；不支持的尺寸抛 KeyError，由上层先校验。"""
    return CANVAS_SIZES[size]
