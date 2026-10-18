#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成第二批 64×64 通用「法阵」粒子 PNG（含像素源 JSON）。

与 ``gen_sigil_particles.py`` 的关系：
    极坐标笔画（圆弧 / 辐条 / 缺口环 / 虚线环 / 光环带）、配色约定、2px 透明边、
    alpha 阶梯全部沿用第一批，直接 import 复用；本文件只补第一批没有的
    「遮罩类」画法（实心形状 + 自动描边、齿轮、多边形填充、月相、闪电、螺旋）。

第二批九张的主题刻意和第一批错开：
    月相 / 齿轮钟 / 符文带 / 星旋 / 魔眼 / 罗盘 / 八芒印 / 雷暴 / 星图。
    第一批偏「几何 + 元素」，这一批偏「图腾 + 器物」，混用时不会撞脸。

不对称原则同第一批：外轮廓仍是大圆（可缺口），不对称体现在
缺口角度、元素大小、偏心、随机但固定种子的长度抖动上。
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from gen_sigil_particles import (
    CENTER,
    SIZE,
    dashed_ring,
    diamond_glyph,
    iter_polar,
    polar_halo,
    polar_stroke,
    put,
    put_soft,
    radial_stroke,
    regular_polygon_points,
    ring_with_gaps,
    star4,
    to_json,
)
from render_pixel_art import load_pixel_art, save_png

# 第二批独立种子基数：与第一批 0x51616C 错开，避免两批随机序列雷同。
SEED_BASE = 0x5161_C2

Grid = dict[tuple[int, int], list[int]]
Color = tuple[int, int, int]
Mask = set[tuple[int, int]]

# 主题配色：deep（暗底/辉光）→ mid（主结构）→ pale（高亮线）→ white（芯）。
# 与第一批一样整体偏亮，游戏里再乘 rCol/gCol/bCol 压暗时仍可读。
PALETTES: dict[str, dict[str, Color]] = {
    "lunar": {
        "deep": (70, 82, 140),
        "mid": (130, 148, 210),
        "pale": (204, 214, 246),
        "white": (250, 250, 255),
    },
    "bronze": {
        "deep": (112, 72, 32),
        "mid": (182, 124, 54),
        "pale": (238, 190, 108),
        "white": (255, 242, 210),
    },
    "crimson": {
        "deep": (118, 24, 42),
        "mid": (192, 54, 72),
        "pale": (246, 124, 132),
        "white": (255, 228, 228),
    },
    "nebula": {
        "deep": (24, 86, 106),
        "mid": (48, 152, 172),
        "pale": (132, 224, 228),
        "white": (232, 255, 252),
    },
    "abyss": {
        "deep": (92, 22, 72),
        "mid": (162, 48, 122),
        "pale": (232, 124, 194),
        "white": (255, 222, 242),
    },
    "steel": {
        "deep": (72, 92, 112),
        "mid": (132, 158, 184),
        "pale": (202, 220, 234),
        "white": (250, 252, 255),
    },
    "jade": {
        "deep": (30, 102, 82),
        "mid": (62, 172, 132),
        "pale": (152, 234, 198),
        "white": (234, 255, 246),
    },
    "storm": {
        "deep": (42, 72, 152),
        "mid": (92, 142, 232),
        "pale": (174, 212, 255),
        "white": (246, 250, 255),
    },
    "starlight": {
        "deep": (38, 50, 122),
        "mid": (84, 104, 204),
        "pale": (174, 188, 250),
        "white": (250, 250, 255),
    },
}

# 4 邻域：判定遮罩边缘用（8 邻域会让斜边描成 2px 粗）。
NEIGHBORS_4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
NEIGHBORS_8 = NEIGHBORS_4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


# ---------------------------------------------------------------------------
# 遮罩工具：先求「形状覆盖了哪些像素」，再决定描边 / 填充怎么上色
# ---------------------------------------------------------------------------


def polar_point(cx: float, cy: float, angle_deg: float, radius: float) -> tuple[float, float]:
    """极坐标 → 画布坐标（角度单位：度；0° 指向右，90° 指向下，与屏幕坐标一致）。"""
    return (cx + math.cos(math.radians(angle_deg)) * radius,
            cy + math.sin(math.radians(angle_deg)) * radius)


def mask_from(predicate) -> Mask:
    """遍历全画布，用像素中心坐标 (x+0.5, y+0.5) 调用 predicate 收集遮罩。"""
    return {
        (x, y)
        for y in range(SIZE)
        for x in range(SIZE)
        if predicate(x + 0.5, y + 0.5)
    }


def disc_mask(cx: float, cy: float, radius: float) -> Mask:
    """实心圆遮罩。"""
    return mask_from(lambda px, py: math.hypot(px - cx, py - cy) <= radius)


def polygon_mask(points: list[tuple[float, float]]) -> Mask:
    """任意简单多边形遮罩（射线法判内外，顶点用浮点像素坐标）。"""
    def inside(px: float, py: float) -> bool:
        crossings = False
        count = len(points)
        for index in range(count):
            x1, y1 = points[index]
            x2, y2 = points[(index + 1) % count]
            if (y1 > py) != (y2 > py):
                intersect_x = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if px < intersect_x:
                    crossings = not crossings
        return crossings
    return mask_from(inside)


