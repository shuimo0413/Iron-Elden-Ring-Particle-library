#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「乐谱符号」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

统一风格：近白主体 + 深色描边，游戏内 ``setColor`` 乘色后主体变色、描边保持深色，仍清晰可读。

- 谱号：``music_treble_clef`` / ``music_bass_clef`` / ``music_alto_clef``
- 变音记号：``music_sharp`` / ``music_flat`` / ``music_natural``
- 单个音符：全 / 二分 / 四分 / 八分 / 十六分 / 附点四分
- 连续音符（音符往往成组出现）：二分对、四分对、八分 2 连 / 4 连（符杠相连）、十六分 2 连 / 4 连
- 休止符：全 / 二分 / 四分 / 八分 / 十六分（全、二分带一段谱线做参照）

绘制函数复用 ``gen_generic_particles``。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

from gen_generic_particles import (
    SIZE,
    SYMBOL_FILL,
    SYMBOL_OUTLINE,
    Grid,
    Mask,
    fill_mask,
    line_mask,
    outline_mask,
    polygon_mask,
    put,
    to_json,
)
from render_pixel_art import load_pixel_art, save_png

# 谱线：比描边浅，作为休止符的位置参照，不抢主体
STAFF_LINE_COLOR = (150, 152, 165)

# 符头倾斜角（度）：负值 = 右上翘，标准印刷体约 -20°
NOTEHEAD_TILT_DEGREES = -20.0

# 单音符（大号）符头半径（像素）：调大更醒目，但会挤占符尾空间
LARGE_HEAD_RADIUS_X = 4.2
LARGE_HEAD_RADIUS_Y = 3.0
# 成组音符（小号）符头半径（像素）：2 连音用
SMALL_HEAD_RADIUS_X = 3.1
SMALL_HEAD_RADIUS_Y = 2.2
# 4 连音每个音符只有约 7 像素宽，符头再缩一档，否则描边会把相邻符头连成一片
TINY_HEAD_RADIUS_X = 2.6
TINY_HEAD_RADIUS_Y = 1.9


# ---------------------------------------------------------------------------
# 基础形状
# ---------------------------------------------------------------------------


def ellipse_mask(center_x: float, center_y: float, radius_x: float, radius_y: float, tilt_degrees: float = 0.0) -> Mask:
    """倾斜椭圆像素集合（以像素中心判定）。"""
    tilt = math.radians(tilt_degrees)
    cos_tilt, sin_tilt = math.cos(tilt), math.sin(tilt)
    mask: Mask = set()
    for y in range(SIZE):
        for x in range(SIZE):
            offset_x = x + 0.5 - center_x
            offset_y = y + 0.5 - center_y
            local_x = offset_x * cos_tilt + offset_y * sin_tilt
            local_y = -offset_x * sin_tilt + offset_y * cos_tilt
            if (local_x / radius_x) ** 2 + (local_y / radius_y) ** 2 <= 1.0:
                mask.add((x, y))
    return mask


def disk_mask(center_x: float, center_y: float, radius: float) -> Mask:
    return ellipse_mask(center_x, center_y, radius, radius)


def notehead_mask(center_x: float, center_y: float, radius_x: float, radius_y: float, hollow: bool) -> Mask:
    """符头：实心（四分及更短）或空心（二分 / 全音符，中间挖一个更斜的窄孔）。"""
    head = ellipse_mask(center_x, center_y, radius_x, radius_y, NOTEHEAD_TILT_DEGREES)
    if hollow:
        hole = ellipse_mask(center_x, center_y, radius_x * 0.62, radius_y * 0.42, NOTEHEAD_TILT_DEGREES - 15)
        head -= hole
    return head


def beam_mask(start_x: float, start_y: float, end_x: float, end_y: float, thickness: float) -> Mask:
    """符杠：从 start 到 end 的平行四边形，竖直方向厚 ``thickness`` 像素。"""
    return polygon_mask([
        (start_x, start_y),
        (end_x, end_y),
        (end_x, end_y + thickness),
        (start_x, start_y + thickness),
    ])


