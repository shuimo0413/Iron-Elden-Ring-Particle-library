#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「通用」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

与法环各系列（辉石 / 圣金 / 冰霜 …）不同，这一批不绑定任何法术，面向任意 mod 复用：

- ``base_*``      白色可染色基底：游戏内 ``setColor`` 乘色后可当任意颜色的光点 / 光环 / 星
- ``smoke_*`` / ``dust_puff``  中性灰烟、土黄尘
- ``rock_chunk_*`` / ``ground_crack``  碎石块、俯视地裂（贴地平铺用）
- ``water_*`` / ``bubble*``  水滴、水花、气泡、气泡破裂
- ``blood_*`` / ``poison_bubble``  同形状换配色
- ``lightning_*``  闪电主干、电火花
- ``explosion_0..3``  4 帧爆炸序列：闪光 → 火球 → 翻滚 → 残烟
- ``slash_arc``  白色斩击弧（可染色）
- ``heart`` / ``anger_mark`` / ``sleep_z``  情绪符号（乐谱符号见 ``gen_music_particles.py``）

所有随机都走固定种子，重复运行输出完全一致。
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Callable

from render_pixel_art import load_pixel_art, save_png

SIZE = 32
CENTER = 16.0

Grid = dict[tuple[int, int], list[int]]
Mask = set[tuple[int, int]]
Rgb = tuple[int, int, int]

WHITE: Rgb = (255, 255, 255)

# 白色基底：边缘略偏灰，乘色后仍能看出明暗层次
BASE_EDGE: Rgb = (200, 200, 205)
BASE_MID: Rgb = (232, 232, 236)

# 中性烟：整体偏亮，方便游戏内再乘色成黑烟 / 彩烟
SMOKE_TONES: list[Rgb] = [(70, 70, 76), (110, 110, 116), (150, 150, 156), (190, 190, 194), (225, 225, 228)]
# 土尘：暖褐
DUST_TONES: list[Rgb] = [(92, 74, 52), (130, 106, 76), (165, 140, 104), (196, 174, 138), (222, 204, 172)]
# 岩石：冷灰褐
ROCK_TONES: list[Rgb] = [(48, 45, 42), (78, 74, 70), (108, 103, 96), (140, 134, 125), (175, 169, 158)]

WATER_TONES: list[Rgb] = [(28, 74, 150), (55, 120, 205), (100, 170, 235), (165, 215, 250), (235, 248, 255)]
BLOOD_TONES: list[Rgb] = [(70, 0, 8), (125, 8, 18), (180, 22, 32), (225, 70, 75), (255, 170, 170)]
POISON_TONES: list[Rgb] = [(30, 70, 18), (70, 135, 35), (120, 195, 60), (180, 235, 110), (235, 255, 200)]

LIGHTNING_GLOW: Rgb = (90, 130, 255)
LIGHTNING_MID: Rgb = (160, 200, 255)

# 爆炸火：暗红 → 橙 → 黄 → 白
FIRE_TONES: list[Rgb] = [(120, 38, 18), (200, 70, 20), (245, 130, 35), (255, 200, 80), (255, 245, 190), WHITE]

HEART_TONES: list[Rgb] = [(110, 10, 30), (190, 30, 55), (230, 55, 75), (255, 110, 125), (255, 190, 195)]
ANGER_FILL: Rgb = (230, 50, 50)
ANGER_OUTLINE: Rgb = (110, 15, 15)
SYMBOL_FILL: Rgb = (240, 240, 244)
SYMBOL_OUTLINE: Rgb = (60, 62, 78)
SLEEP_FILL: Rgb = (225, 232, 255)
SLEEP_OUTLINE: Rgb = (70, 80, 125)


# ---------------------------------------------------------------------------
# 基础绘制
# ---------------------------------------------------------------------------


def clamp_alpha(alpha: float) -> int:
    return max(0, min(255, int(alpha)))


def put(grid: Grid, x: int, y: int, rgb: Rgb, alpha: float, overwrite: bool = False) -> None:
    """写入像素。默认同格取更高 alpha（叠光晕用）；``overwrite`` 时后画覆盖先画（实心图形分层用）。"""
    if not (0 <= x < SIZE and 0 <= y < SIZE):
        return
    alpha = clamp_alpha(alpha)
    if alpha <= 0:
        return
    key = (x, y)
    if overwrite or key not in grid or alpha >= grid[key][3]:
        grid[key] = [rgb[0], rgb[1], rgb[2], alpha]


def hash_noise(x: int, y: int, seed: int) -> float:
    """整数坐标 → [0, 1) 的确定性噪声，用来打散烟边缘、岩石面。"""
    value = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((value ^ (value >> 16)) & 0xFFFF) / 65536.0