def mask_edges(mask: Mask) -> Mask:
    """遮罩里「至少一个 4 邻居在遮罩外」的像素，即 1px 轮廓线。"""
    return {
        (x, y)
        for x, y in mask
        if any((x + offset_x, y + offset_y) not in mask for offset_x, offset_y in NEIGHBORS_4)
    }


def draw_mask(grid: Grid, mask: Mask, edge_color: Color, edge_alpha: float,
              fill_color: Color | None = None, fill_alpha: float = 0.0) -> None:
    """描边 + 可选填充。

    填充 alpha 建议 ≤ 110：64px 法阵里大面积高 alpha 实心块会「吃掉」结构线，
    只剩一个亮斑；低 alpha 填充读起来才像「有体积的光面」。
    """
    edges = mask_edges(mask)
    for x, y in mask:
        if (x, y) in edges:
            put(grid, x, y, edge_color, edge_alpha)
        elif fill_color is not None:
            put(grid, x, y, fill_color, fill_alpha)


def glow_around(grid: Grid, pixels: Mask, color: Color, alpha: float) -> None:
    """给一组像素外围补一圈 1px 辉光（只写空格子或更暗的格子，不覆盖主线）。"""
    for x, y in pixels:
        for offset_x, offset_y in NEIGHBORS_8:
            neighbor = (x + offset_x, y + offset_y)
            if neighbor not in pixels:
                put(grid, neighbor[0], neighbor[1], color, alpha)


def line_pixels(points: list[tuple[float, float]], closed: bool = False) -> list[tuple[int, int]]:
    """折线经过的像素（0.2px 步进，8 连通不断线），返回有序列表方便按进度渐变 alpha。"""
    sequence = list(points) + ([points[0]] if closed and len(points) > 2 else [])
    visited: list[tuple[int, int]] = []
    seen: Mask = set()
    for index in range(len(sequence) - 1):
        start_x, start_y = sequence[index]
        end_x, end_y = sequence[index + 1]
        steps = max(2, int(math.hypot(end_x - start_x, end_y - start_y) / 0.2))
        for step in range(steps + 1):
            weight = step / steps
            pixel = (int(math.floor(start_x + (end_x - start_x) * weight)),
                     int(math.floor(start_y + (end_y - start_y) * weight)))
            if pixel not in seen:
                seen.add(pixel)
                visited.append(pixel)
    return visited


def draw_line(grid: Grid, points: list[tuple[float, float]], color: Color, alpha: float,
              closed: bool = False) -> Mask:
    """画折线并返回像素集合（供 glow_around 使用）。"""
    pixels = line_pixels(points, closed)
    for x, y in pixels:
        put(grid, x, y, color, alpha)
    return set(pixels)


def gear_mask(cx: float, cy: float, root_radius: float, tooth_count: int,
              tooth_heights: list[float], phase_deg: float, hole_radius: float) -> Mask:
    """梯形齿轮遮罩（中间挖空 hole_radius）。

    齿形：前 18% 上升、中间 64% 平台、后 18% 回落。平台比例再大，
    齿根缝会窄到 1px 以下，小齿轮会糊成一个圆。
    """
    def inside(px: float, py: float) -> bool:
        distance = math.hypot(px - cx, py - cy)
        if distance < hole_radius:
            return False
        if distance <= root_radius:
            return True
        angle = math.degrees(math.atan2(py - cy, px - cx))
        normalized = ((angle - phase_deg) % 360.0) / 360.0 * tooth_count
        tooth_index = int(normalized) % tooth_count
        tooth_position = normalized - int(normalized)
        if tooth_position < 0.18:
            profile = tooth_position / 0.18
        elif tooth_position > 0.82:
            profile = (1.0 - tooth_position) / 0.18
        else:
            profile = 1.0
        return distance <= root_radius + tooth_heights[tooth_index] * profile
    return mask_from(inside)


def moon_phase_mask(cx: float, cy: float, radius: float, phase: float) -> Mask:
    """月相受光面遮罩。phase：0 = 新月（全暗），0.25 = 上弦（右半亮），0.5 = 满月，0.75 = 下弦。

    用「明暗交界线是椭圆」的标准近似：交界线横坐标 = cos(2π·phase)·√(1−v²)。
    """
    terminator = math.cos(2.0 * math.pi * phase)

    def lit(px: float, py: float) -> bool:
        normalized_x = (px - cx) / radius
        normalized_y = (py - cy) / radius
        if normalized_x * normalized_x + normalized_y * normalized_y > 1.0:
            return False
        half_chord = math.sqrt(max(0.0, 1.0 - normalized_y * normalized_y))
        if phase <= 0.5:
            return normalized_x > terminator * half_chord
        return normalized_x < -terminator * half_chord
    return mask_from(lit)


def stamp_bitmap(grid: Grid, rows: list[str], center_x: float, center_y: float,
                 color: Color, alpha: float, glow_color: Color | None = None,
                 glow_alpha: float = 0.0) -> None:
    """把字符位图（'#' 为实心）以 (center_x, center_y) 为中心盖到画布上，可附 1px 辉光。"""
    height = len(rows)
    width = len(rows[0])
    origin_x = int(round(center_x - width * 0.5))
    origin_y = int(round(center_y - height * 0.5))
    pixels: Mask = {
        (origin_x + column, origin_y + row)
        for row, line in enumerate(rows)
        for column, char in enumerate(line)
        if char == "#"
    }
    for x, y in pixels:
        put(grid, x, y, color, alpha)
    if glow_color is not None:
        glow_around(grid, pixels, glow_color, glow_alpha)


