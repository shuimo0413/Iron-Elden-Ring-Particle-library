#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「乐谱符号」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

统一风格：近白主体 + 深色描边，游戏内 ``setColor`` 乘色后主体变色、描边保持深色，仍清晰可读。

- 谱号：``music_treble_clef`` / ``music_bass_clef`` / ``music_alto_clef``
- 变音记号：``music_sharp`` / ``music_flat`` / ``music_natural`` / ``music_double_sharp`` / ``music_double_flat``
- 单个音符：二全 / 全 / 二分 / 附点二分 / 四分 / 附点四分 / 八分（符干朝上、朝下）/ 十六分 / 三十二分 / 倚音
- 连续音符（音符往往成组出现）：二分对、四分对、延音线四分对、八分 2 连 / 3 连音 / 4 连（符杠相连）、
  十六分 2 连 / 4 连、五线谱片段
- 休止符：全 / 二分 / 四分 / 八分 / 十六分（全、二分带一段谱线做参照）
- 演奏记号：延长记号、Coda、Segno、反复终止线、渐强、渐弱

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


def build_dotted_half_note() -> dict:
    """附点二分音符：空心符头 + 符干 + 附点。"""
    head_x, head_y = LARGE_HEAD_CENTER
    shape = large_note(hollow=True) | disk_mask(head_x + 9.5, head_y - 0.5, 1.7)
    return finish("music_dotted_half_note", shape)


def build_thirty_second_note() -> dict:
    """三十二分音符：符干拔高到顶，叠三条压短的符尾（每条间隔约 5 像素，描边不粘连）。"""
    stem_top_y = 2.5
    shape = large_note(hollow=False)
    shape |= line_mask([(LARGE_STEM_X, LARGE_STEM_TOP_Y), (LARGE_STEM_X, stem_top_y)], brush_size=2)
    for flag_index in range(3):
        shape |= flag_mask(stem_top_y + flag_index * 5.0, 0.5)
    return finish("music_thirty_second_note", shape)


# 符干朝下的布局（像素）：符头偏右上，符干挂在符头左缘向下，符尾在底部向右上回卷
STEM_DOWN_HEAD_CENTER = (19.0, 7.5)
STEM_DOWN_STEM_X = 15.3
STEM_DOWN_STEM_BOTTOM_Y = 27.5


def build_eighth_note_stem_down() -> dict:
    """符干朝下的八分音符：高音区的常见写法，和朝上版混着刷能让音符群更自然。

    符尾只向右上斜甩、末端不回勾：回勾会和符干围成小圈，整体读成数字 6。
    """
    head_x, head_y = STEM_DOWN_HEAD_CENTER
    shape = notehead_mask(head_x, head_y, LARGE_HEAD_RADIUS_X, LARGE_HEAD_RADIUS_Y, hollow=False)
    shape |= line_mask([(STEM_DOWN_STEM_X, head_y + 1.5), (STEM_DOWN_STEM_X, STEM_DOWN_STEM_BOTTOM_Y)], brush_size=2)
    shape |= line_mask([
        (STEM_DOWN_STEM_X + 1, STEM_DOWN_STEM_BOTTOM_Y),
        (STEM_DOWN_STEM_X + 4.5, STEM_DOWN_STEM_BOTTOM_Y - 2.5),
        (STEM_DOWN_STEM_X + 7.5, STEM_DOWN_STEM_BOTTOM_Y - 6.0),
        (STEM_DOWN_STEM_X + 8.5, STEM_DOWN_STEM_BOTTOM_Y - 10.0),
    ], brush_size=2)
    return finish("music_eighth_note_stem_down", shape)


def build_grace_note() -> dict:
    """倚音（短倚音）：八分音符 + 一道斜穿符干与符尾的斜线。

    记谱里倚音是小号字，但 32 像素粒子里缩小后斜线会和符尾糊成一团，所以沿用大号布局。
    """
    shape = large_note(hollow=False) | flag_mask(LARGE_STEM_TOP_Y)
    shape |= line_mask([(8.5, 19.0), (25.0, 7.0)], brush_size=2)
    return finish("music_grace_note", shape)


def build_breve() -> dict:
    """二全音符（倍全音符）：比全音符略小的空心符头，左右各夹两条短竖线。"""
    shape = notehead_mask(16, 16, 5.0, 3.8, hollow=True)
    for bar_x in (6.0, 8.5, 23.5, 26.0):
        shape |= line_mask([(bar_x, 10.0), (bar_x, 22.0)], brush_size=1)
    return finish("music_breve", shape)


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


