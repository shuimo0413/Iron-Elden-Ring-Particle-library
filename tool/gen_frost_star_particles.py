#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「冰霜星辰」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

配色：淡冰蓝 / 浅青微光 / 冷白闪烁；造型：星屑、冰晶、雪花、光环、微粒。
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

SIZE = 32
CX = 15.5  # 画布几何中心（像素格中心偏置，便于对称）
CY = 15.5

# 有限配色：深冰蓝 → 浅青 → 冷白
C_DEEP = (70, 150, 185)
C_MID = (120, 195, 220)
C_CYAN = (155, 225, 235)
C_PALE = (195, 240, 248)
C_COLD = (230, 248, 255)
C_WHITE = (255, 255, 255)


def clamp_alpha(a: int) -> int:
    return max(0, min(255, int(a)))


def put(grid: dict[tuple[int, int], list[int]], x: int, y: int, rgb: tuple[int, int, int], a: int) -> None:
    """写入像素；同格取更高 alpha，色按新 alpha 加权偏向更亮的一侧。"""
    if not (0 <= x < SIZE and 0 <= y < SIZE):
        return
    a = clamp_alpha(a)
    if a <= 0:
        return
    key = (x, y)
    if key not in grid or a >= grid[key][3]:
        grid[key] = [rgb[0], rgb[1], rgb[2], a]


def soft_disk(
    grid: dict[tuple[int, int], list[int]],
    cx: float,
    cy: float,
    radius: float,
    rgb: tuple[int, int, int],
    alpha_core: int,
    falloff: float = 1.6,
) -> None:
    """柔和圆形光晕：边缘 alpha 按距离衰减。"""
    r_ceil = int(math.ceil(radius)) + 1
    ix0, iy0 = int(cx), int(cy)
    for dy in range(-r_ceil, r_ceil + 1):
        for dx in range(-r_ceil, r_ceil + 1):
            x, y = ix0 + dx, iy0 + dy
            dist = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if dist > radius:
                continue
            t = 1.0 - dist / max(radius, 1e-6)
            a = int(alpha_core * (t ** falloff))
            put(grid, x, y, rgb, a)


def cross_spark(
    grid: dict[tuple[int, int], list[int]],
    cx: int,
    cy: int,
    arm: int,
    rgb_core: tuple[int, int, int],
    rgb_arm: tuple[int, int, int],
) -> None:
    """锐利十字微闪。"""
    put(grid, cx, cy, rgb_core, 255)
    for i in range(1, arm + 1):
        a = 220 - i * 45
        put(grid, cx + i, cy, rgb_arm, a)
        put(grid, cx - i, cy, rgb_arm, a)
        put(grid, cx, cy + i, rgb_arm, a)
        put(grid, cx, cy - i, rgb_arm, a)
    # 对角弱星屑
    if arm >= 2:
        put(grid, cx + 1, cy + 1, C_CYAN, 90)
        put(grid, cx - 1, cy - 1, C_CYAN, 90)
        put(grid, cx + 1, cy - 1, C_CYAN, 70)
        put(grid, cx - 1, cy + 1, C_CYAN, 70)


def star_points(
    grid: dict[tuple[int, int], list[int]],
    cx: float,
    cy: float,
    outer_r: float,
    inner_r: float,
    points: int,
    rotation_deg: float,
    rgb_edge: tuple[int, int, int],
    rgb_core: tuple[int, int, int],
) -> None:
    """锐利多角星（填充），外缘冰蓝、中心冷白。"""
    rot = math.radians(rotation_deg)
    # 扫描包围盒内像素，用角向内外半径判定是否在星形内
    r_max = int(math.ceil(outer_r)) + 1
    ix0, iy0 = int(round(cx)), int(round(cy))
    for dy in range(-r_max, r_max + 1):
        for dx in range(-r_max, r_max + 1):
            x, y = ix0 + dx, iy0 + dy
            px = x + 0.5 - cx
            py = y + 0.5 - cy
            dist = math.hypot(px, py)
            if dist < 0.01:
                put(grid, x, y, rgb_core, 255)
                continue
            ang = math.atan2(py, px) - rot
            # 映射到 [0, pi/points]
            sector = math.pi / points
            local = abs((ang + math.pi) % (2 * sector) - sector)
            # 星形半径：在尖端 outer，在凹处 inner
            t = local / sector  # 0=尖，1=凹
            edge_r = outer_r * (1.0 - t) + inner_r * t
            # 稍锐：尖端更尖
            edge_r = outer_r * (1.0 - t * t) + inner_r * (t * t)
            if dist <= edge_r:
                # 中心更白，边缘更青
                blend = dist / max(edge_r, 1e-6)
                if blend < 0.35:
                    rgb = rgb_core
                    a = 255
                elif blend < 0.7:
                    rgb = C_PALE
                    a = 230
                else:
                    rgb = rgb_edge
                    a = 200 if dist < edge_r - 0.4 else 140
                put(grid, x, y, rgb, a)