# ---------------------------------------------------------------------------
# 1. sigil_lunar：八月相环 + 中心新月
# ---------------------------------------------------------------------------


def build_sigil_lunar() -> dict:
    """月相阵：外环 + 刻度带，八枚月相按圆周排开（满月放大一号），中心一弯新月托一颗星。"""
    palette = PALETTES["lunar"]
    grid: Grid = {}
    rng = random.Random(SEED_BASE + 1)

    polar_halo(grid, CENTER, CENTER, 27.0, 3.5, palette["deep"], 60, falloff=2.2)
    polar_stroke(grid, CENTER, CENTER, 28.6, palette["pale"], 225, half_width_px=0.6)

    # 刻度带：28 根（不是 24/32，避免和八月相共用对称轴），每 7 根加长一根
    for index in range(28):
        angle = index * (360.0 / 28.0) + 4.0
        emphasized = index % 7 == 5
        radial_stroke(grid, CENTER, CENTER, angle,
                      25.0 if emphasized else 25.9, 27.4 + rng.uniform(-0.2, 0.3),
                      palette["white"] if emphasized else palette["mid"],
                      225 if emphasized else 150, 0.4)

    # 八月相：从正上方顺时针，新月 → 盈 → 满 → 亏；月相环半径 20.6px
    # （月亮半径 3.4 时外缘 24px，刚好不碰 25px 起的刻度带）
    moon_orbit_radius = 20.6
    # 相位不是严格 index/8：蛾眉月按 0.125 算只亮 1px 弧，推到 0.17 / 0.83 才有 2px 宽的月牙
    moon_phases = (0.0, 0.17, 0.25, 0.36, 0.5, 0.64, 0.75, 0.83)
    moon_angles: list[float] = []
    for index, phase in enumerate(moon_phases):
        angle = -90.0 + index * 45.0
        moon_angles.append(angle)
        # 满月（index 4）半径 3.9，其它 3.4：唯一的「大」元素，打破八等分的呆板。
        # 小于 3px 时蛾眉月只剩 1px 弧，读不出月相
        moon_radius = 3.9 if index == 4 else 3.4
        moon_x, moon_y = polar_point(CENTER, CENTER, angle, moon_orbit_radius)
        # 暗面：只描一圈暗轮廓，新月也能看到「这里有一个月亮」
        draw_mask(grid, disc_mask(moon_x, moon_y, moon_radius), palette["mid"], 165, palette["deep"], 55)
        lit = moon_phase_mask(moon_x, moon_y, moon_radius, phase)
        # 受光面整块用 white：月牙只有 1~2px 宽，若再分 pale 描边就和暗面轮廓分不开
        draw_mask(grid, lit, palette["white"], 250, palette["white"], 250)

    # 月相之间的连接弧：在每个月亮处留缺口，避免轨道线穿过暗面
    ring_with_gaps(grid, CENTER, CENTER, moon_orbit_radius, palette["mid"], 120,
                   [(angle, 27.0) for angle in moon_angles], 0.45)

    # 内环：虚线
    dashed_ring(grid, CENTER, CENTER, 13.2, palette["mid"], 160, 11.0, 7.0, phase_deg=17.0)

    # 中心新月：大圆减去右上偏移的小圆，开口朝右上
    crescent = disc_mask(CENTER - 0.5, CENTER + 0.5, 9.0) - disc_mask(CENTER + 2.9, CENTER - 2.1, 8.0)
    draw_mask(grid, crescent, palette["pale"], 235, palette["white"], 200)
    put_soft(grid, CENTER + 3.6, CENTER - 2.4, palette["white"], 245, radius_px=1.6)
    put_soft(grid, CENTER + 6.2, CENTER + 2.6, palette["pale"], 170, radius_px=0.9)

    return to_json("sigil_lunar", grid)


# ---------------------------------------------------------------------------
# 2. sigil_clockwork：钟面刻度 + 三枚咬合齿轮
# ---------------------------------------------------------------------------