def finish(name: str, shape: Mask, extra: Callable[[Grid], None] | None = None) -> dict:
    """统一上色：近白填充 + 深色描边；``extra`` 用于在描边之后补画谱线等附件。"""
    grid: Grid = {}
    fill_mask(grid, shape, SYMBOL_FILL, 255)
    outline_mask(grid, shape, SYMBOL_OUTLINE, 255)
    if extra is not None:
        extra(grid)
    return to_json(name, grid)


# ---------------------------------------------------------------------------
# 单个音符
# ---------------------------------------------------------------------------

# 大号单音符的布局（像素）：符头偏左下，符干从符头右缘向上
LARGE_HEAD_CENTER = (12.0, 24.0)
LARGE_STEM_X = 15.5
LARGE_STEM_TOP_Y = 4.5


def large_note(hollow: bool, with_stem: bool = True) -> Mask:
    head_x, head_y = LARGE_HEAD_CENTER
    shape = notehead_mask(head_x, head_y, LARGE_HEAD_RADIUS_X, LARGE_HEAD_RADIUS_Y, hollow)
    if with_stem:
        shape |= line_mask([(LARGE_STEM_X, head_y - 1.5), (LARGE_STEM_X, LARGE_STEM_TOP_Y)], brush_size=2)
    return shape


def flag_mask(top_y: float, length_scale: float = 1.0) -> Mask:
    """八分符尾：从符干顶部向右下甩出的弯钩；``length_scale`` < 1 时竖向压短（十六分叠两条用）。"""
    return line_mask([
        (LARGE_STEM_X + 1, top_y),
        (LARGE_STEM_X + 5, top_y + 3.5 * length_scale),
        (LARGE_STEM_X + 7.5, top_y + 7.5 * length_scale),
        (LARGE_STEM_X + 6.5, top_y + 12 * length_scale),
    ], brush_size=2)


def build_whole_note() -> dict:
    """全音符：无符干的大空心符头，比其他符头更宽更扁。"""
    shape = notehead_mask(16, 16, 6.2, 4.4, hollow=True)
    return finish("music_whole_note", shape)


def build_half_note() -> dict:
    """二分音符：空心符头 + 符干。"""
    return finish("music_half_note", large_note(hollow=True))


def build_quarter_note() -> dict:
    """四分音符：实心符头 + 符干。"""
    return finish("music_quarter_note", large_note(hollow=False))


def build_eighth_note() -> dict:
    """八分音符：四分 + 一条符尾。"""
    return finish("music_eighth_note", large_note(hollow=False) | flag_mask(LARGE_STEM_TOP_Y))


def build_sixteenth_note() -> dict:
    """十六分音符：四分 + 两条符尾。"""
    shape = large_note(hollow=False) | flag_mask(LARGE_STEM_TOP_Y, 0.7) | flag_mask(LARGE_STEM_TOP_Y + 6.5, 0.7)
    return finish("music_sixteenth_note", shape)


def build_dotted_quarter_note() -> dict:
    """附点四分音符：符头右侧加一个附点（时值延长一半）。"""
    head_x, head_y = LARGE_HEAD_CENTER
    shape = large_note(hollow=False) | disk_mask(head_x + 9.5, head_y - 0.5, 1.7)
    return finish("music_dotted_quarter_note", shape)


# ---------------------------------------------------------------------------
# 连续音符
# ---------------------------------------------------------------------------

# 符杠竖直厚度（像素）与两条符杠之间的间距（像素）
BEAM_THICKNESS = 2.4
BEAM_SPACING = 4.0


