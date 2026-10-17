#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 64×64 通用「法阵」粒子 PNG（含像素源 JSON）。

为什么是 64×64 而不是库内惯例的 32×32：
    32×32 去掉四周 2px 留白后可用圆直径只有约 28px，外环 2px + 内环 2px
    就把半径吃掉一半，剩给符文的空间每个只有 4×4 像素，只能画点和短横，
    读不出「阵」的结构。64×64 才放得下三层信息：
    外环 → 刻度/辐条带 → 内环（或中心徽记）。

构图约定（六张共用）：
    1. 外轮廓必须是大圆（允许缺口），「不对称」只体现在刻度间距、辐条长短、
       缺口角度、环心偏移上，绝不把圆本身画歪；
    2. 三层信息：外环（中亮 2px）→ 刻度带（1px 高亮）→ 内环 / 中心纹样；
    3. alpha 走 255 / 200 / 150 / 90 / 50 阶梯做辉光衰减，四周留 2px 透明边，
       防止粒子图集拼图时渗色；
    4. 底色偏亮（乘法染色友好）：游戏里粒子还会乘 rCol/gCol/bCol，
       本库这张图自己带主题色，但整体偏亮，压暗后仍可读。

绘制方式：全部在极坐标下按「距离带 ±0.5px / 角度带」求像素，
    所以任意半径的 1px 圆、弧、辐条都不会出现粗细随角度变化的问题。
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

# 画布边长（逻辑像素）。粒子贴图必须为正方形，切图集时按 64×64 整块拼。
SIZE = 64

# 圆心落在画布正中：用像素中心 (x+0.5) 参与距离计算，半径 29 时最外像素索引 61，仍留 2px 边。
CENTER = SIZE * 0.5

# 固定随机种子基数：保证每次重跑生成完全一致的像素（法阵讲究构图，不能每次抖出不同结果）。
SEED_BASE = 0x51616C

# 主题配色：deep（外圈暗底/辉光）→ mid（主环）→ pale（高亮线）→ white（芯）。
PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "arcane": {
        "deep": (52, 88, 168),
        "mid": (96, 150, 232),
        "pale": (168, 205, 248),
        "white": (240, 248, 255),
    },
    "frost": {
        "deep": (40, 96, 124),
        "mid": (86, 166, 196),
        "pale": (160, 226, 240),
        "white": (242, 253, 255),
    },
    "ember": {
        "deep": (140, 52, 24),
        "mid": (206, 96, 36),
        "pale": (248, 168, 72),
        "white": (255, 240, 200),
    },
    "verdant": {
        "deep": (36, 104, 60),
        "mid": (74, 168, 96),
        "pale": (156, 224, 150),
        "white": (238, 255, 226),
    },
    "void": {
        "deep": (60, 32, 104),
        "mid": (110, 64, 176),
        "pale": (176, 132, 232),
        "white": (240, 224, 255),
    },
    "gold": {
        "deep": (132, 92, 24),
        "mid": (206, 158, 52),
        "pale": (248, 214, 120),
        "white": (255, 250, 220),
    },
}


# ---------------------------------------------------------------------------
# 基础写入
# ---------------------------------------------------------------------------


def put(grid: dict[tuple[int, int], list[int]], x: int, y: int,
        color: tuple[int, int, int], alpha: float) -> None:
    """写入一个逻辑像素；同格取更高 alpha。

    后画的亮结构（环、刻度）因此总能盖住先画的辉光，不需要关心绘制顺序里的透明度叠乘。
    """
    if not (0 <= x < SIZE and 0 <= y < SIZE):
        return
    value = int(round(alpha))
    if value <= 0:
        return
    value = min(255, value)
    key = (x, y)
    previous = grid.get(key)
    if previous is None or value >= previous[3]:
        grid[key] = [color[0], color[1], color[2], value]


