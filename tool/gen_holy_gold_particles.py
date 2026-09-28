#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「神圣金光」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

提示词对应：
1) 神圣金色碎星碎片 / 棱角光晶 / 圣光粉尘 / 爆炸微粒
2) 小型神圣金光球：中心亮白、金色外圈光晕

配色：深金 → 暖金 → 亮金 → 金白 → 纯白；硬朗像素轮廓，有限配色。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

SIZE = 32

# 有限配色：深琥珀金 → 暖金 → 亮金 → 金白 → 纯白
C_DEEP = (160, 100, 30)
C_MID = (210, 150, 45)
C_GOLD = (235, 190, 70)
C_PALE = (250, 230, 150)
C_WARM = (255, 245, 200)
C_WHITE = (255, 255, 255)


def clamp_alpha(a: int) -> int:
    return max(0, min(255, int(a)))


def put(grid: dict[tuple[int, int], list[int]], x: int, y: int, rgb: tuple[int, int, int], a: int) -> None:
    """写入像素；同格取更高 alpha。"""
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


def hard_disk(
    grid: dict[tuple[int, int], list[int]],
    cx: float,
    cy: float,
    radius: float,
    rgb_core: tuple[int, int, int],
    rgb_edge: tuple[int, int, int],
    alpha_core: int = 255,
    alpha_edge: int = 200,
) -> None:
    """清晰像素边缘的圆盘：中心更亮，外圈金色。"""
    r_ceil = int(math.ceil(radius)) + 1
    ix0, iy0 = int(round(cx)), int(round(cy))
    for dy in range(-r_ceil, r_ceil + 1):
        for dx in range(-r_ceil, r_ceil + 1):
            x, y = ix0 + dx, iy0 + dy
            dist = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if dist > radius:
                continue
            blend = dist / max(radius, 1e-6)
            if blend < 0.35:
                put(grid, x, y, C_WHITE, alpha_core)
            elif blend < 0.65:
                put(grid, x, y, rgb_core, alpha_core - 20)
            elif blend < 0.88:
                put(grid, x, y, rgb_edge, alpha_edge)
            else:
                # 硬边：外圈一圈深金，保证轮廓可读
                put(grid, x, y, C_DEEP, max(120, alpha_edge - 40))


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
    if arm >= 2:
        put(grid, cx + 1, cy + 1, C_GOLD, 90)
        put(grid, cx - 1, cy - 1, C_GOLD, 90)
        put(grid, cx + 1, cy - 1, C_MID, 70)
        put(grid, cx - 1, cy + 1, C_MID, 70)


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
    """锐利多角星（填充），外缘金、中心白。"""
    rot = math.radians(rotation_deg)
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
            sector = math.pi / points
            local = abs((ang + math.pi) % (2 * sector) - sector)
            t = local / sector
            edge_r = outer_r * (1.0 - t * t) + inner_r * (t * t)
            if dist <= edge_r:
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
    """菱形棱角光晶碎片。"""
    for dy in range(-half_h, half_h + 1):
        for dx in range(-half_w - 1, half_w + 2):
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
                put(grid, cx + dx, cy + dy, C_GOLD, 180)
            else:
                put(grid, cx + dx, cy + dy, C_MID, 130)


def angular_chip(
    grid: dict[tuple[int, int], list[int]],
    cx: int,
    cy: int,
    verts: list[tuple[int, int]],
    rgb_fill: tuple[int, int, int],
    rgb_edge: tuple[int, int, int],
) -> None:
    """不规则多角碎星：用轴对齐包围盒 + 凸包近似填充。"""
    xs = [cx + vx for vx, _ in verts]
    ys = [cy + vy for _, vy in verts]
    for y in range(min(ys), max(ys) + 1):
        for x in range(min(xs), max(xs) + 1):
            # 射线法粗判多边形内
            inside = False
            n = len(verts)
            for i in range(n):
                x1, y1 = cx + verts[i][0], cy + verts[i][1]
                x2, y2 = cx + verts[(i + 1) % n][0], cy + verts[(i + 1) % n][1]
                if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / max(y2 - y1, 1e-6) + x1):
                    inside = not inside
            if not inside:
                continue
            # 靠近边缘用深金，内部亮
            min_edge = min(abs(x - cx), abs(y - cy), abs(x - xs[0]), abs(y - ys[0]))
            if min_edge <= 0:
                put(grid, x, y, rgb_edge, 200)
            else:
                put(grid, x, y, rgb_fill, 230)