def diamond_shard(
    grid: dict[tuple[int, int], list[int]],
    cx: int,
    cy: int,
    half_w: int,
    half_h: int,
    tilt: int = 0,
) -> None:
    """菱形冰晶碎片；tilt=0 正菱，tilt=±1 斜切。"""
    for dy in range(-half_h, half_h + 1):
        for dx in range(-half_w - 1, half_w + 2):
            # 菱形：|dx|/w + |dy|/h <= 1
            nx = abs(dx - tilt * (dy // 2)) / max(half_w, 1)
            ny = abs(dy) / max(half_h, 1)
            if nx + ny > 1.05:
                continue
            edge = nx + ny
            if edge < 0.25:
                put(grid, cx + dx, cy + dy, C_WHITE, 250)
            elif edge < 0.55:
                put(grid, cx + dx, cy + dy, C_PALE, 220)
            elif edge < 0.85:
                put(grid, cx + dx, cy + dy, C_CYAN, 180)
            else:
                put(grid, cx + dx, cy + dy, C_MID, 120)


def snowflake(
    grid: dict[tuple[int, int], list[int]],
    cx: int,
    cy: int,
    arm_len: int,
) -> None:
    """六向星尘雪花（像素锐边）。"""
    dirs = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (1, 1),
        (-1, -1),
        (1, -1),
        (-1, 1),
    ]
    # 主臂：正交 + 对角（近似六向）
    main = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]
    put(grid, cx, cy, C_WHITE, 255)
    for dx, dy in main:
        for i in range(1, arm_len + 1):
            a = 240 - i * 28
            put(grid, cx + dx * i, cy + dy * i, C_PALE if i < arm_len else C_CYAN, a)
            # 小分叉
            if i == arm_len // 2 + 1 and arm_len >= 4:
                px, py = -dy, dx  # 垂直方向
                put(grid, cx + dx * i + px, cy + dy * i + py, C_CYAN, 150)
                put(grid, cx + dx * i - px, cy + dy * i - py, C_CYAN, 150)
    # 对角弱臂
    for dx, dy in [(1, -1), (-1, 1)]:
        for i in range(1, max(2, arm_len - 1)):
            put(grid, cx + dx * i, cy + dy * i, C_MID, 110 - i * 20)


def ring_halo(
    grid: dict[tuple[int, int], list[int]],
    cx: float,
    cy: float,
    radius: float,
    thickness: float,
    rgb: tuple[int, int, int],
    alpha_peak: int,
) -> None:
    """寒霜光环：环形带。"""
    r_ceil = int(math.ceil(radius + thickness)) + 1
    ix0, iy0 = int(cx), int(cy)
    for dy in range(-r_ceil, r_ceil + 1):
        for dx in range(-r_ceil, r_ceil + 1):
            x, y = ix0 + dx, iy0 + dy
            dist = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            band = abs(dist - radius)
            if band > thickness:
                continue
            t = 1.0 - band / thickness
            a = int(alpha_peak * (t ** 1.4))
            put(grid, x, y, rgb, a)


def stardust_scatter(
    grid: dict[tuple[int, int], list[int]],
    seeds: list[tuple[int, int, int]],
) -> None:
    """细碎星屑：seeds = (x, y, size) size 0=单点 1=小十字。"""
    for x, y, size in seeds:
        put(grid, x, y, C_WHITE if size >= 1 else C_PALE, 255 if size >= 1 else 180)
        if size >= 1:
            put(grid, x + 1, y, C_CYAN, 140)
            put(grid, x - 1, y, C_CYAN, 140)
            put(grid, x, y + 1, C_CYAN, 140)
            put(grid, x, y - 1, C_CYAN, 140)
        if size >= 2:
            soft_disk(grid, x + 0.5, y + 0.5, 2.2, C_MID, 60, falloff=1.2)