def stemmed_group(head_centers: list[tuple[float, float]], stem_tops: list[float], hollow: bool) -> Mask:
    """一组带符干的小号音符：符干顶部 y 由 ``stem_tops`` 给出；超过 2 个音符自动换更小符头。"""
    crowded = len(head_centers) > 2
    radius_x = TINY_HEAD_RADIUS_X if crowded else SMALL_HEAD_RADIUS_X
    radius_y = TINY_HEAD_RADIUS_Y if crowded else SMALL_HEAD_RADIUS_Y
    stem_offset_x = radius_x - 0.5
    shape: Mask = set()
    for (head_x, head_y), stem_top_y in zip(head_centers, stem_tops):
        shape |= notehead_mask(head_x, head_y, radius_x, radius_y, hollow)
        stem_x = head_x + stem_offset_x
        shape |= line_mask([(stem_x, head_y - 1), (stem_x, stem_top_y)], brush_size=1)
    return shape


def beamed_group(head_centers: list[tuple[float, float]], beam_start_y: float, beam_end_y: float, beam_count: int) -> Mask:
    """符杠相连的一组音符：符干顶部落在符杠斜线上，``beam_count`` = 1 为八分、2 为十六分。"""
    stem_offset_x = (TINY_HEAD_RADIUS_X if len(head_centers) > 2 else SMALL_HEAD_RADIUS_X) - 0.5
    first_stem_x = head_centers[0][0] + stem_offset_x
    last_stem_x = head_centers[-1][0] + stem_offset_x
    slope = (beam_end_y - beam_start_y) / (last_stem_x - first_stem_x)
    stem_tops = [beam_start_y + slope * (head_x + stem_offset_x - first_stem_x) for head_x, _ in head_centers]
    shape = stemmed_group(head_centers, stem_tops, hollow=False)
    for beam_index in range(beam_count):
        offset_y = beam_index * BEAM_SPACING
        shape |= beam_mask(first_stem_x - 0.5, beam_start_y + offset_y,
                           last_stem_x + 1.5, beam_end_y + offset_y + slope * 2, BEAM_THICKNESS)
    return shape


PAIR_HEADS = [(8.0, 25.0), (21.0, 21.0)]
FOUR_HEADS = [(5.0, 26.5), (12.0, 23.5), (19.0, 25.0), (26.0, 21.0)]


def build_half_note_pair() -> dict:
    """两个二分音符（上行）。二分音符没有符杠，只是并排出现。"""
    return finish("music_half_note_pair", stemmed_group(PAIR_HEADS, [8.0, 4.0], hollow=True))


def build_quarter_note_pair() -> dict:
    """两个四分音符（上行）。"""
    return finish("music_quarter_note_pair", stemmed_group(PAIR_HEADS, [8.0, 4.0], hollow=False))


def build_eighth_beamed_pair() -> dict:
    """两个八分音符，一条符杠相连（经典 ♫）。"""
    return finish("music_eighth_beamed_pair", beamed_group(PAIR_HEADS, 7.0, 4.0, beam_count=1))


def build_eighth_beamed_four() -> dict:
    """四个八分音符一组，一条符杠。"""
    return finish("music_eighth_beamed_four", beamed_group(FOUR_HEADS, 8.0, 5.0, beam_count=1))


def build_sixteenth_beamed_pair() -> dict:
    """两个十六分音符，两条符杠（♬）。"""
    return finish("music_sixteenth_beamed_pair", beamed_group(PAIR_HEADS, 6.0, 3.0, beam_count=2))


def build_sixteenth_beamed_four() -> dict:
    """四个十六分音符一组，两条符杠。"""
    return finish("music_sixteenth_beamed_four", beamed_group(FOUR_HEADS, 6.0, 3.0, beam_count=2))


# ---------------------------------------------------------------------------
# 谱号
# ---------------------------------------------------------------------------


def build_treble_clef() -> dict:
    """高音谱号（G 谱号）：底部圆点尾 → 竖脊上行 → 顶部小环 → 斜下 → 绕 G 线螺旋收尾。"""
    spine_and_spiral = [
        (12.5, 28.0), (14.5, 29.5), (16.8, 29.0), (17.8, 27.0),
        (17.2, 22.0), (16.3, 16.0), (15.6, 10.5), (15.2, 6.0),
        (15.8, 2.8), (17.4, 1.6), (18.8, 2.8), (18.6, 5.5),
        (17.0, 8.5), (14.0, 11.5), (11.0, 14.5), (9.0, 17.5),
        (8.6, 20.5), (9.8, 23.3), (12.3, 25.0), (15.8, 25.3),
        (19.0, 24.2), (20.8, 21.8), (20.6, 19.0), (18.6, 17.2),
        (15.8, 17.0), (13.6, 18.3), (13.0, 20.6), (14.2, 22.2),
    ]
    shape = line_mask(spine_and_spiral, brush_size=2) | disk_mask(11.8, 27.6, 2.3)
    return finish("music_treble_clef", shape)