def build_sigil_clockwork() -> dict:
    """齿轮钟阵：双层表圈 + 12 时标 + 分钟点，内部大中小三枚偏心齿轮互相咬合。"""
    palette = PALETTES["bronze"]
    grid: Grid = {}
    rng = random.Random(SEED_BASE + 2)

    polar_halo(grid, CENTER, CENTER, 27.6, 3.0, palette["deep"], 70, falloff=2.0)
    polar_stroke(grid, CENTER, CENTER, 28.6, palette["pale"], 225, half_width_px=0.6)
    polar_stroke(grid, CENTER, CENTER, 27.0, palette["mid"], 150, half_width_px=0.5)

    # 12 时标：12 点位置画双线，其余单线
    for hour in range(12):
        angle = -90.0 + hour * 30.0
        if hour == 0:
            for offset in (-3.2, 3.2):
                radial_stroke(grid, CENTER, CENTER, angle + offset, 22.8, 26.2,
                              palette["white"], 240, 0.5)
        else:
            radial_stroke(grid, CENTER, CENTER, angle, 23.6 if hour % 3 else 22.8, 26.2,
                          palette["pale"], 215, 0.5)
    # 分钟点：单像素，跳过时标位置
    for minute in range(60):
        if minute % 5 == 0:
            continue
        put_soft(grid, *polar_point(CENTER, CENTER, -90.0 + minute * 6.0, 25.6),
                 palette["mid"], 120, radius_px=0.6)

    # 大齿轮：偏左下，10 齿，镂空 + 5 辐
    big_center_x, big_center_y = CENTER - 4.0, CENTER + 3.0
    big_teeth = [rng.uniform(2.1, 2.7) for _ in range(10)]
    draw_mask(grid, gear_mask(big_center_x, big_center_y, 11.0, 10, big_teeth, 8.0, 7.0),
              palette["pale"], 225, palette["deep"], 95)
    for index in range(5):
        radial_stroke(grid, big_center_x, big_center_y, index * 72.0 + 20.0, 2.0, 7.2,
                      palette["mid"], 190, 0.55)
    draw_mask(grid, disc_mask(big_center_x, big_center_y, 2.2), palette["pale"], 230, palette["white"], 220)

    # 中齿轮：右上，7 齿
    middle_center_x, middle_center_y = CENTER + 9.5, CENTER - 8.0
    middle_teeth = [2.0] * 7
    draw_mask(grid, gear_mask(middle_center_x, middle_center_y, 5.2, 7, middle_teeth, 21.0, 2.0),
              palette["pale"], 220, palette["deep"], 95)
    put(grid, int(middle_center_x), int(middle_center_y), palette["white"], 235)

    # 小齿轮：右下，6 齿，实心无孔（太小了，挖孔只剩一个圈）
    small_center_x, small_center_y = CENTER + 8.0, CENTER + 13.0
    small_teeth = [1.6] * 6
    draw_mask(grid, gear_mask(small_center_x, small_center_y, 3.6, 6, small_teeth, 0.0, 0.0),
              palette["pale"], 215, palette["mid"], 110)
    put(grid, int(small_center_x), int(small_center_y), palette["white"], 240)

    return to_json("sigil_clockwork", grid)


# ---------------------------------------------------------------------------
# 3. sigil_runic：符文带 + 七芒星
# ---------------------------------------------------------------------------

# 3×5 符文字库：64px 里能读出「字」的最小尺寸；更小只剩点和横。
RUNE_GLYPHS_3X5: list[list[str]] = [
    [".#.", "##.", ".#.", ".##", ".#."],
    ["#.#", "#.#", "###", ".#.", ".#."],
    ["###", "#..", "##.", "#..", "#.."],
    ["#..", "##.", "#.#", "##.", "#.."],
    [".#.", "#.#", ".#.", "#.#", ".#."],
    ["#.#", ".#.", "#.#", ".#.", "#.#"],
    ["###", ".#.", ".#.", ".#.", "###"],
    ["#..", "#..", "###", "..#", "..#"],
    ["..#", ".#.", "#.#", ".#.", "#.."],
    ["###", "#.#", "#.#", ".#.", "#.#"],
    [".#.", ".#.", "###", ".#.", "#.#"],
    ["#..", ".#.", "..#", ".#.", "#.."],
]

# 中心大符文 5×7。
RUNE_CORE_5X7: list[str] = [
    "..#..",
    ".###.",
    "#.#.#",
    "..#..",
    ".#.#.",
    "#...#",
    "#...#",
]


def build_sigil_runic() -> dict:
    """符文阵：双环之间一圈 3×5 符文（17 字 + 1 个菱形空位），内部七芒星 {7/2} 与中心大符文。"""
    palette = PALETTES["crimson"]
    grid: Grid = {}
    rng = random.Random(SEED_BASE + 3)

    polar_halo(grid, CENTER, CENTER, 25.0, 4.6, palette["deep"], 60, falloff=2.0)
    polar_stroke(grid, CENTER, CENTER, 29.0, palette["pale"], 225, half_width_px=0.55)
    polar_stroke(grid, CENTER, CENTER, 21.2, palette["mid"], 195, half_width_px=0.5)

    # 符文带：18 个槽位（20° 一格），第 11 格换成菱形，读起来像「缺字」
    glyph_band_radius = 25.1
    blank_slot = 11
    for slot in range(18):
        angle = -90.0 + slot * 20.0 + 6.0
        slot_x, slot_y = polar_point(CENTER, CENTER, angle, glyph_band_radius)
        if slot == blank_slot:
            diamond_glyph(grid, slot_x, slot_y, 1.8, 2.6, palette["white"], palette["mid"], 230)
            continue
        glyph = RUNE_GLYPHS_3X5[rng.randrange(len(RUNE_GLYPHS_3X5))]
        stamp_bitmap(grid, glyph, slot_x, slot_y, palette["white"], 235, palette["deep"], 90)

    # 七芒星 {7/2}：整体转 5°，避免顶点正对符文缝
    heptagram_radius = 18.6
    vertices = regular_polygon_points(CENTER, CENTER, heptagram_radius, 7, -90.0 + 5.0)
    star_order = [vertices[(index * 2) % 7] for index in range(7)]
    star_pixels = draw_line(grid, star_order, palette["pale"], 215, closed=True)
    glow_around(grid, star_pixels, palette["deep"], 70)
    for vertex_x, vertex_y in vertices:
        put_soft(grid, vertex_x, vertex_y, palette["white"], 235, radius_px=1.2)

    polar_stroke(grid, CENTER, CENTER, 9.6, palette["mid"], 185, half_width_px=0.5)
    stamp_bitmap(grid, RUNE_CORE_5X7, CENTER, CENTER, palette["white"], 245, palette["mid"], 120)

    return to_json("sigil_runic", grid)