# 三连音的 3 字（像素点阵，3 宽 × 5 高），左上角放在 TRIPLET_DIGIT_ORIGIN
TRIPLET_DIGIT_ROWS = ["###", "..#", ".##", "..#", "###"]
TRIPLET_DIGIT_ORIGIN = (15, 1)
TRIPLET_HEADS = [(6.0, 26.0), (15.0, 24.0), (24.0, 22.0)]


def build_eighth_triplet() -> dict:
    """八分三连音：三个八分音符一条符杠，符杠上方标一个小「3」。"""
    shape = beamed_group(TRIPLET_HEADS, 12.0, 9.0, beam_count=1)
    origin_x, origin_y = TRIPLET_DIGIT_ORIGIN
    for row_index, row in enumerate(TRIPLET_DIGIT_ROWS):
        for column_index, cell in enumerate(row):
            if cell == "#":
                shape.add((origin_x + column_index, origin_y + row_index))
    return finish("music_eighth_triplet", shape)


def build_tied_quarter_pair() -> dict:
    """两个同音高的四分音符，符头下方一条延音线（两端细、中间粗的扁弧）相连。

    弧要贴近符头、从内侧连到内侧；弧太深太宽时两个符头像眼睛，整体会读成笑脸。
    """
    heads = [(8.0, 20.0), (22.0, 20.0)]
    shape = stemmed_group(heads, [4.0, 4.0], hollow=False)
    tie_arc = [(9.5, 24.0), (12.0, 25.4), (15.0, 25.8), (18.0, 25.4), (20.5, 24.0)]
    shape |= line_mask(tie_arc, brush_size=1)
    shape |= line_mask(tie_arc[1:4], brush_size=2)
    return finish("music_tied_quarter_pair", shape)


# 五线谱片段：五条谱线的 y 坐标（像素，间距 5）
STAFF_FRAGMENT_LINE_YS = (5, 10, 15, 20, 25)


def staff_lines(line_ys: tuple[int, ...]) -> Callable[[Grid], None]:
    """补画多条整宽谱线，同样只画在空白处。"""
    def draw(grid: Grid) -> None:
        for line_y in line_ys:
            for x in range(1, 31):
                if (x, line_y) not in grid:
                    put(grid, x, line_y, STAFF_LINE_COLOR, 210)
    return draw


def build_staff_fragment() -> dict:
    """一小段五线谱 + 一对上行的八分音符，适合做「乐声飘散」的大号粒子。"""
    heads = [(10.0, 22.5), (22.0, 17.5)]
    shape = beamed_group(heads, 8.0, 3.0, beam_count=1)
    return finish("music_staff_fragment", shape, extra=staff_lines(STAFF_FRAGMENT_LINE_YS))


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


def build_double_sharp() -> dict:
    """重升号 𝄪：细 X 交叉，四个端点各压一个菱形块。"""
    shape = line_mask([(10.0, 10.0), (22.0, 22.0)], brush_size=2)
    shape |= line_mask([(22.0, 10.0), (10.0, 22.0)], brush_size=2)
    for corner_x, corner_y in ((8.5, 8.5), (23.5, 8.5), (8.5, 23.5), (23.5, 23.5)):
        shape |= polygon_mask([
            (corner_x, corner_y - 3.6),
            (corner_x + 3.6, corner_y),
            (corner_x, corner_y + 3.6),
            (corner_x - 3.6, corner_y),
        ])
    return finish("music_double_sharp", shape)


def flat_glyph(stem_x: float) -> Mask:
    """单个窄版降号：竖线 + 右下空心半圆肚，宽约 9 像素，两个并排放得下。"""
    shape = line_mask([(stem_x, 2.5), (stem_x, 28.5)], brush_size=2)
    shape |= line_mask([
        (stem_x + 1.0, 19.0), (stem_x + 3.5, 16.5), (stem_x + 6.5, 16.5),
        (stem_x + 8.0, 18.8), (stem_x + 7.0, 22.0), (stem_x + 4.5, 25.0), (stem_x + 1.0, 28.0),
    ], brush_size=2)
    return shape


def build_double_flat() -> dict:
    """重降号 𝄫：两个窄版降号并排。"""
    return finish("music_double_flat", flat_glyph(5.0) | flat_glyph(17.0))


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


# ---------------------------------------------------------------------------
# 演奏记号
# ---------------------------------------------------------------------------