def put_soft(grid: dict[tuple[int, int], list[int]], cx: float, cy: float,
             color: tuple[int, int, int], alpha: float, radius_px: float = 1.2) -> None:
    """在浮点坐标处落一个带微晕的点（占 1~4 像素），用于星点、火星。

    radius_px 控制晕的开散范围：1.0 基本是单像素，1.6 开始能看出十字微光。
    """
    base_x, base_y = int(math.floor(cx)), int(math.floor(cy))
    put(grid, base_x, base_y, color, alpha)
    reach = int(math.ceil(radius_px))
    for offset_y in range(-reach, reach + 1):
        for offset_x in range(-reach, reach + 1):
            if offset_x == 0 and offset_y == 0:
                continue
            distance = math.hypot(offset_x, offset_y)
            if distance > radius_px:
                continue
            falloff = 1.0 - distance / (radius_px + 0.35)
            peripheral = alpha * falloff * falloff * 0.55
            if peripheral >= 12:
                put(grid, base_x + offset_x, base_y + offset_y, color, peripheral)


# ---------------------------------------------------------------------------
# 极坐标笔画
# ---------------------------------------------------------------------------


def iter_polar(cx: float, cy: float):
    """遍历全部像素并给出相对 (cx, cy) 的距离与角度（角度单位：度）。"""
    for y in range(SIZE):
        for x in range(SIZE):
            delta_x = x + 0.5 - cx
            delta_y = y + 0.5 - cy
            yield x, y, math.hypot(delta_x, delta_y), math.degrees(math.atan2(delta_y, delta_x))


def wrapped_delta_deg(angle: float, reference: float) -> float:
    """把两角之差归一化到 (-180, 180]，避免 0°/360° 接缝处断线。"""
    return (angle - reference + 180.0) % 360.0 - 180.0


def polar_stroke(grid, cx: float, cy: float, radius: float,
                 color: tuple[int, int, int], alpha: float,
                 start_deg: float = 0.0, span_deg: float = 360.0,
                 half_width_px: float = 0.55) -> None:
    """画一段 1px 圆弧：距离带半径 ±half_width_px，角度限 [start_deg, start_deg+span_deg]。

    half_width_px 默认 0.55 ≈ 1 像素；给到 0.9 会变成 2px 粗环（只在外环上偶尔用）。
    """
    full_circle = span_deg >= 359.999
    for x, y, distance, angle in iter_polar(cx, cy):
        if abs(distance - radius) > half_width_px:
            continue
        if not full_circle and not (0.0 <= wrapped_delta_deg(angle, start_deg) <= span_deg):
            continue
        put(grid, x, y, color, alpha)


def polar_halo(grid, cx: float, cy: float, radius: float, half_band_px: float,
               color: tuple[int, int, int], alpha_peak: float,
               falloff: float = 1.8, start_deg: float = 0.0, span_deg: float = 360.0) -> None:
    """柔和光环带（法阵的「发光底盘」）。

    half_band_px 决定晕的宽度（以像素计，3~4 是法阵常用的量），
    falloff 越大人越向内收，1.2 偏弥散、2.4 几乎只剩一条软边。
    """
    full_circle = span_deg >= 359.999
    for x, y, distance, angle in iter_polar(cx, cy):
        offset = abs(distance - radius)
        if offset > half_band_px:
            continue
        if not full_circle and not (0.0 <= wrapped_delta_deg(angle, start_deg) <= span_deg):
            continue
        weight = 1.0 - offset / half_band_px
        put(grid, x, y, color, alpha_peak * (weight ** falloff))


def radial_stroke(grid, cx: float, cy: float, angle_deg: float,
                  radius_inner: float, radius_outer: float,
                  color: tuple[int, int, int], alpha: float,
                  half_width_px: float = 0.5) -> None:
    """沿某个角度画一段辐条（半径 radius_inner → radius_outer）。

    线宽用「弧长换算成角度」实现：硬编码角度会让远端变粗、近端变细。
    half_width_px = 0.5 是标准 1px；0.8~1.0 用于强调主辐条。
    """
    for x, y, distance, angle in iter_polar(cx, cy):
        if not (radius_inner <= distance <= radius_outer):
            continue
        angular_half_width = math.degrees(half_width_px / max(distance, 1.0))
        if abs(wrapped_delta_deg(angle, angle_deg)) > angular_half_width:
            continue
        put(grid, x, y, color, alpha)


def radial_ticks(grid, cx: float, cy: float, angles_deg: list[float],
                 radius_inner: float, radius_outer: float,
                 color: tuple[int, int, int], alpha: float,
                 half_width_px: float = 0.45) -> None:
    """在给定角度列表上批量画放射状刻度。"""
    for angle in angles_deg:
        radial_stroke(grid, cx, cy, angle, radius_inner, radius_outer,
                      color, alpha, half_width_px)