# ---------------------------------------------------------------------------
# 4. sigil_spiral：三臂星旋
# ---------------------------------------------------------------------------


def build_sigil_spiral() -> dict:
    """星旋阵：三条长度各异的对数螺旋臂从亮核甩出，臂间撒星点，外层断环 + 虚线环。"""
    palette = PALETTES["nebula"]
    grid: Grid = {}
    rng = random.Random(SEED_BASE + 4)

    polar_halo(grid, CENTER, CENTER, 27.4, 3.4, palette["deep"], 65, falloff=2.1)
    ring_with_gaps(grid, CENTER, CENTER, 28.6, palette["pale"], 215,
                   [(34.0, 12.0), (151.0, 7.0), (268.0, 18.0)], 0.55)
    dashed_ring(grid, CENTER, CENTER, 26.4, palette["mid"], 140, 6.0, 9.0, phase_deg=5.0)

    # 螺旋臂：(起始角°, 扫过角°)。扫过角不等 → 三条臂终点半径一致但长短、弯曲程度不同
    arm_specs = [(0.0, 300.0), (127.0, 340.0), (243.0, 255.0)]
    arm_start_radius = 2.8
    arm_end_radius = 24.4
    for start_deg, sweep_deg in arm_specs:
        growth = math.log(arm_end_radius / arm_start_radius) / math.radians(sweep_deg)
        sample_count = int(sweep_deg * 3)
        for sample in range(sample_count + 1):
            progress = sample / sample_count
            theta_radians = math.radians(sweep_deg) * progress
            radius = arm_start_radius * math.exp(growth * theta_radians)
            angle = start_deg + math.degrees(theta_radians)
            point_x, point_y = polar_point(CENTER, CENTER, angle, radius)
            # 臂心：前 30% 白、中段 pale、尾 25% 变 mid 并衰减
            if progress < 0.3:
                color, alpha = palette["white"], 240
            elif progress < 0.75:
                color, alpha = palette["pale"], 225
            else:
                color, alpha = palette["mid"], 210 - 80 * (progress - 0.75) / 0.25
            put(grid, int(point_x), int(point_y), color, alpha)
            # 臂外侧加一道暗边，形成 2px 的「气体带」
            outer_x, outer_y = polar_point(CENTER, CENTER, angle, radius + 1.1)
            put(grid, int(outer_x), int(outer_y), palette["deep"], 95 * (1.0 - progress * 0.6))

    # 星点：避开核心（r < 6）和外环（r > 24）
    placed = 0
    while placed < 11:
        angle = rng.uniform(0.0, 360.0)
        radius = rng.uniform(6.5, 23.5)
        point_x, point_y = polar_point(CENTER, CENTER, angle, radius)
        if (int(point_x), int(point_y)) in grid:
            continue
        put_soft(grid, point_x, point_y, palette["white"], rng.choice((150, 190, 235)),
                 radius_px=rng.choice((0.6, 0.6, 1.3)))
        placed += 1

    # 亮核
    draw_mask(grid, disc_mask(CENTER, CENTER, 2.6), palette["pale"], 235, palette["white"], 255)
    polar_halo(grid, CENTER, CENTER, 3.6, 1.6, palette["mid"], 120, falloff=1.6)

    return to_json("sigil_spiral", grid)


# ---------------------------------------------------------------------------
# 5. sigil_eye：魔眼
# ---------------------------------------------------------------------------


def build_sigil_eye() -> dict:
    """魔眼阵：两圆相交出杏仁眼眶，竖瞳留空，上睫芒 7 根、下睫芒 4 根长短不一，外围断环。"""
    palette = PALETTES["abyss"]
    grid: Grid = {}

    polar_halo(grid, CENTER, CENTER, 27.6, 3.0, palette["deep"], 70, falloff=2.0)
    ring_with_gaps(grid, CENTER, CENTER, 28.6, palette["pale"], 215,
                   [(20.0, 9.0), (95.0, 12.0), (203.0, 15.0)], 0.55)
    dashed_ring(grid, CENTER, CENTER, 26.8, palette["deep"], 150, 4.0, 4.0, phase_deg=2.0)

    # 眼眶：上眼睑 = 圆心在下方的大圆，下眼睑 = 圆心在上方的大圆，交集即杏仁形
    lid_radius = 20.0
    lid_offset = 12.4

    def in_almond(px: float, py: float) -> bool:
        return (math.hypot(px - CENTER, py - (CENTER + lid_offset)) <= lid_radius
                and math.hypot(px - CENTER, py - (CENTER - lid_offset)) <= lid_radius)

    almond = mask_from(in_almond)
    draw_mask(grid, almond, palette["pale"], 235, palette["deep"], 60)
    glow_around(grid, mask_edges(almond), palette["mid"], 90)

    # 睫芒：从眼眶外 1.5px 起，往外延伸到各自终点半径
    def ray_start_radius(angle_deg: float) -> float:
        radius = 0.0
        while in_almond(*polar_point(CENTER, CENTER, angle_deg, radius)):
            radius += 0.25
        return radius + 1.5

    upper_rays = [(-160.0, 22.5), (-137.0, 24.6), (-113.0, 21.4), (-90.0, 25.6),
                  (-66.0, 22.2), (-42.0, 24.8), (-20.0, 20.4)]
    lower_rays = [(36.0, 18.4), (71.0, 21.2), (108.0, 19.6), (147.0, 17.2)]
    for angle, end_radius in upper_rays + lower_rays:
        start_radius = ray_start_radius(angle)
        if end_radius > start_radius:
            radial_stroke(grid, CENTER, CENTER, angle, start_radius, end_radius,
                          palette["pale"], 200, 0.45)
            put_soft(grid, *polar_point(CENTER, CENTER, angle, end_radius + 0.6),
                     palette["white"], 220, radius_px=0.9)

    # 虹膜 + 竖瞳（竖瞳直接清空像素，粒子里透明 = 最暗）
    iris_center_x, iris_center_y = CENTER + 0.5, CENTER
    draw_mask(grid, disc_mask(iris_center_x, iris_center_y, 6.4), palette["pale"], 235, palette["mid"], 190)
    polar_stroke(grid, iris_center_x, iris_center_y, 4.2, palette["deep"], 200, half_width_px=0.45)
    pupil = mask_from(lambda px, py: ((px - iris_center_x) / 1.4) ** 2 + ((py - iris_center_y) / 4.8) ** 2 <= 1.0)
    for pixel in pupil:
        grid.pop(pixel, None)
    put_soft(grid, iris_center_x - 3.0, iris_center_y - 3.0, palette["white"], 250, radius_px=1.2)

    return to_json("sigil_eye", grid)