def soft_disk(grid: Grid, cx: float, cy: float, radius: float, rgb: Rgb, alpha_core: float, falloff: float = 1.6) -> None:
    """柔和圆形光晕：alpha 从中心向外按 ``(1 - d/r) ** falloff`` 衰减；falloff 越大越集中。"""
    reach = int(math.ceil(radius)) + 1
    for y in range(int(cy) - reach, int(cy) + reach + 1):
        for x in range(int(cx) - reach, int(cx) + reach + 1):
            distance = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if distance > radius:
                continue
            put(grid, x, y, rgb, alpha_core * (1.0 - distance / radius) ** falloff)


def ring_band(grid: Grid, cx: float, cy: float, radius: float, half_thickness: float, rgb: Rgb, alpha_peak: float) -> None:
    """环带：距圆周越近越不透明。"""
    reach = int(math.ceil(radius + half_thickness)) + 1
    for y in range(int(cy) - reach, int(cy) + reach + 1):
        for x in range(int(cx) - reach, int(cx) + reach + 1):
            band_distance = abs(math.hypot(x + 0.5 - cx, y + 0.5 - cy) - radius)
            if band_distance > half_thickness:
                continue
            put(grid, x, y, rgb, alpha_peak * (1.0 - band_distance / half_thickness) ** 1.3)


def line_mask(points: list[tuple[float, float]], brush_size: int = 1) -> Mask:
    """折线 → 像素集合。``brush_size`` 为方形笔刷边长（像素）。"""
    mask: Mask = set()
    brush_offset = (brush_size - 1) / 2.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) * 2))
        for step in range(steps + 1):
            progress = step / steps
            px = x0 + (x1 - x0) * progress
            py = y0 + (y1 - y0) * progress
            left = int(round(px - brush_offset))
            top = int(round(py - brush_offset))
            for dy in range(brush_size):
                for dx in range(brush_size):
                    mask.add((left + dx, top + dy))
    return {(x, y) for x, y in mask if 0 <= x < SIZE and 0 <= y < SIZE}


def polygon_mask(vertices: list[tuple[float, float]]) -> Mask:
    """射线法填充多边形（以像素中心判定）。"""
    mask: Mask = set()
    count = len(vertices)
    for y in range(SIZE):
        for x in range(SIZE):
            sample_x, sample_y = x + 0.5, y + 0.5
            inside = False
            for index in range(count):
                ax, ay = vertices[index]
                bx, by = vertices[(index + 1) % count]
                if (ay > sample_y) != (by > sample_y):
                    cross_x = ax + (sample_y - ay) * (bx - ax) / (by - ay)
                    if sample_x < cross_x:
                        inside = not inside
            if inside:
                mask.add((x, y))
    return mask


def circles_depth(circles: list[tuple[float, float, float]], x: int, y: int) -> float:
    """多圆并集的「厚度」：0 在外，越靠近某圆心越接近 1。"""
    best_depth = 0.0
    for cx, cy, radius in circles:
        distance = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
        if distance < radius:
            best_depth = max(best_depth, 1.0 - distance / radius)
    return best_depth