def ring_halo(
    grid: dict[tuple[int, int], list[int]],
    cx: float,
    cy: float,
    radius: float,
    thickness: float,
    rgb: tuple[int, int, int],
    alpha_peak: int,
) -> None:
    """金色光环带。"""
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
    """细碎圣光粉尘：seeds = (x, y, size) size 0=单点 1=小十字 2=带微晕。"""
    for x, y, size in seeds:
        put(grid, x, y, C_WHITE if size >= 1 else C_PALE, 255 if size >= 1 else 180)
        if size >= 1:
            put(grid, x + 1, y, C_GOLD, 140)
            put(grid, x - 1, y, C_GOLD, 140)
            put(grid, x, y + 1, C_GOLD, 140)
            put(grid, x, y - 1, C_GOLD, 140)
        if size >= 2:
            soft_disk(grid, x + 0.5, y + 0.5, 2.2, C_MID, 60, falloff=1.2)


def to_json(name: str, grid: dict[tuple[int, int], list[int]]) -> dict:
    pixels = [
        {"x": x, "y": y, "rgba": rgba}
        for (x, y), rgba in sorted(grid.items())
        if rgba[3] > 0
    ]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


# ---------------------------------------------------------------------------
# 提示词1：碎星碎片 / 光晶 / 粉尘 / 爆炸微粒
# ---------------------------------------------------------------------------


def build_holy_shard() -> dict:
    """棱角光晶碎片：斜切菱形 + 柔和辉光。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 5.5, C_MID, 45, falloff=2.0)
    diamond_shard(g, 16, 16, 4, 7, tilt=1)
    put(g, 15, 11, C_WHITE, 255)
    put(g, 16, 12, C_WHITE, 230)
    put(g, 17, 18, C_PALE, 160)
    return to_json("holy_shard", g)


def build_holy_star() -> dict:
    """神圣金色碎星：六角星 + 微晕。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 10, C_DEEP, 45, falloff=2.0)
    soft_disk(g, 16, 16, 6, C_MID, 80, falloff=1.8)
    star_points(g, 16, 16, 9.5, 3.2, 6, -90, C_GOLD, C_WHITE)
    cross_spark(g, 16, 16, 2, C_WHITE, C_PALE)
    return to_json("holy_star", g)


def build_holy_spark() -> dict:
    """明亮金白色闪光十字。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 4.5, C_GOLD, 70, falloff=1.5)
    cross_spark(g, 16, 16, 3, C_WHITE, C_PALE)
    put(g, 16, 16, C_WHITE, 255)
    return to_json("holy_spark", g)


def build_holy_crystal() -> dict:
    """多片棱角光晶簇。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 7, C_DEEP, 40, falloff=2.0)
    diamond_shard(g, 16, 15, 5, 9, tilt=0)
    diamond_shard(g, 11, 18, 2, 4, tilt=-1)
    diamond_shard(g, 21, 17, 2, 3, tilt=1)
    put(g, 16, 12, C_WHITE, 255)
    put(g, 16, 13, C_WHITE, 240)
    return to_json("holy_crystal", g)


def build_holy_stardust() -> dict:
    """细碎圣光粉尘散射。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 12, C_DEEP, 25, falloff=2.4)
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
        (13, 19, 0),
        (23, 14, 0),
    ]
    stardust_scatter(g, seeds)
    return to_json("holy_stardust", g)


def build_holy_flare() -> dict:
    """圣光爆炸微粒：十字光刺 + 暖金晕。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 11, C_DEEP, 55, falloff=2.0)
    soft_disk(g, 16, 16, 7, C_GOLD, 110, falloff=1.6)
    for i in range(1, 10):
        a = 200 - i * 18
        put(g, 16 + i, 16, C_PALE if i < 5 else C_MID, a)
        put(g, 16 - i, 16, C_PALE if i < 5 else C_MID, a)
        put(g, 16, 16 + i, C_PALE if i < 5 else C_MID, a)
        put(g, 16, 16 - i, C_PALE if i < 5 else C_MID, a)
    for i in range(1, 6):
        a = 140 - i * 22
        put(g, 16 + i, 16 + i, C_GOLD, a)
        put(g, 16 - i, 16 - i, C_GOLD, a)
        put(g, 16 + i, 16 - i, C_MID, a - 20)
        put(g, 16 - i, 16 + i, C_MID, a - 20)
    put(g, 16, 16, C_WHITE, 255)
    return to_json("holy_flare", g)