# ---------------------------------------------------------------------------
# 6. sigil_compass：罗盘（磁偏角）
# ---------------------------------------------------------------------------


def build_sigil_compass() -> dict:
    """罗盘阵：表圈按真北刻 72 格，八芒罗盘玫瑰整体偏转 −8°（磁偏角），北针加长并在表圈顶端标菱形。"""
    palette = PALETTES["steel"]
    grid: Grid = {}

    polar_halo(grid, CENTER, CENTER, 27.6, 3.0, palette["deep"], 65, falloff=2.0)
    polar_stroke(grid, CENTER, CENTER, 28.6, palette["pale"], 225, half_width_px=0.6)

    # 表圈刻度（按真北，不随玫瑰偏转）：5° 短、15° 中、90° 长（正北让给菱形标记）
    for index in range(72):
        angle = -90.0 + index * 5.0
        if index == 0:
            continue
        if index % 18 == 0:
            radial_stroke(grid, CENTER, CENTER, angle, 23.8, 27.9, palette["white"], 235, 0.5)
        elif index % 3 == 0:
            radial_stroke(grid, CENTER, CENTER, angle, 25.4, 27.9, palette["pale"], 195, 0.42)
        else:
            radial_stroke(grid, CENTER, CENTER, angle, 26.8, 27.9, palette["mid"], 140, 0.4)
    diamond_glyph(grid, *polar_point(CENTER, CENTER, -90.0, 25.6), 1.8, 2.6,
                  palette["white"], palette["pale"], 245)

    # 罗盘玫瑰：每根针是风筝形，左半亮、右半暗（经典立体针）
    declination_deg = -8.0
    needle_specs: list[tuple[float, float, float]] = []
    for index in range(8):
        angle = -90.0 + declination_deg + index * 45.0
        if index == 0:
            needle_specs.append((angle, 21.6, 3.2))
        elif index % 2 == 0:
            needle_specs.append((angle, 17.6, 3.2))
        else:
            needle_specs.append((angle, 11.2, 2.2))

    # 先画短的对角针，再画长针，让长针盖在上面
    for angle, length, half_width in sorted(needle_specs, key=lambda spec: spec[1]):
        tip = polar_point(CENTER, CENTER, angle, length)
        left = polar_point(CENTER, CENTER, angle - 90.0, half_width)
        right = polar_point(CENTER, CENTER, angle + 90.0, half_width)
        center = (CENTER, CENTER)
        bright_half = polygon_mask([center, left, tip])
        dim_half = polygon_mask([center, tip, right])
        for pixel in bright_half:
            grid[pixel] = [*palette["pale"], 230]
        for pixel in dim_half - bright_half:
            grid[pixel] = [*palette["deep"], 200]
        put(grid, int(tip[0]), int(tip[1]), palette["white"], 250)

    # 内环：在主针经过处留缺口
    ring_with_gaps(grid, CENTER, CENTER, 20.2, palette["mid"], 150,
                   [(spec[0], 14.0) for spec in needle_specs if spec[1] > 20.0], 0.45)
    polar_stroke(grid, CENTER, CENTER, 14.4, palette["deep"], 120, half_width_px=0.45)
    draw_mask(grid, disc_mask(CENTER, CENTER, 1.8), palette["white"], 250, palette["white"], 250)

    return to_json("sigil_compass", grid)


# ---------------------------------------------------------------------------
# 7. sigil_octagram：双方交叠八芒印
# ---------------------------------------------------------------------------