def is_edge(mask: Mask, x: int, y: int) -> bool:
    return any((x + dx, y + dy) not in mask for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def outline_mask(grid: Grid, mask: Mask, rgb: Rgb, alpha: float) -> None:
    """在 mask 外侧描一圈 4 邻域轮廓。"""
    for x, y in mask:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (x + dx, y + dy)
            if neighbor not in mask:
                put(grid, neighbor[0], neighbor[1], rgb, alpha, overwrite=True)


def fill_mask(grid: Grid, mask: Mask, rgb: Rgb, alpha: float) -> None:
    for x, y in mask:
        put(grid, x, y, rgb, alpha, overwrite=True)


def shade_mask(
    grid: Grid,
    mask: Mask,
    tones: list[Rgb],
    alphas: list[float],
    noise_seed: int | None = None,
    noise_strength: float = 0.0,
) -> None:
    """按左上光源给实心形状上色：边缘最暗档，内部按朝光程度分档。

    ``tones`` / ``alphas`` 从暗到亮一一对应；``noise_strength`` 越大面越碎（岩石用）。
    """
    if not mask:
        return
    centroid_x = sum(x for x, _ in mask) / len(mask) + 0.5
    centroid_y = sum(y for _, y in mask) / len(mask) + 0.5
    max_radius = max(math.hypot(x + 0.5 - centroid_x, y + 0.5 - centroid_y) for x, y in mask) or 1.0
    light_x, light_y = -math.sqrt(0.5), -math.sqrt(0.5)
    for x, y in mask:
        if is_edge(mask, x, y):
            tone_index = 0
        else:
            offset_x = (x + 0.5 - centroid_x) / max_radius
            offset_y = (y + 0.5 - centroid_y) / max_radius
            facing_light = 0.5 + 0.5 * (offset_x * light_x + offset_y * light_y)
            if noise_seed is not None:
                facing_light += (hash_noise(x, y, noise_seed) - 0.5) * noise_strength
            tone_index = 1 + int(max(0.0, min(0.999, facing_light)) * (len(tones) - 1))
            tone_index = min(tone_index, len(tones) - 1)
        put(grid, x, y, tones[tone_index], alphas[tone_index], overwrite=True)


def shaded_blob(
    grid: Grid,
    circles: list[tuple[float, float, float]],
    tones: list[Rgb],
    alphas: list[float],
    light_shift: float = 0.35,
    hole_seed: int | None = None,
    hole_chance: float = 0.0,
) -> None:
    """云团 / 烟团：多圆并集，把每个圆向左上平移 ``light_shift * r`` 再算厚度作为受光度。

    ``hole_chance`` > 0 时外缘随机挖洞，表现消散。
    """
    lit_circles = [(cx - radius * light_shift, cy - radius * light_shift, radius) for cx, cy, radius in circles]
    mask: Mask = {(x, y) for y in range(SIZE) for x in range(SIZE) if circles_depth(circles, x, y) > 0}
    for x, y in mask:
        depth = circles_depth(circles, x, y)
        if hole_seed is not None and depth < 0.22 and hash_noise(x, y, hole_seed) < hole_chance:
            continue
        if is_edge(mask, x, y):
            tone_index = 0
        else:
            lit = circles_depth(lit_circles, x, y)
            tone_index = min(len(tones) - 1, 1 + int(lit * (len(tones) - 1) * 1.15))
        put(grid, x, y, tones[tone_index], alphas[tone_index], overwrite=True)


def depth_blob(
    grid: Grid,
    circles: list[tuple[float, float, float]],
    tones: list[Rgb],
    alphas: list[float],
    hole_seed: int | None = None,
    hole_chance: float = 0.0,
) -> None:
    """火球：中心最厚处取最亮档，向外逐档变暗（不分光照方向）。"""
    for y in range(SIZE):
        for x in range(SIZE):
            depth = circles_depth(circles, x, y)
            if depth <= 0:
                continue
            if hole_seed is not None and depth < 0.4 and hash_noise(x, y, hole_seed) < hole_chance:
                continue
            tone_index = min(len(tones) - 1, int(depth * len(tones) * 1.05))
            put(grid, x, y, tones[tone_index], alphas[tone_index], overwrite=True)


def to_json(name: str, grid: Grid) -> dict:
    pixels = [{"x": x, "y": y, "rgba": rgba} for (x, y), rgba in sorted(grid.items()) if rgba[3] > 0]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


# ---------------------------------------------------------------------------
# 白色可染色基底
# ---------------------------------------------------------------------------


def build_base_glow() -> dict:
    """纯白柔光球：最常用的「任意颜色光点」。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 13, BASE_EDGE, 70, falloff=2.2)
    soft_disk(grid, CENTER, CENTER, 8, BASE_MID, 150, falloff=1.6)
    soft_disk(grid, CENTER, CENTER, 3.5, WHITE, 255, falloff=1.0)
    return to_json("base_glow", grid)


def build_base_dot() -> dict:
    """实心白点：硬边圆 + 一圈软边，适合当火花 / 雨点 / 弹孔碎屑。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 6.5, BASE_EDGE, 90, falloff=1.4)
    fill_mask(grid, {(x, y) for y in range(SIZE) for x in range(SIZE)
                     if math.hypot(x + 0.5 - CENTER, y + 0.5 - CENTER) <= 3.6}, WHITE, 255)
    return to_json("base_dot", grid)


def build_base_ring() -> dict:
    """白色细环：冲击波 / 涟漪 / 范围提示，配合缩放动画使用。"""
    grid: Grid = {}
    ring_band(grid, CENTER, CENTER, 12.0, 3.0, BASE_EDGE, 90)
    ring_band(grid, CENTER, CENTER, 12.0, 1.4, WHITE, 240)
    return to_json("base_ring", grid)