def segment_spans(gaps: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """把「缺口列表」换算成「实心弧段列表」。

    gaps 每项是 (缺口中心角, 缺口宽度角)；返回每段 (起始角, 跨越角)。
    """
    ordered = sorted((angle % 360.0, width) for angle, width in gaps)
    spans: list[tuple[float, float]] = []
    for index, (center, width) in enumerate(ordered):
        start = (center + width * 0.5) % 360.0
        next_center, next_width = ordered[(index + 1) % len(ordered)]
        end = (next_center - next_width * 0.5) % 360.0
        spans.append((start, (end - start) % 360.0))
    return spans


def ring_with_gaps(grid, cx: float, cy: float, radius: float,
                   color: tuple[int, int, int], alpha: float,
                   gaps: list[tuple[float, float]],
                   half_width_px: float = 0.55) -> None:
    """画带若干缺口的整圆（法阵「断裂感」的主要来源）。"""
    for start, span in segment_spans(gaps):
        polar_stroke(grid, cx, cy, radius, color, alpha, start, span, half_width_px)


def dashed_ring(grid, cx: float, cy: float, radius: float,
                color: tuple[int, int, int], alpha: float,
                dash_deg: float, gap_deg: float, phase_deg: float = 0.0,
                half_width_px: float = 0.5) -> None:
    """等距虚线环；dash_deg / gap_deg 是弧长角度（半径越小时视觉上越碎）。"""
    angle = phase_deg % 360.0
    while angle < phase_deg + 360.0:
        polar_stroke(grid, cx, cy, radius, color, alpha, angle % 360.0, dash_deg, half_width_px)
        angle += dash_deg + gap_deg


# ---------------------------------------------------------------------------
# 直角坐标图形
# ---------------------------------------------------------------------------


def polyline(grid, points: list[tuple[float, float]],
             color: tuple[int, int, int], alpha: float, closed: bool = False) -> None:
    """按 0.2px 步进连接折线（顶点为像素中心坐标），保证 8 连通不断线。"""
    sequence = list(points) + ([points[0]] if closed and len(points) > 2 else [])
    for index in range(len(sequence) - 1):
        start_x, start_y = sequence[index]
        end_x, end_y = sequence[index + 1]
        steps = max(2, int(math.hypot(end_x - start_x, end_y - start_y) / 0.2))
        for step in range(steps + 1):
            weight = step / steps
            x = start_x + (end_x - start_x) * weight
            y = start_y + (end_y - start_y) * weight
            put(grid, int(round(x)), int(round(y)), color, alpha)


def regular_polygon_points(cx: float, cy: float, radius: float,
                           sides: int, start_deg: float) -> list[tuple[float, float]]:
    """正多边形顶点（角度从 start_deg 起，顺时针按屏幕坐标递增）。"""
    return [
        (
            cx + math.cos(math.radians(start_deg + 360.0 * index / sides)) * radius,
            cy + math.sin(math.radians(start_deg + 360.0 * index / sides)) * radius,
        )
        for index in range(sides)
    ]


def diamond_glyph(grid, cx: float, cy: float, half_w: float, half_h: float,
                  fill_color: tuple[int, int, int], edge_color: tuple[int, int, int],
                  alpha: float = 235) -> None:
    """小菱形符文：内部填充 + 外缘描边。

    half_w/half_h 是半宽半高（像素）。3×5 已是 64px 法阵里能放下的最小可读符文；
    小于 2×2 只会变成一个点。
    """
    for y in range(int(cy - half_h) - 1, int(cy + half_h) + 2):
        for x in range(int(cx - half_w) - 1, int(cx + half_w) + 2):
            ratio = (abs(x + 0.5 - cx) / half_w) + (abs(y + 0.5 - cy) / half_h)
            if ratio > 1.02:
                continue
            if ratio > 0.72:
                put(grid, x, y, edge_color, alpha)
            else:
                put(grid, x, y, fill_color, alpha)


def star4(grid, cx: float, cy: float, arm: int,
          ray_color: tuple[int, int, int], core_color: tuple[int, int, int],
          alpha: float = 230) -> None:
    """四角星：四向渐细光刺 + 中心小菱形，用作法阵中心徽记。"""
    for step in range(1, arm + 1):
        decay = alpha * (1.0 - 0.62 * (step - 1) / max(arm - 1, 1))
        put(grid, int(round(cx)) + step, int(round(cy)), ray_color, decay)
        put(grid, int(round(cx)) - step, int(round(cy)), ray_color, decay)
        put(grid, int(round(cx)), int(round(cy)) + step, ray_color, decay)
        put(grid, int(round(cx)), int(round(cy)) - step, ray_color, decay)
    base_x, base_y = int(round(cx)), int(round(cy))
    for offset_x, offset_y in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        put(grid, base_x + offset_x, base_y + offset_y, core_color, 255)


def to_json(name: str, grid: dict[tuple[int, int], list[int]]) -> dict:
    """导出 render_pixel_art 能直接吃的 JSON 结构。"""
    pixels = [
        {"x": x, "y": y, "rgba": rgba}
        for (x, y), rgba in sorted(grid.items())
        if rgba[3] > 0
    ]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


# ---------------------------------------------------------------------------
# 1. sigil_arcane：双环 + 刻度带 + 空心三角（通用蓝白，最百搭）
# ---------------------------------------------------------------------------


def build_sigil_arcane() -> dict:
    """学院风基础阵：外双环、24 刻度、虚线内环、中心空心三角 + 三枚菱形符文。"""
    palette = PALETTES["arcane"]
    grid: dict[tuple[int, int], list[int]] = {}
    rng = random.Random(SEED_BASE + 1)

    # 底盘辉光：让阵「亮起来」而不是贴纸感
    polar_halo(grid, CENTER, CENTER, 28.0, 3.6, palette["deep"], 70, falloff=2.2)

    # 外双环：外亮内略暗，形成一圈可读的厚度
    polar_stroke(grid, CENTER, CENTER, 28.5, palette["pale"], 235, half_width_px=0.6)
    polar_stroke(grid, CENTER, CENTER, 27.0, palette["mid"], 165, half_width_px=0.55)

    # 刻度带：整体旋转 7° 偏开四条对称轴；每 6 根里第 4 根加长（不是第 1 根，避免形成正交对称）
    for index in range(24):
        angle = index * 15.0 + 7.0
        emphasized = index % 6 == 3
        inner_radius = 21.2 if emphasized else 23.4
        outer_radius = 26.4 + rng.uniform(-0.25, 0.45)
        radial_stroke(grid, CENTER, CENTER, angle, inner_radius, outer_radius,
                      palette["white"] if emphasized else palette["pale"],
                      245 if emphasized else 170, 0.42 if emphasized else 0.38)

    # 内环：四段弧、四处缺口宽度不同（12°/18°/10°/26°）
    for start, span in ((0.0, 84.0), (96.0, 90.0), (204.0, 84.0), (298.0, 36.0)):
        polar_stroke(grid, CENTER, CENTER, 20.0, palette["mid"], 185, start, span, 0.5)

    # 对内环的 4 根短桥接辐条（角度不等距）
    for angle in (18.0, 96.0, 187.0, 301.0):
        radial_stroke(grid, CENTER, CENTER, angle, 15.5, 19.6, palette["deep"], 120, 0.4)

    # 三枚菱形符文：第三枚故意偏 11°，破坏三等分
    for index, angle in enumerate((-83.0, 37.0, 161.0)):
        offset_angle = angle + (11.0 if index == 2 else 0.0)
        center_x = CENTER + math.cos(math.radians(offset_angle)) * 13.8
        center_y = CENTER + math.sin(math.radians(offset_angle)) * 13.8
        diamond_glyph(grid, center_x, center_y, 2.6, 3.8,
                      palette["white"], palette["mid"], 235)

    # 中心：空心三角（顶点朝上，整体再转 6°）
    triangle = regular_polygon_points(CENTER, CENTER, 8.0, 3, -90.0 + 6.0)
    polyline(grid, triangle, palette["pale"], 235, closed=True)
    # 三角外侧再套一圈断续小弧，避免中心只有一根线
    dashed_ring(grid, CENTER, CENTER, 10.6, palette["deep"], 110, 7.0, 11.0, phase_deg=13.0)
    star4(grid, CENTER, CENTER, 3, palette["white"], palette["white"], 235)

    return to_json("sigil_arcane", grid)


# ---------------------------------------------------------------------------
# 2. sigil_frost：六芒星骨架（几何感最强）
# ---------------------------------------------------------------------------


def build_sigil_frost() -> dict:
    """六芒星阵：外环六处不等缺口 + 双三角交叠 + 内六边形 + 中心雪花枝。"""
    palette = PALETTES["frost"]
    grid: dict[tuple[int, int], list[int]] = {}
    rng = random.Random(SEED_BASE + 2)

    polar_halo(grid, CENTER, CENTER, 24.0, 5.0, palette["deep"], 55, falloff=2.0)

    # 外环：缺口故意不正对六芒星尖角（错开 13°），宽度 4°~9° 随机 → 天然不对称
    gaps = [(19.0, 7.0), (79.0, 5.0), (139.0, 9.0), (199.0, 4.5), (259.0, 6.5), (319.0, 8.0)]
    ring_with_gaps(grid, CENTER, CENTER, 28.5, palette["pale"], 200, gaps, 0.55)

    # 六芒星：两个半径 24 的正三角，一个朝上一个朝下
    upper_triangle = regular_polygon_points(CENTER, CENTER, 24.0, 3, -90.0)
    lower_triangle = regular_polygon_points(CENTER, CENTER, 24.0, 3, 90.0)
    polyline(grid, upper_triangle, palette["pale"], 235, closed=True)
    polyline(grid, lower_triangle, palette["mid"], 210, closed=True)

    # 交叠出的内六边形（半径 = 24 * cos30 ≈ 12.5），比内环更贴合六芒星
    inner_hexagon = regular_polygon_points(CENTER, CENTER, 12.4, 6, -60.0)
    polyline(grid, inner_hexagon, palette["white"], 215, closed=True)

    # 六根主辐条：从内六边形顶点向外伸，长度各自不同（打破完美对称）
    for index in range(6):
        angle = -90.0 + 60.0 * index
        outer_radius = 24.0 - rng.choice((0.0, 0.0, 1.6, 3.0))
        radial_stroke(grid, CENTER, CENTER, angle, 13.0, outer_radius, palette["mid"], 150, 0.4)

    # 中心雪花：六向细枝 + 每枝两根短分叉
    for index in range(6):
        angle = -90.0 + 60.0 * index
        radial_stroke(grid, CENTER, CENTER, angle, 1.0, 11.0, palette["white"], 225, 0.45)
        for branch_offset in (-26.0, 26.0):
            branch_center = CENTER + math.cos(math.radians(angle)) * 7.2
            branch_center_y = CENTER + math.sin(math.radians(angle)) * 7.2
            branch_length = 2.4
            radial_stroke(
                grid,
                branch_center,
                branch_center_y,
                angle + branch_offset,
                0.4,
                branch_length,
                palette["pale"],
                190,
                0.4,
            )

    # 六个六边中点的小菱形点缀（半径 21.5）
    for index in range(6):
        angle = -60.0 + 60.0 * index + 4.0
        center_x = CENTER + math.cos(math.radians(angle)) * 21.5
        center_y = CENTER + math.sin(math.radians(angle)) * 21.5
        diamond_glyph(grid, center_x, center_y, 1.6, 2.6, palette["pale"], palette["deep"], 210)

    star4(grid, CENTER, CENTER, 3, palette["white"], palette["white"], 240)
    return to_json("sigil_frost", grid)


# ---------------------------------------------------------------------------
# 3. sigil_ember：断裂外环 + 锯齿内框（最「炸」的一张）
# ---------------------------------------------------------------------------


def build_sigil_ember() -> dict:
    """碎裂阵：多段断环 + 17 齿锯齿轮 + 偏心菱形核心 + 外飞火星。"""
    palette = PALETTES["ember"]
    grid: dict[tuple[int, int], list[int]] = {}
    rng = random.Random(SEED_BASE + 3)

    polar_halo(grid, CENTER, CENTER, 28.2, 3.4, palette["deep"], 80, falloff=2.0)

    # 外环：6 处缺口，宽度 6°~21° 不等，读起来像被烧断
    gaps = [(22.0, 14.0), (79.0, 9.0), (131.0, 21.0), (208.0, 11.0), (262.0, 17.0), (331.0, 6.0)]
    ring_with_gaps(grid, CENTER, CENTER, 28.4, palette["pale"], 215, gaps, 0.6)
    # 缺口内侧补一段短弧残影，强化「断裂后仍有余温」
    for gap_angle, gap_width in ((131.0, 21.0), (262.0, 17.0)):
        polar_stroke(grid, CENTER, CENTER, 26.4, palette["mid"], 120,
                     gap_angle - gap_width * 0.3, gap_width * 0.6, 0.45)

    # 锯齿轮：13 个不等高齿。齿形用「梯形」而不是锯齿——64px 下 17 齿以上
    # 每个齿只有 3px 弧长，会糊成一条毛边；梯形方齿才能看出「齿轮」。
    tooth_count = 13
    tooth_heights = [rng.uniform(2.6, 4.2) for _ in range(tooth_count)]
    tooth_root_radius = 18.4
    for x, y, distance, angle in iter_polar(CENTER, CENTER):
        if distance < tooth_root_radius - 0.4 or distance > tooth_root_radius + 4.6:
            continue
        normalized = (angle % 360.0) / 360.0 * tooth_count
        tooth_index = int(normalized) % tooth_count
        tooth_position = normalized - int(normalized)
        # 前 15% 上升、中间 70% 平台、后 15% 回落
        if tooth_position < 0.15:
            profile = tooth_position / 0.15
        elif tooth_position > 0.85:
            profile = (1.0 - tooth_position) / 0.15
        else:
            profile = 1.0
        outer_radius = tooth_root_radius + tooth_heights[tooth_index] * profile
        if distance > outer_radius:
            continue
        if distance > outer_radius - 0.7:
            put(grid, x, y, palette["pale"], 210)
        else:
            put(grid, x, y, palette["mid"], 180)

    # 内圈：实线 + 更靠内的一圈虚线，制造「烧灼纹理」
    polar_stroke(grid, CENTER, CENTER, 14.0, palette["deep"], 165, half_width_px=0.5)
    dashed_ring(grid, CENTER, CENTER, 11.2, palette["mid"], 150, 9.0, 8.0, phase_deg=21.0)

    # 核心：偏上 1px 的菱形，顶部留高光面
    diamond_glyph(grid, CENTER, CENTER - 1.0, 4.4, 6.4, palette["pale"], palette["deep"], 235)
    polyline(
        grid,
        [
            (CENTER - 3.0, CENTER - 4.0),
            (CENTER, CENTER - 7.5),
            (CENTER + 3.0, CENTER - 4.0),
        ],
        palette["white"],
        225,
    )

    # 阵外火星：只放两枚，避免变成「碎屑图」
    for angle, distance in ((38.0, 30.2), (286.0, 29.6)):
        put_soft(
            grid,
            CENTER + math.cos(math.radians(angle)) * distance,
            CENTER + math.sin(math.radians(angle)) * distance,
            palette["white"],
            220,
            radius_px=1.5,
        )

    return to_json("sigil_ember", grid)


# ---------------------------------------------------------------------------
# 4. sigil_verdant：藤蔓缠绕 + 花心（最柔的一张）
# ---------------------------------------------------------------------------


def build_sigil_verdant() -> dict:
    """生发阵：正弦扰动的藤蔓环 + 7 片不等位置叶芽 + 虚线内环 + 五瓣花心。"""
    palette = PALETTES["verdant"]
    grid: dict[tuple[int, int], list[int]] = {}
    rng = random.Random(SEED_BASE + 4)

    polar_halo(grid, CENTER, CENTER, 28.0, 3.2, palette["deep"], 55, falloff=2.2)

    # 外环：两处不等缺口
    ring_with_gaps(grid, CENTER, CENTER, 28.5, palette["mid"], 185,
                   [(63.0, 9.0), (241.0, 16.0)], 0.55)

    # 藤蔓环：半径随角度做两组不同频率的正弦起伏，看起来像缠绕的枝条
    vine_amplitude = 1.7
    for x, y, distance, angle in iter_polar(CENTER, CENTER):
        if distance < 18.0 or distance > 25.0:
            continue
        angle_radians = math.radians(angle)
        vine_radius = (
            22.6
            + vine_amplitude * math.sin(5.0 * angle_radians + 0.7)
            + 0.7 * math.sin(11.0 * angle_radians + 2.1)
        )
        offset = abs(distance - vine_radius)
        if offset <= 0.55:
            put(grid, x, y, palette["pale"], 220)
        elif offset <= 1.5:
            put(grid, x, y, palette["deep"], 105)

    # 叶芽：7 片，沿藤蔓向外伸出 2~4px；硬边像素叶，不用柔光晕
    # （64px 下柔光叶会和藤蔓糊成一团，看不出是叶子）
    for angle in (12.0, 61.0, 104.0, 168.0, 219.0, 276.0, 331.0):
        angle_radians = math.radians(angle)
        vine_radius = (
            22.6
            + vine_amplitude * math.sin(5.0 * angle_radians + 0.7)
            + 0.7 * math.sin(11.0 * angle_radians + 2.1)
        )
        leaf_length = rng.choice((2, 3, 4))
        direction_x = math.cos(angle_radians)
        direction_y = math.sin(angle_radians)
        perpendicular_x, perpendicular_y = -direction_y, direction_x
        base_x = CENTER + direction_x * vine_radius
        base_y = CENTER + direction_y * vine_radius
        for step in range(1, leaf_length + 1):
            leaf_x = int(round(base_x + direction_x * step))
            leaf_y = int(round(base_y + direction_y * step))
            put(grid, leaf_x, leaf_y, palette["pale"], 220)
            # 叶片中部加宽一格，叶尖保持单像素
            if step == max(2, leaf_length - 1):
                put(grid, int(round(leaf_x + perpendicular_x)), int(round(leaf_y + perpendicular_y)),
                    palette["mid"], 200)
                put(grid, int(round(leaf_x - perpendicular_x)), int(round(leaf_y - perpendicular_y)),
                    palette["mid"], 200)
        tip_x = int(round(base_x + direction_x * (leaf_length + 1)))
        tip_y = int(round(base_y + direction_y * (leaf_length + 1)))
        put(grid, tip_x, tip_y, palette["white"], 240)

    # 内环：虚线（每 10° 实、7° 虚）
    dashed_ring(grid, CENTER, CENTER, 15.0, palette["mid"], 195, 10.0, 7.0, phase_deg=33.0)

    # 花心：5 瓣（角度不等距）+ 四角星心
    for index in range(5):
        angle = -90.0 + 72.0 * index + (6.0 if index == 4 else 0.0)
        petal_x = CENTER + math.cos(math.radians(angle)) * 4.8
        petal_y = CENTER + math.sin(math.radians(angle)) * 4.8
        diamond_glyph(grid, petal_x, petal_y, 2.2, 3.0, palette["white"], palette["mid"], 235)
    star4(grid, CENTER, CENTER, 3, palette["pale"], palette["white"], 245)

    return to_json("sigil_verdant", grid)


# ---------------------------------------------------------------------------
# 5. sigil_void：三环偏心的结构（最「不规整」的一张）
# ---------------------------------------------------------------------------


def build_sigil_void() -> dict:
    """虚空阵：三层圆环各偏 1.5px，内圈九根不等长辐条，中心留空只放三颗游点。"""
    palette = PALETTES["void"]
    grid: dict[tuple[int, int], list[int]] = {}
    rng = random.Random(SEED_BASE + 5)

    polar_halo(grid, CENTER, CENTER, 29.0, 3.0, palette["deep"], 75, falloff=2.1)

    # 外环：两处不等缺口
    ring_with_gaps(grid, CENTER, CENTER, 29.0, palette["pale"], 205,
                   [(102.0, 13.0), (249.0, 21.0)], 0.55)

    # 第二环：中心偏右上 1.5,-1.0
    second_center_x, second_center_y = CENTER + 1.5, CENTER - 1.0
    polar_stroke(grid, second_center_x, second_center_y, 23.0, palette["mid"], 215, half_width_px=0.55)
    polar_halo(grid, second_center_x, second_center_y, 23.0, 2.0, palette["deep"], 60, falloff=2.0)

    # 第三环：中心偏左下 1.5,+1.0（与第二环互为镜像，形成「咬合」错觉）
    third_center_x, third_center_y = CENTER - 1.5, CENTER + 1.0
    polar_stroke(grid, third_center_x, third_center_y, 17.0, palette["pale"], 195, half_width_px=0.5)

    # 九根不等长辐条（第三环内侧）
    for index in range(9):
        angle = index * 40.0 + 9.0
        inner_radius = 6.8 + rng.uniform(0.0, 1.4)
        outer_radius = 16.6 - rng.uniform(0.0, 1.6)
        radial_stroke(grid, third_center_x, third_center_y, angle, inner_radius, outer_radius,
                      palette["deep"], 135, 0.4)

    # 中心留空（半径 6 以内不画环），只放一个极小的内圈
    polar_stroke(grid, CENTER, CENTER, 6.2, palette["deep"], 145, half_width_px=0.5)

    # 三颗游点，角度不等距
    for angle in (-38.0, 74.0, 196.0):
        distance = 3.6
        put_soft(
            grid,
            CENTER + math.cos(math.radians(angle)) * distance,
            CENTER + math.sin(math.radians(angle)) * distance,
            palette["white"],
            240,
            radius_px=0.9,
        )

    # 环间小星点：让稀疏的区域不显得空
    for angle, distance, alpha in ((70.0, 26.2, 190), (158.0, 26.6, 165), (300.0, 26.0, 200)):
        put_soft(
            grid,
            CENTER + math.cos(math.radians(angle)) * distance,
            CENTER + math.sin(math.radians(angle)) * distance,
            palette["pale"],
            alpha,
            radius_px=1.4,
        )

    return to_json("sigil_void", grid)


# ---------------------------------------------------------------------------
# 6. sigil_gold：太阳芒 + 半环（最「仪式」的一张）
# ---------------------------------------------------------------------------


def build_sigil_gold() -> dict:
    """黄金阵：268° 主弧 + 独立弧段、黄金角排布的不等长芒线、短芒内圈、四角星心。"""
    palette = PALETTES["gold"]
    grid: dict[tuple[int, int], list[int]] = {}
    rng = random.Random(SEED_BASE + 6)

    polar_halo(grid, CENTER, CENTER, 26.0, 5.0, palette["deep"], 65, falloff=2.0)

    # 主弧：留出右侧约 92° 的大缺口，是这张图最主要的「不完整」感
    polar_stroke(grid, CENTER, CENTER, 28.5, palette["pale"], 230, -78.0, 268.0, 0.6)
    # 缺口里再放一段孤立短弧（像另一层阵的残片）
    polar_stroke(grid, CENTER, CENTER, 28.5, palette["mid"], 170, 196.0, 26.0, 0.5)

    # 芒线：黄金角（137.508°）递增，天然避开任何对称轴
    golden_angle = 137.508
    for index in range(15):
        angle = (index * golden_angle) % 360.0
        emphasized = index % 5 == 2
        inner_radius = 20.2 + rng.uniform(0.0, 1.2)
        outer_radius = 25.4 + rng.uniform(0.0, 2.6)
        radial_stroke(grid, CENTER, CENTER, angle, inner_radius, outer_radius,
                      palette["white"] if emphasized else palette["pale"],
                      235 if emphasized else 175, 0.62 if emphasized else 0.4)

    # 内环：三处小缺口
    ring_with_gaps(grid, CENTER, CENTER, 19.4, palette["mid"], 185,
                   [(41.0, 8.0), (152.0, 6.0), (287.0, 11.0)], 0.5)

    # 内圈短芒：8 根，长度不一，只到内环为止
    for index in range(8):
        angle = index * 45.0 + 11.0 + rng.uniform(-4.0, 4.0)
        radial_stroke(grid, CENTER, CENTER, angle, 12.4, 17.6 - rng.uniform(0.0, 2.0),
                      palette["mid"], 165, 0.4)

    # 中心：四角星 + 一圈极细内环
    polar_stroke(grid, CENTER, CENTER, 8.6, palette["deep"], 135, half_width_px=0.5)
    star4(grid, CENTER, CENTER, 6, palette["pale"], palette["white"], 240)

    return to_json("sigil_gold", grid)


BUILDERS = [
    build_sigil_arcane,
    build_sigil_frost,
    build_sigil_ember,
    build_sigil_verdant,
    build_sigil_void,
    build_sigil_gold,
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
        # scale=1：逻辑像素 1:1 入库，不放大
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