def build_sigil_octagram() -> dict:
    """八芒印：两个正方形 45° 交叠成八芒星，内切圆 + 偏转 7° 的内方 + 中心小印；只有三个尖角挂圆珠。"""
    palette = PALETTES["jade"]
    grid: Grid = {}

    polar_halo(grid, CENTER, CENTER, 26.0, 4.0, palette["deep"], 60, falloff=2.0)
    ring_with_gaps(grid, CENTER, CENTER, 28.6, palette["pale"], 220,
                   [(-67.5, 10.0), (112.5, 6.0)], 0.55)

    star_radius = 25.0
    square_a = regular_polygon_points(CENTER, CENTER, star_radius, 4, -90.0)
    square_b = regular_polygon_points(CENTER, CENTER, star_radius, 4, -45.0)
    pixels_a = draw_line(grid, square_a, palette["pale"], 225, closed=True)
    pixels_b = draw_line(grid, square_b, palette["mid"], 205, closed=True)
    glow_around(grid, pixels_a | pixels_b, palette["deep"], 75)

    # 八芒尖角之间的外圈小点（半径 27，正好卡在尖角与外环之间）
    for index in range(8):
        put_soft(grid, *polar_point(CENTER, CENTER, -67.5 + index * 45.0, 26.6),
                 palette["mid"], 160, radius_px=0.7)

    # 三个尖角挂圆珠（−90° / 45° / 180°），其余五个空着
    for angle in (-90.0, 45.0, 180.0):
        bead_x, bead_y = polar_point(CENTER, CENTER, angle, star_radius)
        draw_mask(grid, disc_mask(bead_x, bead_y, 2.0), palette["white"], 240, palette["pale"], 200)

    # 交叠八边形的内切圆（正方形内切半径 25·cos45° ≈ 17.7，再收 0.9px 不贴线）
    polar_stroke(grid, CENTER, CENTER, 16.8, palette["pale"], 200, half_width_px=0.5)
    dashed_ring(grid, CENTER, CENTER, 14.6, palette["mid"], 140, 8.0, 6.0, phase_deg=11.0)

    inner_square = regular_polygon_points(CENTER, CENTER, 10.6, 4, -45.0 + 7.0)
    draw_line(grid, inner_square, palette["pale"], 215, closed=True)

    # 中心小印：方框 + 四角点 + 芯
    seal_rows = [
        "#.....#",
        ".#####.",
        ".#...#.",
        ".#.#.#.",
        ".#...#.",
        ".#####.",
        "#.....#",
    ]
    stamp_bitmap(grid, seal_rows, CENTER, CENTER, palette["white"], 240, palette["deep"], 90)

    return to_json("sigil_octagram", grid)


# ---------------------------------------------------------------------------
# 8. sigil_storm：雷暴
# ---------------------------------------------------------------------------


def build_bolt_points(rng: random.Random, angle_deg: float, start_radius: float,
                      end_radius: float, joints: int, lateral_px: float) -> list[tuple[float, float]]:
    """一条径向闪电的折点：半径均分，每个折点沿切向左右交替偏移，幅度随机。"""
    points = [polar_point(CENTER, CENTER, angle_deg, start_radius)]
    side = rng.choice((-1.0, 1.0))
    for joint in range(1, joints):
        radius = start_radius + (end_radius - start_radius) * joint / joints
        lateral = side * rng.uniform(lateral_px * 0.5, lateral_px)
        offset_deg = math.degrees(lateral / radius)
        points.append(polar_point(CENTER, CENTER, angle_deg + offset_deg, radius))
        side = -side
    points.append(polar_point(CENTER, CENTER, angle_deg, end_radius))
    return points


def build_sigil_storm() -> dict:
    """雷暴阵：碎裂外环 + 双层内环，七道不等距不等长闪电向外劈出，其中三道带分叉。"""
    palette = PALETTES["storm"]
    grid: Grid = {}
    rng = random.Random(SEED_BASE + 8)

    polar_halo(grid, CENTER, CENTER, 27.8, 3.0, palette["deep"], 75, falloff=2.0)
    # 八处缺口：固定角度（随机角度可能互相重叠，segment_spans 会算出反向的整圈弧）
    ring_with_gaps(grid, CENTER, CENTER, 28.6, palette["pale"], 215,
                   [(8.0, 6.0), (47.0, 10.0), (101.0, 4.5), (139.0, 8.0),
                    (188.0, 11.0), (236.0, 5.0), (281.0, 9.0), (327.0, 6.5)], 0.55)

    polar_stroke(grid, CENTER, CENTER, 9.8, palette["pale"], 225, half_width_px=0.5)
    polar_stroke(grid, CENTER, CENTER, 8.2, palette["mid"], 170, half_width_px=0.45)

    bolt_pixels: Mask = set()
    fork_bolts = {1, 3, 5}
    for index in range(7):
        angle = index * (360.0 / 7.0) + 9.0 + rng.uniform(-9.0, 9.0)
        end_radius = rng.uniform(23.0, 27.6)
        points = build_bolt_points(rng, angle, 10.6, end_radius, 5, 2.0)
        bolt_pixels |= draw_line(grid, points, palette["pale"], 230)
        # 闪电根部两格白芯：像是从内环「迸」出来
        for pixel in line_pixels(points[:2])[:3]:
            put(grid, pixel[0], pixel[1], palette["white"], 250)
        put_soft(grid, *points[-1], palette["white"], 235, radius_px=1.1)
        if index in fork_bolts:
            fork_origin = points[2]
            fork_angle_offset = rng.choice((-1.0, 1.0)) * rng.uniform(22.0, 32.0)
            fork_radius = math.hypot(fork_origin[0] - CENTER, fork_origin[1] - CENTER)
            fork_points = [
                fork_origin,
                polar_point(CENTER, CENTER, angle + fork_angle_offset * 0.6, fork_radius + 3.0),
                polar_point(CENTER, CENTER, angle + fork_angle_offset, fork_radius + 6.0),
            ]
            bolt_pixels |= draw_line(grid, fork_points, palette["mid"], 190)

    glow_around(grid, bolt_pixels, palette["deep"], 85)

    # 雷云弧：闪电之间零散的短弧
    for _ in range(5):
        polar_stroke(grid, CENTER, CENTER, rng.uniform(15.0, 20.0), palette["mid"], 130,
                     rng.uniform(0.0, 360.0), rng.uniform(10.0, 22.0), 0.45)

    star4(grid, CENTER, CENTER, 5, palette["pale"], palette["white"], 245)

    return to_json("sigil_storm", grid)