def to_json(name: str, grid: dict[tuple[int, int], list[int]]) -> dict:
    pixels = [
        {"x": x, "y": y, "rgba": rgba}
        for (x, y), rgba in sorted(grid.items())
        if rgba[3] > 0
    ]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


def build_frost_star() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 10, C_DEEP, 50, falloff=2.0)
    soft_disk(g, 16, 16, 6, C_MID, 90, falloff=1.8)
    star_points(g, 16, 16, 9.5, 3.2, 6, -90, C_CYAN, C_WHITE)
    cross_spark(g, 16, 16, 2, C_WHITE, C_PALE)
    return to_json("frost_star", g)


def build_frost_spark() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 4.5, C_CYAN, 70, falloff=1.5)
    cross_spark(g, 16, 16, 3, C_WHITE, C_PALE)
    put(g, 16, 16, C_WHITE, 255)
    return to_json("frost_spark", g)


def build_frost_glow() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 14, C_DEEP, 55, falloff=2.2)
    soft_disk(g, 16, 16, 9, C_MID, 100, falloff=1.8)
    soft_disk(g, 16, 16, 5, C_CYAN, 160, falloff=1.4)
    soft_disk(g, 16, 16, 2.2, C_WHITE, 220, falloff=1.1)
    return to_json("frost_glow", g)


def build_frost_halo() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    ring_halo(g, 16, 16, 11.0, 2.8, C_DEEP, 90)
    ring_halo(g, 16, 16, 11.0, 1.6, C_CYAN, 160)
    ring_halo(g, 16, 16, 11.0, 0.9, C_PALE, 200)
    soft_disk(g, 16, 16, 3.5, C_MID, 70, falloff=1.6)
    put(g, 16, 16, C_WHITE, 180)
    # 环上微闪星屑
    for ang_deg in (20, 95, 160, 230, 300):
        rad = math.radians(ang_deg)
        x = int(round(16 + math.cos(rad) * 11))
        y = int(round(16 + math.sin(rad) * 11))
        put(g, x, y, C_WHITE, 220)
    return to_json("frost_halo", g)


def build_frost_shard() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 5, C_MID, 40, falloff=2.0)
    diamond_shard(g, 16, 16, 4, 7, tilt=1)
    # 高光边
    put(g, 15, 11, C_WHITE, 255)
    put(g, 16, 12, C_WHITE, 230)
    put(g, 17, 18, C_PALE, 160)
    return to_json("frost_shard", g)


def build_frost_crystal() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 7, C_DEEP, 45, falloff=2.0)
    # 主晶 + 两侧小碎片
    diamond_shard(g, 16, 15, 5, 9, tilt=0)
    diamond_shard(g, 11, 18, 2, 4, tilt=-1)
    diamond_shard(g, 21, 17, 2, 3, tilt=1)
    put(g, 16, 12, C_WHITE, 255)
    put(g, 16, 13, C_WHITE, 240)
    return to_json("frost_crystal", g)


def build_frost_snowflake() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 8, C_DEEP, 40, falloff=2.2)
    soft_disk(g, 16, 16, 4, C_CYAN, 80, falloff=1.6)
    snowflake(g, 16, 16, 7)
    return to_json("frost_snowflake", g)


def build_frost_stardust() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 12, C_DEEP, 28, falloff=2.4)
    seeds = [
        (16, 16, 2),
        (10, 12, 1),
        (22, 11, 1),
        (12, 21, 1),
        (21, 20, 0),
        (8, 17, 0),
        (24, 16, 0),
        (15, 9, 0),
        (18, 24, 1),
        (14, 14, 0),
        (19, 15, 0),
        (11, 15, 0),
        (25, 21, 0),
        (7, 10, 0),
        (20, 8, 0),
    ]
    stardust_scatter(g, seeds)
    return to_json("frost_stardust", g)