def build_bass_clef() -> dict:
    """低音谱号（F 谱号）：左上实心圆头 + 向右下收的反 C 弧 + 右侧两点（夹住 F 线）。"""
    arc = [
        (9.0, 10.0), (10.0, 6.8), (13.0, 4.8), (17.0, 4.8), (20.2, 6.8),
        (21.4, 10.5), (20.6, 14.5), (18.0, 18.5), (14.0, 22.5), (8.0, 26.5),
    ]
    shape = line_mask(arc, brush_size=2)
    shape |= line_mask(arc[3:7], brush_size=3)
    shape |= disk_mask(9.0, 10.5, 2.8)
    shape |= disk_mask(26.0, 8.0, 1.6)
    shape |= disk_mask(26.0, 14.0, 1.6)
    return finish("music_bass_clef", shape)


def build_alto_clef() -> dict:
    """中音谱号（C 谱号）：左侧粗细两竖 + 右侧上下对称两个 C 弧，尖端指向中线（中央 C）。"""
    upper_lobe = [
        (12.5, 16.0), (14.8, 12.6), (18.5, 13.8), (22.2, 12.4), (24.2, 9.0),
        (23.2, 5.4), (19.8, 3.6), (16.4, 4.6),
    ]
    lower_lobe = [(x, 32.0 - y) for x, y in upper_lobe]
    shape = line_mask([(7.0, 3.5), (7.0, 28.5)], brush_size=3)
    shape |= line_mask([(11.0, 3.5), (11.0, 28.5)], brush_size=1)
    shape |= line_mask(upper_lobe, brush_size=2) | line_mask(lower_lobe, brush_size=2)
    shape |= line_mask(upper_lobe[2:5], brush_size=3) | line_mask(lower_lobe[2:5], brush_size=3)
    shape |= disk_mask(16.8, 6.4, 1.9) | disk_mask(16.8, 25.6, 1.9)
    return finish("music_alto_clef", shape)


# ---------------------------------------------------------------------------
# 变音记号
# ---------------------------------------------------------------------------


def build_sharp() -> dict:
    """升号 ♯：两条竖线 + 两条右上斜的粗横杠。"""
    shape = line_mask([(12.0, 6.0), (12.0, 28.0)], brush_size=2)
    shape |= line_mask([(19.0, 3.5), (19.0, 25.5)], brush_size=2)
    shape |= beam_mask(7.0, 12.5, 25.0, 9.0, 3.0)
    shape |= beam_mask(7.0, 21.0, 25.0, 17.5, 3.0)
    return finish("music_sharp", shape)


def build_flat() -> dict:
    """降号 ♭：长竖线 + 右下空心半圆肚。"""
    shape = line_mask([(11.0, 2.5), (11.0, 28.5)], brush_size=2)
    shape |= line_mask([
        (12.0, 18.0), (15.5, 15.5), (19.5, 15.3), (21.6, 17.6),
        (20.8, 21.2), (17.5, 24.5), (12.5, 28.0),
    ], brush_size=2)
    return finish("music_flat", shape)


def build_natural() -> dict:
    """还原号 ♮：左竖线偏上、右竖线偏下，中间两条斜粗杠。"""
    shape = line_mask([(11.0, 3.5), (11.0, 22.0)], brush_size=2)
    shape |= line_mask([(20.0, 10.0), (20.0, 28.5)], brush_size=2)
    shape |= beam_mask(11.0, 12.0, 21.5, 9.0, 3.0)
    shape |= beam_mask(11.0, 20.5, 21.5, 17.5, 3.0)
    return finish("music_natural", shape)