def build_holy_chip() -> dict:
    """不规则碎星碎片：硬朗棱角，适合爆炸飞散。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 4.5, C_MID, 40, falloff=2.0)
    # 主碎片（尖锐多边形）
    verts = [(-3, -5), (2, -4), (4, 1), (1, 5), (-4, 3), (-5, -1)]
    angular_chip(g, 16, 16, verts, C_PALE, C_DEEP)
    # 高光边
    put(g, 14, 12, C_WHITE, 255)
    put(g, 15, 13, C_WHITE, 220)
    put(g, 17, 14, C_WARM, 180)
    # 旁侧小角片
    diamond_shard(g, 21, 20, 2, 3, tilt=1)
    put(g, 10, 19, C_GOLD, 160)
    put(g, 11, 20, C_MID, 120)
    return to_json("holy_chip", g)


def build_holy_sparkle() -> dict:
    """微弱金白闪烁点。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 3.5, C_GOLD, 55, falloff=1.4)
    put(g, 16, 16, C_WHITE, 255)
    put(g, 15, 16, C_WARM, 160)
    put(g, 17, 16, C_WARM, 160)
    put(g, 16, 15, C_WARM, 160)
    put(g, 16, 17, C_WARM, 160)
    return to_json("holy_sparkle", g)


# ---------------------------------------------------------------------------
# 提示词2：小型神圣金光球
# ---------------------------------------------------------------------------


def build_holy_orb() -> dict:
    """小型神圣金光球：中心亮白，金色外圈，清晰像素边缘。"""
    g: dict[tuple[int, int], list[int]] = {}
    # 外层柔和金色光晕（投射魔法感）
    soft_disk(g, 16, 16, 9.5, C_DEEP, 50, falloff=2.2)
    soft_disk(g, 16, 16, 7.0, C_MID, 90, falloff=1.8)
    # 硬边光核球
    hard_disk(g, 16, 16, 5.2, C_PALE, C_GOLD, alpha_core=255, alpha_edge=220)
    soft_disk(g, 16, 16, 2.4, C_WHITE, 240, falloff=1.1)
    put(g, 16, 16, C_WHITE, 255)
    put(g, 15, 15, C_WARM, 180)  # 左上微高光
    return to_json("holy_orb", g)


def build_holy_glow() -> dict:
    """更大一档的暖金辉光球（可做拖尾/冲击芯）。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 14, C_DEEP, 50, falloff=2.2)
    soft_disk(g, 16, 16, 9, C_MID, 95, falloff=1.8)
    soft_disk(g, 16, 16, 5.5, C_GOLD, 150, falloff=1.4)
    soft_disk(g, 16, 16, 2.5, C_WHITE, 220, falloff=1.1)
    return to_json("holy_glow", g)


def build_holy_halo() -> dict:
    """金色圣环：外环 + 中心微光。"""
    g: dict[tuple[int, int], list[int]] = {}
    ring_halo(g, 16, 16, 11.0, 2.8, C_DEEP, 85)
    ring_halo(g, 16, 16, 11.0, 1.6, C_GOLD, 155)
    ring_halo(g, 16, 16, 11.0, 0.9, C_PALE, 200)
    soft_disk(g, 16, 16, 3.5, C_MID, 70, falloff=1.6)
    put(g, 16, 16, C_WHITE, 180)
    for ang_deg in (20, 95, 160, 230, 300):
        rad = math.radians(ang_deg)
        x = int(round(16 + math.cos(rad) * 11))
        y = int(round(16 + math.sin(rad) * 11))
        put(g, x, y, C_WHITE, 220)
    return to_json("holy_halo", g)


def build_holy_mote(index: int) -> dict:
    """漂浮圣光微粒：0 最小、1 小十字、2 带金晕小球。"""
    g: dict[tuple[int, int], list[int]] = {}
    if index == 0:
        put(g, 16, 16, C_PALE, 220)
        put(g, 15, 16, C_GOLD, 80)
        put(g, 17, 16, C_GOLD, 80)
        put(g, 16, 15, C_GOLD, 80)
        put(g, 16, 17, C_GOLD, 80)
    elif index == 1:
        soft_disk(g, 16, 16, 3.2, C_MID, 70, falloff=1.5)
        cross_spark(g, 16, 16, 2, C_WHITE, C_GOLD)
    else:
        soft_disk(g, 16, 16, 5.0, C_DEEP, 50, falloff=1.8)
        hard_disk(g, 16, 16, 2.8, C_PALE, C_GOLD, alpha_core=255, alpha_edge=200)
        soft_disk(g, 16, 16, 1.6, C_WHITE, 220, falloff=1.1)
        put(g, 16, 16, C_WHITE, 255)
    return to_json(f"holy_mote_{index}", g)


BUILDERS = [
    # 提示词1
    build_holy_shard,
    build_holy_star,
    build_holy_spark,
    build_holy_crystal,
    build_holy_stardust,
    build_holy_flare,
    build_holy_chip,
    build_holy_sparkle,
    # 提示词2
    build_holy_orb,
    build_holy_glow,
    build_holy_halo,
    lambda: build_holy_mote(0),
    lambda: build_holy_mote(1),
    lambda: build_holy_mote(2),
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

    print(f"已生成 {len(written)} 个神圣金光粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