def build_fermata() -> dict:
    """延长记号 𝄐：向上拱的半圆弧（两端细、顶部粗）+ 弧心一个圆点。"""
    center_x, center_y = 16.0, 22.0
    radius_x, radius_y = 12.0, 11.0
    arc = [
        (center_x + radius_x * math.cos(math.radians(angle)), center_y - radius_y * math.sin(math.radians(angle)))
        for angle in range(0, 181, 15)
    ]
    shape = line_mask(arc, brush_size=2)
    shape |= line_mask(arc[3:10], brush_size=3)
    shape |= disk_mask(center_x, center_y - 1.0, 2.4)
    return finish("music_fermata", shape)


def build_coda() -> dict:
    """Coda 𝄌：左右偏粗的椭圆环 + 穿出环外的十字。"""
    ring = ellipse_mask(16, 16, 8.5, 9.5) - ellipse_mask(16, 16, 5.5, 7.5)
    shape = ring
    shape |= line_mask([(15.5, 2.5), (15.5, 29.5)], brush_size=2)
    shape |= line_mask([(2.5, 15.5), (29.5, 15.5)], brush_size=2)
    return finish("music_coda", shape)


def build_segno() -> dict:
    """Segno 𝄋：带圆头的斜 S + 左下到右上的斜线 + S 两侧各一个圆点。

    斜线要从两个圆头之间穿过：贴着圆头走会围出两个闭环，整体读成数字 8。
    """
    s_curve = [
        (21.0, 9.0), (19.5, 6.0), (16.0, 5.0), (12.5, 6.5), (11.5, 10.0),
        (14.0, 13.5), (18.0, 16.5), (20.5, 20.0), (19.5, 24.5), (16.0, 26.5),
        (12.5, 25.5), (11.0, 22.5),
    ]
    shape = line_mask(s_curve, brush_size=2)
    shape |= line_mask(s_curve[4:8], brush_size=3)
    shape |= disk_mask(21.6, 9.6, 1.9) | disk_mask(10.4, 22.0, 1.9)
    shape |= line_mask([(11.3, 29.0), (20.7, 2.0)], brush_size=1)
    shape |= disk_mask(7.5, 13.5, 1.9) | disk_mask(24.5, 18.5, 1.9)
    return finish("music_segno", shape)


def build_repeat_end() -> dict:
    """反复终止线：左侧上下两个圆点 + 细线 + 粗线（「从头反复」的那一侧）。"""
    shape = disk_mask(10.0, 12.5, 2.0) | disk_mask(10.0, 19.5, 2.0)
    shape |= line_mask([(16.0, 4.0), (16.0, 28.0)], brush_size=2)
    shape |= {(x, y) for x in range(20, 25) for y in range(4, 29)}
    return finish("music_repeat_end", shape)


def hairpin_mask(open_on_right: bool) -> Mask:
    """渐强 / 渐弱的「发夹」：两条从一点张开的斜线。"""
    tip_x, open_x = (4.0, 27.5) if open_on_right else (27.5, 4.0)
    shape = line_mask([(tip_x, 16.0), (open_x, 8.0)], brush_size=2)
    shape |= line_mask([(tip_x, 16.0), (open_x, 24.0)], brush_size=2)
    return shape


def build_crescendo() -> dict:
    """渐强 <：开口朝右。"""
    return finish("music_crescendo", hairpin_mask(open_on_right=True))


def build_decrescendo() -> dict:
    """渐弱 >：开口朝左。"""
    return finish("music_decrescendo", hairpin_mask(open_on_right=False))


BUILDERS: list[Callable[[], dict]] = [
    build_treble_clef,
    build_bass_clef,
    build_alto_clef,
    build_sharp,
    build_flat,
    build_natural,
    build_double_sharp,
    build_double_flat,
    build_breve,
    build_whole_note,
    build_half_note,
    build_dotted_half_note,
    build_quarter_note,
    build_eighth_note,
    build_eighth_note_stem_down,
    build_sixteenth_note,
    build_thirty_second_note,
    build_dotted_quarter_note,
    build_grace_note,
    build_half_note_pair,
    build_quarter_note_pair,
    build_tied_quarter_pair,
    build_eighth_beamed_pair,
    build_eighth_triplet,
    build_eighth_beamed_four,
    build_sixteenth_beamed_pair,
    build_sixteenth_beamed_four,
    build_staff_fragment,
    build_whole_rest,
    build_half_rest,
    build_quarter_rest,
    build_eighth_rest,
    build_sixteenth_rest,
    build_fermata,
    build_coda,
    build_segno,
    build_repeat_end,
    build_crescendo,
    build_decrescendo,
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