def build_frost_mist() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    # 不规则寒雾团：多个偏移软盘叠加
    blobs = [
        (14, 15, 9, C_DEEP, 70),
        (18, 16, 8, C_MID, 75),
        (16, 18, 7, C_CYAN, 65),
        (13, 18, 5, C_MID, 55),
        (19, 13, 5, C_DEEP, 50),
        (16, 14, 3.5, C_PALE, 90),
    ]
    for bx, by, r, rgb, a in blobs:
        soft_disk(g, bx, by, r, rgb, a, falloff=1.9)
    # 内部细碎星屑
    for x, y in ((12, 14), (18, 17), (15, 12), (20, 15), (14, 19)):
        put(g, x, y, C_WHITE, 120)
    return to_json("frost_mist", g)


def build_frost_flare() -> dict:
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 11, C_DEEP, 60, falloff=2.0)
    soft_disk(g, 16, 16, 7, C_CYAN, 120, falloff=1.6)
    # 十字光刺
    for i in range(1, 10):
        a = 200 - i * 18
        put(g, 16 + i, 16, C_PALE if i < 5 else C_MID, a)
        put(g, 16 - i, 16, C_PALE if i < 5 else C_MID, a)
        put(g, 16, 16 + i, C_PALE if i < 5 else C_MID, a)
        put(g, 16, 16 - i, C_PALE if i < 5 else C_MID, a)
    for i in range(1, 6):
        a = 140 - i * 22
        put(g, 16 + i, 16 + i, C_CYAN, a)
        put(g, 16 - i, 16 - i, C_CYAN, a)
        put(g, 16 + i, 16 - i, C_MID, a - 20)
        put(g, 16 - i, 16 + i, C_MID, a - 20)
    put(g, 16, 16, C_WHITE, 255)
    return to_json("frost_flare", g)


def build_frost_mote(index: int) -> dict:
    """漂浮魔法微粒：0 最小单点，1 小十字，2 带微晕。"""
    g: dict[tuple[int, int], list[int]] = {}
    if index == 0:
        put(g, 16, 16, C_PALE, 220)
        put(g, 15, 16, C_CYAN, 80)
        put(g, 17, 16, C_CYAN, 80)
        put(g, 16, 15, C_CYAN, 80)
        put(g, 16, 17, C_CYAN, 80)
    elif index == 1:
        soft_disk(g, 16, 16, 3.2, C_MID, 70, falloff=1.5)
        cross_spark(g, 16, 16, 2, C_WHITE, C_CYAN)
    else:
        soft_disk(g, 16, 16, 5, C_DEEP, 55, falloff=1.8)
        soft_disk(g, 16, 16, 2.5, C_CYAN, 120, falloff=1.3)
        cross_spark(g, 16, 16, 2, C_WHITE, C_PALE)
        put(g, 14, 14, C_PALE, 100)
        put(g, 18, 17, C_CYAN, 90)
    return to_json(f"frost_mote_{index}", g)


def build_frost_sparkle() -> dict:
    """微弱冷白闪烁：极小高亮点 + 极淡晕。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 3.5, C_CYAN, 55, falloff=1.4)
    put(g, 16, 16, C_WHITE, 255)
    put(g, 15, 16, C_COLD, 160)
    put(g, 17, 16, C_COLD, 160)
    put(g, 16, 15, C_COLD, 160)
    put(g, 16, 17, C_COLD, 160)
    return to_json("frost_sparkle", g)


def build_frost_aura() -> dict:
    """寒霜光环粒子：外环 + 内星屑。"""
    g: dict[tuple[int, int], list[int]] = {}
    ring_halo(g, 16, 16, 12.5, 3.2, C_DEEP, 70)
    ring_halo(g, 16, 16, 12.5, 1.8, C_MID, 120)
    ring_halo(g, 16, 16, 9.0, 1.2, C_CYAN, 100)
    soft_disk(g, 16, 16, 4, C_PALE, 80, falloff=1.5)
    snowflake(g, 16, 16, 3)
    return to_json("frost_aura", g)


BUILDERS = [
    build_frost_star,
    build_frost_spark,
    build_frost_glow,
    build_frost_halo,
    build_frost_shard,
    build_frost_crystal,
    build_frost_snowflake,
    build_frost_stardust,
    build_frost_mist,
    build_frost_flare,
    build_frost_sparkle,
    build_frost_aura,
    lambda: build_frost_mote(0),
    lambda: build_frost_mote(1),
    lambda: build_frost_mote(2),
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

    print(f"已生成 {len(written)} 个冰霜星辰粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