# ---------------------------------------------------------------------------
# 休止符
# ---------------------------------------------------------------------------


def staff_line(line_y: int) -> Callable[[Grid], None]:
    """返回一个补画谱线的回调：谱线只画在空白处，不覆盖符号本体。"""
    def draw(grid: Grid) -> None:
        for x in range(4, 28):
            if (x, line_y) not in grid:
                put(grid, x, line_y, STAFF_LINE_COLOR, 210)
    return draw


def build_whole_rest() -> dict:
    """全休止符：倒挂在谱线下方的实心矩形。"""
    block = {(x, y) for x in range(11, 21) for y in range(13, 18)}
    return finish("music_whole_rest", block, extra=staff_line(12))


def build_half_rest() -> dict:
    """二分休止符：立在谱线上方的实心矩形。"""
    block = {(x, y) for x in range(11, 21) for y in range(14, 19)}
    return finish("music_half_rest", block, extra=staff_line(19))


def build_quarter_rest() -> dict:
    """四分休止符：竖向闪电折线 + 底部反钩。"""
    zigzag = [(13.0, 3.0), (19.0, 10.0), (15.0, 14.5), (20.0, 21.0)]
    hook = [(20.0, 21.0), (16.0, 19.8), (13.0, 22.5), (14.0, 26.5), (16.5, 28.5)]
    shape = line_mask(zigzag, brush_size=3) | line_mask(hook, brush_size=2)
    return finish("music_quarter_rest", shape)


def build_eighth_rest() -> dict:
    """八分休止符：左上圆点 + 向右上翘的小钩 + 斜向左下的杆。"""
    shape = disk_mask(11.5, 10.0, 2.6)
    shape |= line_mask([(11.5, 12.0), (15.5, 12.8), (20.5, 8.5)], brush_size=2)
    shape |= line_mask([(20.5, 8.5), (14.0, 27.5)], brush_size=2)
    return finish("music_eighth_rest", shape)


def build_sixteenth_rest() -> dict:
    """十六分休止符：两个圆点钩挂在同一根斜杆上。"""
    def stem_x_at(y: float) -> float:
        return 21.5 - 8.5 * (y - 4.0) / 24.0

    shape = line_mask([(stem_x_at(4.0), 4.0), (stem_x_at(28.0), 28.0)], brush_size=2)
    for dot_x, dot_y, hook_end_y in ((11.0, 7.5, 6.5), (8.5, 15.5, 14.5)):
        shape |= disk_mask(dot_x, dot_y, 2.3)
        shape |= line_mask([(dot_x, dot_y + 2.0), (dot_x + 4.0, dot_y + 2.6),
                            (stem_x_at(hook_end_y), hook_end_y)], brush_size=2)
    return finish("music_sixteenth_rest", shape)


BUILDERS: list[Callable[[], dict]] = [
    build_treble_clef,
    build_bass_clef,
    build_alto_clef,
    build_sharp,
    build_flat,
    build_natural,
    build_whole_note,
    build_half_note,
    build_quarter_note,
    build_eighth_note,
    build_sixteenth_note,
    build_dotted_quarter_note,
    build_half_note_pair,
    build_quarter_note_pair,
    build_eighth_beamed_pair,
    build_eighth_beamed_four,
    build_sixteenth_beamed_pair,
    build_sixteenth_beamed_four,
    build_whole_rest,
    build_half_rest,
    build_quarter_rest,
    build_eighth_rest,
    build_sixteenth_rest,
]


def main() -> int:
    tool_dir = Path(__file__).absolute().parent
    origin = tool_dir / "origin_json"
    library = tool_dir.parent
    origin.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for builder in BUILDERS:
        data = builder()
        name = data["name"]
        json_path = origin / f"{name}.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        art = load_pixel_art(json_path)
        png_path = library / f"{name}.png"
        save_png(art, png_path, scale=1)
        written.append(f"{name}: {len(data['pixels'])} px → {png_path.name}")

    print(f"已生成 {len(written)} 个乐谱粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