def build_base_spark() -> dict:
    """白色四芒闪光：长十字 + 短斜刺。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 5, BASE_MID, 110, falloff=1.5)
    center = int(CENTER)
    for step in range(1, 13):
        arm_alpha = 255 - step * 18
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(grid, center + dx * step, center + dy * step, WHITE, arm_alpha)
    for step in range(1, 5):
        diagonal_alpha = 170 - step * 35
        for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            put(grid, center + dx * step, center + dy * step, BASE_MID, diagonal_alpha)
    put(grid, center, center, WHITE, 255)
    return to_json("base_spark", grid)


def build_base_star() -> dict:
    """白色五角星：奖励 / 暴击 / 卡通命中。"""
    grid: Grid = {}
    outer_radius, inner_radius = 12.0, 5.0
    vertices = []
    for index in range(10):
        radius = outer_radius if index % 2 == 0 else inner_radius
        angle = math.radians(-90 + index * 36)
        vertices.append((CENTER + math.cos(angle) * radius, CENTER + 1 + math.sin(angle) * radius))
    star = polygon_mask(vertices)
    fill_mask(grid, star, WHITE, 255)
    for x, y in star:
        if is_edge(star, x, y):
            put(grid, x, y, BASE_EDGE, 255, overwrite=True)
    outline_mask(grid, star, (150, 150, 158), 200)
    return to_json("base_star", grid)


# ---------------------------------------------------------------------------
# 烟 / 尘
# ---------------------------------------------------------------------------


def build_smoke_puff(frame: int) -> dict:
    """烟团 3 帧：0 浓而小 → 1 膨胀 → 2 大而稀、外缘破碎。可按年龄切帧，也可单帧随机。"""
    grid: Grid = {}
    if frame == 0:
        circles = [(16, 17, 6), (12, 19, 4.5), (20, 19, 4.5), (16, 13, 4.5)]
        alphas = [210, 220, 230, 235, 240]
        shaded_blob(grid, circles, SMOKE_TONES, alphas)
    elif frame == 1:
        circles = [(16, 17, 8), (10, 19, 6), (22, 19, 6), (14, 11, 6), (20, 12, 5)]
        alphas = [170, 185, 195, 205, 210]
        shaded_blob(grid, circles, SMOKE_TONES, alphas, hole_seed=11, hole_chance=0.12)
    else:
        circles = [(16, 17, 10), (7, 19, 6.5), (25, 18, 6.5), (12, 8, 6.5), (21, 9, 6)]
        alphas = [100, 115, 130, 140, 150]
        shaded_blob(grid, circles, SMOKE_TONES, alphas, hole_seed=29, hole_chance=0.35)
    return to_json(f"smoke_puff_{frame}", grid)


def build_smoke_wisp() -> dict:
    """细长上飘的烟丝：S 形，越往上越淡越细。用于熄灭的蜡烛 / 冒烟的伤口 / 余烬。"""
    grid: Grid = {}
    for step in range(60):
        progress = step / 59.0
        center_y = 29 - progress * 25
        center_x = CENTER + math.sin(progress * math.pi * 2.2) * 4.5 * (0.4 + progress)
        radius = 3.2 - progress * 1.8
        fade = 1.0 - progress * 0.75
        soft_disk(grid, center_x, center_y, radius + 1.5, SMOKE_TONES[1], 70 * fade, falloff=1.4)
        soft_disk(grid, center_x - 0.4, center_y, radius, SMOKE_TONES[3], 190 * fade, falloff=0.9)
    return to_json("smoke_wisp", grid)


def build_dust_puff() -> dict:
    """贴地扬起的土尘：扁宽云团 + 上方零星沙粒。落地 / 冲刺 / 重击地面用。"""
    grid: Grid = {}
    circles = [(16, 22, 7), (9, 23, 5), (23, 23, 5), (12, 18, 4.5), (20, 18, 4), (16, 15, 3.5), (4, 25, 2.8), (28, 25, 2.8)]
    alphas = [190, 205, 215, 225, 230]
    shaded_blob(grid, circles, DUST_TONES, alphas, hole_seed=7, hole_chance=0.15)
    rng = random.Random(42)
    for _ in range(9):
        speck_x = rng.randint(4, 27)
        speck_y = rng.randint(4, 12)
        put(grid, speck_x, speck_y, DUST_TONES[rng.randint(1, 3)], rng.randint(150, 230))
    return to_json("dust_puff", grid)


# ---------------------------------------------------------------------------
# 碎石 / 地裂
# ---------------------------------------------------------------------------


ROCK_SHAPES: list[list[tuple[float, float]]] = [
    [(-8, -4), (-2, -9), (6, -6), (9, 0), (5, 8), (-3, 9), (-9, 3)],
    [(-6, -3), (0, -7), (6, -2), (5, 5), (-1, 7), (-6, 4)],
    [(-4, -2), (1, -5), (5, 0), (2, 4), (-3, 4)],
]


def build_rock_chunk(index: int) -> dict:
    """碎石块 3 种大小：0 大块、1 中块、2 小块带两颗碎屑。左上受光，面上带噪点。"""
    grid: Grid = {}
    vertices = [(CENTER + vx, CENTER + vy) for vx, vy in ROCK_SHAPES[index]]
    rock = polygon_mask(vertices)
    shade_mask(grid, rock, ROCK_TONES, [255] * len(ROCK_TONES), noise_seed=100 + index, noise_strength=0.35)
    if index == 2:
        for pebble_x, pebble_y, pebble_radius in ((25, 23, 1.6), (8, 9, 1.2)):
            pebble = {(x, y) for y in range(SIZE) for x in range(SIZE)
                      if math.hypot(x + 0.5 - pebble_x, y + 0.5 - pebble_y) <= pebble_radius}
            shade_mask(grid, pebble, ROCK_TONES[:3], [255, 255, 255])
    return to_json(f"rock_chunk_{index}", grid)


def build_ground_crack() -> dict:
    """俯视地裂：中心坑 + 6 条随机游走裂缝带分叉。贴地水平渲染，重击 / 落地 / 陨石落点用。"""
    grid: Grid = {}
    rng = random.Random(2024)
    crack_core: Rgb = (35, 28, 22)
    crack_halo: Rgb = (90, 74, 58)

    def walk(start_x: float, start_y: float, angle_degrees: float, length: int, allow_branch: bool) -> None:
        position_x, position_y = start_x, start_y
        heading = math.radians(angle_degrees)
        for step in range(length):
            heading += math.radians(rng.uniform(-28, 28))
            position_x += math.cos(heading)
            position_y += math.sin(heading)
            pixel_x, pixel_y = int(position_x), int(position_y)
            taper = 1.0 - step / max(length, 1) * 0.5
            put(grid, pixel_x, pixel_y, crack_core, 240 * taper, overwrite=True)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put(grid, pixel_x + dx, pixel_y + dy, crack_halo, 100 * taper)
            if allow_branch and step > 3 and rng.random() < 0.18:
                walk(position_x, position_y, math.degrees(heading) + rng.choice((-50, 50)), length // 2, False)

    for base_angle in (10, 75, 140, 200, 260, 320):
        walk(CENTER, CENTER, base_angle + rng.uniform(-12, 12), rng.randint(10, 14), True)
    soft_disk(grid, CENTER, CENTER, 4.5, crack_halo, 140, falloff=1.2)
    soft_disk(grid, CENTER, CENTER, 2.2, crack_core, 245, falloff=0.6)
    return to_json("ground_crack", grid)


# ---------------------------------------------------------------------------
# 液体（水 / 血 / 毒共用形状）
# ---------------------------------------------------------------------------


def drop_mask() -> Mask:
    """水滴形：下半圆 + 向上收尖的锥。"""
    mask: Mask = set()
    for y in range(SIZE):
        for x in range(SIZE):
            sample_x, sample_y = x + 0.5, y + 0.5
            in_bulb = math.hypot(sample_x - CENTER, sample_y - 20) <= 6.5
            in_cone = 7 <= sample_y <= 20 and abs(sample_x - CENTER) <= 6.5 * ((sample_y - 7) / 13) ** 0.85
            if in_bulb or in_cone:
                mask.add((x, y))
    return mask


def draw_drop(grid: Grid, tones: list[Rgb]) -> None:
    drop = drop_mask()
    shade_mask(grid, drop, tones, [235, 240, 245, 250, 255])
    for x, y in ((13, 17), (13, 18), (14, 16), (12, 19)):
        put(grid, x, y, tones[-1], 255, overwrite=True)


def draw_splash(grid: Grid, tones: list[Rgb]) -> None:
    """皇冠形水花：底部扁环 + 5 根上溅水柱 + 柱顶飞珠。"""
    base_y = 25
    for y in range(SIZE):
        for x in range(SIZE):
            normalized = math.hypot((x + 0.5 - CENTER) / 11.0, (y + 0.5 - base_y) / 2.6)
            if abs(normalized - 1.0) < 0.22:
                put(grid, x, y, tones[2], 220)
            elif normalized < 0.78:
                put(grid, x, y, tones[1], 90)
    spouts = [(-9, 7, -2.0), (-5, 11, -1.0), (0, 14, 0.0), (5, 11, 1.0), (9, 7, 2.0)]
    for offset_x, height, lean in spouts:
        root_x = CENTER + offset_x
        tip_x, tip_y = root_x + lean, base_y - height
        put_column = line_mask([(root_x, base_y - 1), (tip_x, tip_y)], brush_size=2)
        for x, y in put_column:
            fraction_up = (base_y - y) / max(height, 1)
            tone = tones[3] if fraction_up > 0.5 else tones[2]
            put(grid, x, y, tone, 235, overwrite=True)
        droplet_x, droplet_y = tip_x + lean * 0.8, tip_y - 3
        soft_disk(grid, droplet_x, droplet_y, 1.8, tones[3], 255, falloff=0.4)
        put(grid, int(droplet_x), int(droplet_y), tones[4], 255)
    for droplet_x, droplet_y in ((3, 15), (29, 14), (11, 6), (22, 5)):
        put(grid, droplet_x, droplet_y, tones[3], 220)


def draw_bubble(grid: Grid, tones: list[Rgb], radius: float = 8.0) -> None:
    """气泡：半透明内芯 + 亮边 + 左上高光弧。"""
    soft_disk(grid, CENTER, CENTER, radius, tones[2], 45, falloff=0.3)
    ring_band(grid, CENTER, CENTER, radius, 1.3, tones[3], 220)
    for angle_degrees in range(200, 255, 6):
        angle = math.radians(angle_degrees)
        put(grid, int(CENTER + math.cos(angle) * (radius - 2.5)), int(CENTER + math.sin(angle) * (radius - 2.5)), tones[4], 240)
    put(grid, int(CENTER + radius * 0.35), int(CENTER + radius * 0.45), tones[4], 160)


def build_water_drop() -> dict:
    """水滴：雨 / 汗 / 溅射。"""
    grid: Grid = {}
    draw_drop(grid, WATER_TONES)
    return to_json("water_drop", grid)


def build_water_splash() -> dict:
    """水花：落水 / 水系命中。"""
    grid: Grid = {}
    draw_splash(grid, WATER_TONES)
    return to_json("water_splash", grid)


def build_bubble() -> dict:
    """水下气泡。"""
    grid: Grid = {}
    draw_bubble(grid, WATER_TONES)
    return to_json("bubble", grid)


def build_bubble_pop() -> dict:
    """气泡破裂：断开的环 + 向外飞的小水珠。接在 bubble 后面播一帧。"""
    grid: Grid = {}
    for start_degrees in (10, 100, 190, 280):
        for angle_degrees in range(start_degrees, start_degrees + 45, 3):
            angle = math.radians(angle_degrees)
            put(grid, int(CENTER + math.cos(angle) * 10), int(CENTER + math.sin(angle) * 10), WATER_TONES[3], 210)
    for index in range(8):
        angle = math.radians(index * 45 + 22)
        droplet_x = CENTER + math.cos(angle) * 13.5
        droplet_y = CENTER + math.sin(angle) * 13.5
        put(grid, int(droplet_x), int(droplet_y), WATER_TONES[4], 230)
    soft_disk(grid, CENTER, CENTER, 5, WATER_TONES[2], 40, falloff=1.2)
    return to_json("bubble_pop", grid)


def build_blood_drop() -> dict:
    """血滴：出血 / 受伤。"""
    grid: Grid = {}
    draw_drop(grid, BLOOD_TONES)
    return to_json("blood_drop", grid)


def build_blood_splash() -> dict:
    """血花：暴击 / 出血触发。"""
    grid: Grid = {}
    draw_splash(grid, BLOOD_TONES)
    return to_json("blood_splash", grid)


def build_poison_bubble() -> dict:
    """毒泡：毒沼 / 中毒状态，内含一颗小泡。"""
    grid: Grid = {}
    draw_bubble(grid, POISON_TONES)
    soft_disk(grid, 19.5, 19.5, 2.6, POISON_TONES[3], 200, falloff=0.5)
    put(grid, 19, 18, POISON_TONES[4], 255)
    return to_json("poison_bubble", grid)


# ---------------------------------------------------------------------------
# 闪电
# ---------------------------------------------------------------------------


def draw_glowing_line(grid: Grid, points: list[tuple[float, float]], glow_scale: float = 1.0) -> None:
    """三层发光线：外层蓝晕 → 中层淡蓝双像素 → 白芯。"""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(1, int(math.hypot(x1 - x0, y1 - y0)))
        for step in range(steps + 1):
            progress = step / steps
            soft_disk(grid, x0 + (x1 - x0) * progress, y0 + (y1 - y0) * progress,
                      2.8 * glow_scale, LIGHTNING_GLOW, 75, falloff=1.3)
    for x, y in line_mask(points, brush_size=2):
        put(grid, x, y, LIGHTNING_MID, 220)
    for x, y in line_mask(points, brush_size=1):
        put(grid, x, y, WHITE, 255, overwrite=True)


def build_lightning_bolt() -> dict:
    """竖直闪电主干 + 一条分叉。拉伸成长条 billboard 使用；随机水平翻转可以假装不同形状。"""
    grid: Grid = {}
    zigzag_offsets = [0, -3, 2, -2, 4, -1, 3, -2, 1]
    trunk = [(CENTER + offset, 1 + index * 3.6) for index, offset in enumerate(zigzag_offsets)]
    branch = [trunk[3], (CENTER + 3, trunk[3][1] + 3), (CENTER + 8, trunk[3][1] + 5), (CENTER + 11, trunk[3][1] + 9)]
    draw_glowing_line(grid, branch, glow_scale=0.7)
    draw_glowing_line(grid, trunk)
    return to_json("lightning_bolt", grid)


def build_lightning_spark() -> dict:
    """电火花：中心白点 + 6 条短锯齿电弧。感电 / 雷属性命中。"""
    grid: Grid = {}
    rng = random.Random(77)
    soft_disk(grid, CENTER, CENTER, 6, LIGHTNING_GLOW, 120, falloff=1.4)
    for index in range(6):
        base_angle = math.radians(index * 60 + rng.uniform(-15, 15))
        length = rng.uniform(9, 13)
        points = [(CENTER, CENTER)]
        for segment in range(1, 4):
            distance = length * segment / 3
            wobble = rng.uniform(-0.45, 0.45) if segment < 3 else 0.0
            points.append((CENTER + math.cos(base_angle + wobble) * distance,
                           CENTER + math.sin(base_angle + wobble) * distance))
        for x, y in line_mask(points, brush_size=1):
            fade = 1.0 - math.hypot(x + 0.5 - CENTER, y + 0.5 - CENTER) / (length + 2)
            put(grid, x, y, WHITE if fade > 0.5 else LIGHTNING_MID, 255 * max(fade, 0.35))
    soft_disk(grid, CENTER, CENTER, 2.5, WHITE, 255, falloff=0.6)
    return to_json("lightning_spark", grid)


# ---------------------------------------------------------------------------
# 爆炸序列
# ---------------------------------------------------------------------------


def build_explosion(frame: int) -> dict:
    """爆炸 4 帧（建议每帧 2~3 tick）：0 白闪光刺 → 1 火球 → 2 翻滚变暗 → 3 残烟夹火星。"""
    grid: Grid = {}
    if frame == 0:
        soft_disk(grid, CENTER, CENTER, 11, FIRE_TONES[3], 90, falloff=1.8)
        center = int(CENTER)
        for index in range(8):
            angle = math.radians(index * 45 + 22.5 * (index % 2))
            ray_length = 12 if index % 2 == 0 else 8
            for step in range(1, ray_length):
                put(grid, int(center + math.cos(angle) * step), int(center + math.sin(angle) * step),
                    FIRE_TONES[4] if step < ray_length / 2 else FIRE_TONES[3], 255 - step * 17)
        depth_blob(grid, [(CENTER, CENTER, 6)], FIRE_TONES[2:], [230, 245, 255, 255])
    elif frame == 1:
        circles = [(16, 16, 8.5), (10, 12, 5), (22, 11, 6), (9, 20, 4.5), (20, 22, 6.5), (15, 8, 4), (25, 17, 3.5)]
        depth_blob(grid, circles, FIRE_TONES, [200, 230, 245, 255, 255, 255])
    elif frame == 2:
        circles = [(16, 15, 11), (8, 12, 6), (24, 11, 6), (9, 22, 6.5), (23, 22, 6.5), (16, 5, 5)]
        rolling_tones = [SMOKE_TONES[0], FIRE_TONES[0], FIRE_TONES[1], FIRE_TONES[2], FIRE_TONES[3]]
        depth_blob(grid, circles, rolling_tones, [170, 210, 230, 245, 250], hole_seed=5, hole_chance=0.2)
    else:
        circles = [(16, 14, 12), (7, 11, 6.5), (25, 10, 6.5), (8, 22, 6.5), (24, 22, 6.5), (16, 4, 5.5)]
        shaded_blob(grid, circles, SMOKE_TONES[:4], [90, 110, 130, 140], hole_seed=13, hole_chance=0.4)
        rng = random.Random(9)
        for _ in range(7):
            ember_x, ember_y = rng.randint(6, 25), rng.randint(5, 26)
            put(grid, ember_x, ember_y, FIRE_TONES[rng.randint(2, 3)], 240, overwrite=True)
    return to_json(f"explosion_{frame}", grid)


# ---------------------------------------------------------------------------
# 斩击
# ---------------------------------------------------------------------------


def build_slash_arc() -> dict:
    """白色月牙斩击弧：中间最厚最亮，两端收细淡出。可染色；旋转 billboard 表现不同挥砍方向。"""
    grid: Grid = {}
    outer_cx, outer_cy, outer_radius = CENTER, 30.0, 20.0
    inner_cx, inner_cy, inner_radius = CENTER, 33.5, 20.0
    max_angle_degrees = 52.0
    for y in range(SIZE):
        for x in range(SIZE):
            sample_x, sample_y = x + 0.5, y + 0.5
            outer_distance = math.hypot(sample_x - outer_cx, sample_y - outer_cy)
            inner_distance = math.hypot(sample_x - inner_cx, sample_y - inner_cy)
            if outer_distance > outer_radius or inner_distance < inner_radius:
                continue
            angle_from_top = abs(math.degrees(math.atan2(sample_x - outer_cx, outer_cy - sample_y)))
            if angle_from_top > max_angle_degrees:
                continue
            end_fade = 1.0 - (angle_from_top / max_angle_degrees) ** 2
            near_outer_edge = outer_radius - outer_distance < 1.2
            put(grid, x, y, WHITE if near_outer_edge else BASE_MID, 255 * end_fade if near_outer_edge else 200 * end_fade)
    for y in range(SIZE):
        for x in range(SIZE):
            sample_x, sample_y = x + 0.5, y + 0.5
            band = abs(math.hypot(sample_x - outer_cx, sample_y - outer_cy) - outer_radius - 0.8)
            angle_from_top = abs(math.degrees(math.atan2(sample_x - outer_cx, outer_cy - sample_y)))
            if band < 1.5 and angle_from_top < max_angle_degrees * 0.8:
                put(grid, x, y, BASE_EDGE, 70 * (1.0 - angle_from_top / max_angle_degrees))
    return to_json("slash_arc", grid)


# ---------------------------------------------------------------------------
# 情绪符号
# ---------------------------------------------------------------------------


def build_heart() -> dict:
    """爱心：繁殖 / 治疗 / 好感。隐式心形曲线 (x²+y²-1)³ - x²y³ ≤ 0。"""
    grid: Grid = {}
    scale = 10.5
    heart: Mask = set()
    for y in range(SIZE):
        for x in range(SIZE):
            heart_x = (x + 0.5 - CENTER) / scale
            heart_y = -(y + 0.5 - CENTER) / scale + 0.125
            if (heart_x ** 2 + heart_y ** 2 - 1) ** 3 - heart_x ** 2 * heart_y ** 3 <= 0:
                heart.add((x, y))
    shade_mask(grid, heart, HEART_TONES, [255] * len(HEART_TONES))
    for x, y in ((9, 8), (10, 8), (8, 9), (8, 10), (9, 9)):
        put(grid, x, y, WHITE, 255, overwrite=True)
    return to_json("heart", grid)


def build_anger_mark() -> dict:
    """怒气符号（漫画青筋）：四段弧凸面朝中心。愤怒 / 嘲讽 / 仇恨标记。"""
    grid: Grid = {}
    anger: Mask = set()
    for sign_x, sign_y in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        corner_x = CENTER + sign_x * 11
        corner_y = CENTER + sign_y * 11
        for y in range(SIZE):
            for x in range(SIZE):
                offset_x = (x + 0.5 - CENTER) * sign_x
                offset_y = (y + 0.5 - CENTER) * sign_y
                if offset_x < 1.5 or offset_y < 1.5 or offset_x > 12 or offset_y > 12:
                    continue
                if abs(math.hypot(x + 0.5 - corner_x, y + 0.5 - corner_y) - 8.0) <= 1.3:
                    anger.add((x, y))
    fill_mask(grid, anger, ANGER_FILL, 255)
    outline_mask(grid, anger, ANGER_OUTLINE, 255)
    return to_json("anger_mark", grid)


def build_sleep_z() -> dict:
    """睡眠 Zz：一大一小两个 Z。睡眠 / 眩晕 / 催眠状态。"""
    grid: Grid = {}
    big_z = line_mask([(14, 8), (25, 8), (14, 19), (25, 19)], brush_size=2)
    small_z = line_mask([(5, 21), (11, 21), (5, 27), (11, 27)], brush_size=2)
    letters = big_z | small_z
    fill_mask(grid, letters, SLEEP_FILL, 255)
    outline_mask(grid, letters, SLEEP_OUTLINE, 255)
    return to_json("sleep_z", grid)


BUILDERS: list[Callable[[], dict]] = [
    build_base_glow,
    build_base_dot,
    build_base_ring,
    build_base_spark,
    build_base_star,
    lambda: build_smoke_puff(0),
    lambda: build_smoke_puff(1),
    lambda: build_smoke_puff(2),
    build_smoke_wisp,
    build_dust_puff,
    lambda: build_rock_chunk(0),
    lambda: build_rock_chunk(1),
    lambda: build_rock_chunk(2),
    build_ground_crack,
    build_water_drop,
    build_water_splash,
    build_bubble,
    build_bubble_pop,
    build_blood_drop,
    build_blood_splash,
    build_poison_bubble,
    build_lightning_bolt,
    build_lightning_spark,
    lambda: build_explosion(0),
    lambda: build_explosion(1),
    lambda: build_explosion(2),
    lambda: build_explosion(3),
    build_slash_arc,
    build_heart,
    build_anger_mark,
    build_sleep_z,
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

    print(f"已生成 {len(written)} 个通用粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