# ---------------------------------------------------------------------------
# 9. sigil_constellation：星图
# ---------------------------------------------------------------------------


def build_sigil_constellation() -> dict:
    """星图阵：外环 + 星表刻点，两组连线星座、一条倾斜轨道椭圆与一颗行星，背景零星暗星。"""
    palette = PALETTES["starlight"]
    grid: Grid = {}
    rng = random.Random(SEED_BASE + 9)

    polar_halo(grid, CENTER, CENTER, 27.6, 3.0, palette["deep"], 65, falloff=2.0)
    polar_stroke(grid, CENTER, CENTER, 28.6, palette["pale"], 215, half_width_px=0.55)

    # 星表刻点：每 7.5° 一点，四个「象限标」偏 10° 加长
    for index in range(48):
        put_soft(grid, *polar_point(CENTER, CENTER, index * 7.5, 26.7), palette["mid"], 150, radius_px=0.6)
    for angle in (-80.0, 10.0, 100.0, 190.0):
        radial_stroke(grid, CENTER, CENTER, angle, 25.2, 27.9, palette["pale"], 210, 0.45)

    # 倾斜轨道：椭圆 a=22 b=8 倾角 −28°，虚线（每 14° 画 9°）
    orbit_semi_major, orbit_semi_minor, orbit_tilt = 22.0, 8.0, math.radians(-28.0)

    def orbit_point(parameter_deg: float) -> tuple[float, float]:
        local_x = math.cos(math.radians(parameter_deg)) * orbit_semi_major
        local_y = math.sin(math.radians(parameter_deg)) * orbit_semi_minor
        return (CENTER + local_x * math.cos(orbit_tilt) - local_y * math.sin(orbit_tilt),
                CENTER + local_x * math.sin(orbit_tilt) + local_y * math.cos(orbit_tilt))

    for dash_start in range(0, 360, 14):
        draw_line(grid, [orbit_point(dash_start + step) for step in range(0, 10, 3)],
                  palette["deep"], 115)
    planet_x, planet_y = orbit_point(200.0)
    draw_mask(grid, disc_mask(planet_x, planet_y, 1.9), palette["pale"], 235, palette["white"], 235)

    # 星座 A（左上，6 星）与星座 B（右下，5 星）：坐标为画布像素
    constellation_a = [(17.5, 21.5), (22.5, 15.5), (30.5, 13.5), (28.5, 21.5), (35.5, 24.5), (40.5, 18.5)]
    links_a = [(0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5)]
    constellation_b = [(37.5, 40.5), (44.5, 35.5), (48.5, 42.5), (42.5, 48.5), (33.5, 47.5)]
    links_b = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 3)]
    for stars, links in ((constellation_a, links_a), (constellation_b, links_b)):
        for start_index, end_index in links:
            draw_line(grid, [stars[start_index], stars[end_index]], palette["mid"], 175)
        for star_x, star_y in stars:
            put_soft(grid, star_x, star_y, palette["white"], rng.choice((215, 235, 250)),
                     radius_px=rng.choice((0.9, 1.3, 1.6)))

    # 主星：星座 B 第二颗，用四角星强调
    star4(grid, constellation_b[1][0], constellation_b[1][1], 3, palette["pale"], palette["white"], 250)

    # 背景暗星：只落在空格上
    placed = 0
    while placed < 9:
        angle = rng.uniform(0.0, 360.0)
        radius = rng.uniform(4.0, 24.0)
        point_x, point_y = polar_point(CENTER, CENTER, angle, radius)
        if any((int(point_x) + offset_x, int(point_y) + offset_y) in grid
               for offset_x in (-1, 0, 1) for offset_y in (-1, 0, 1)):
            continue
        put(grid, int(point_x), int(point_y), palette["pale"], rng.choice((110, 140, 170)))
        placed += 1

    return to_json("sigil_constellation", grid)


BUILDERS = [
    build_sigil_lunar,
    build_sigil_clockwork,
    build_sigil_runic,
    build_sigil_spiral,
    build_sigil_eye,
    build_sigil_compass,
    build_sigil_octagram,
    build_sigil_storm,
    build_sigil_constellation,
]


def main() -> int:
    tool_dir = Path(__file__).absolute().parent
    origin_dir = tool_dir / "origin_json"
    library_dir = tool_dir.parent
    origin_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for builder in BUILDERS:
        data = builder()
        name = data["name"]
        json_path = origin_dir / f"{name}.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        art = load_pixel_art(json_path)
        png_path = library_dir / f"{name}.png"
        save_png(art, png_path, scale=1)
        written.append(f"{name}: {len(data['pixels'])} px → {png_path.name}")

    print(f"已生成 {len(written)} 张 64×64 法阵粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin_dir}")
    print(f"PNG:  {library_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
