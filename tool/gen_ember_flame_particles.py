#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「余烬 / 火焰碎片」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

提示词对应：
1. 漂浮余烬：暗红余火、橙红微光、细小炭屑、微弱火光
2. 火焰碎片：不规则火屑、亮橙红、灼热点、灰烬微粒、硬朗轮廓

配色有限：炭黑红 → 暗红 → 橙红 → 亮橙 → 暖黄白。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

SIZE = 32

# 有限配色：炭屑 → 余火 → 焰心
C_CHAR = (55, 18, 12)       # 近黑炭屑
C_DEEP = (110, 28, 16)      # 暗红余火
C_EMBER = (168, 48, 22)     # 燃着的炭边
C_ORANGE = (220, 88, 28)    # 橙红火光
C_BRIGHT = (255, 140, 45)   # 亮橙
C_HOT = (255, 200, 90)      # 灼热暖黄
C_CORE = (255, 245, 200)    # 焰心近白
C_ASH = (90, 72, 62)        # 冷灰烬
C_ASH_PALE = (140, 120, 105)


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


def hard_blob(
    grid: dict[tuple[int, int], list[int]],
    cells: list[tuple[int, int, tuple[int, int, int], int]],
) -> None:
    """硬朗像素块：直接按格写入，不做羽化。"""
    for x, y, rgb, a in cells:
        put(grid, x, y, rgb, a)


def to_json(name: str, grid: dict[tuple[int, int], list[int]]) -> dict:
    pixels = [
        {"x": x, "y": y, "rgba": rgba}
        for (x, y), rgba in sorted(grid.items())
        if rgba[3] > 0
    ]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


# ---------------------------------------------------------------------------
# 提示词 1：漂浮余烬
# ---------------------------------------------------------------------------

def build_ember_mote(index: int) -> dict:
    """漂浮余烬微粒：0 单点炭火，1 微十字，2 带淡橙晕。"""
    g: dict[tuple[int, int], list[int]] = {}
    if index == 0:
        put(g, 16, 16, C_BRIGHT, 230)
        put(g, 15, 16, C_EMBER, 90)
        put(g, 17, 16, C_EMBER, 90)
        put(g, 16, 15, C_EMBER, 90)
        put(g, 16, 17, C_DEEP, 70)
    elif index == 1:
        soft_disk(g, 16, 16, 2.8, C_EMBER, 55, falloff=1.4)
        put(g, 16, 16, C_HOT, 255)
        put(g, 15, 16, C_ORANGE, 180)
        put(g, 17, 16, C_ORANGE, 180)
        put(g, 16, 15, C_ORANGE, 160)
        put(g, 16, 17, C_DEEP, 140)
        put(g, 16, 18, C_CHAR, 80)
    else:
        soft_disk(g, 16, 16, 4.5, C_DEEP, 50, falloff=1.8)
        soft_disk(g, 16, 16, 2.4, C_ORANGE, 110, falloff=1.3)
        put(g, 16, 16, C_CORE, 255)
        put(g, 15, 16, C_HOT, 200)
        put(g, 17, 16, C_HOT, 200)
        put(g, 16, 15, C_BRIGHT, 190)
        put(g, 16, 17, C_ORANGE, 170)
        put(g, 14, 17, C_EMBER, 90)
        put(g, 18, 15, C_EMBER, 80)
    return to_json(f"ember_mote_{index}", g)


def build_ember_cinder() -> dict:
    """细小燃烧炭屑：暗硬轮廓 + 一边燃着的橙边。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16.5, 16.5, 3.5, C_EMBER, 40, falloff=1.8)
    # 不规则炭块（硬边）
    hard_blob(g, [
        (15, 15, C_CHAR, 220),
        (16, 15, C_DEEP, 240),
        (17, 15, C_CHAR, 200),
        (14, 16, C_CHAR, 180),
        (15, 16, C_DEEP, 255),
        (16, 16, C_EMBER, 255),
        (17, 16, C_ORANGE, 230),
        (18, 16, C_BRIGHT, 160),
        (15, 17, C_CHAR, 210),
        (16, 17, C_DEEP, 240),
        (17, 17, C_EMBER, 200),
        (16, 18, C_CHAR, 160),
        (17, 18, C_DEEP, 120),
        # 上方微弱火光
        (17, 14, C_HOT, 140),
        (18, 15, C_ORANGE, 110),
    ])
    return to_json("ember_cinder", g)


def build_ember_glow() -> dict:
    """微弱余火光晕：外暗红、内橙、心暖黄。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 12, C_DEEP, 45, falloff=2.2)
    soft_disk(g, 16, 16, 8, C_EMBER, 80, falloff=1.9)
    soft_disk(g, 16, 16, 5, C_ORANGE, 140, falloff=1.5)
    soft_disk(g, 16, 16, 2.4, C_HOT, 210, falloff=1.2)
    put(g, 16, 16, C_CORE, 255)
    return to_json("ember_glow", g)


def build_ember_spark() -> dict:
    """余火微闪：十字橙火花。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 4.0, C_EMBER, 55, falloff=1.5)
    put(g, 16, 16, C_CORE, 255)
    for i in range(1, 4):
        a = 220 - i * 50
        rgb = C_HOT if i == 1 else (C_BRIGHT if i == 2 else C_ORANGE)
        put(g, 16 + i, 16, rgb, a)
        put(g, 16 - i, 16, rgb, a)
        put(g, 16, 16 - i, rgb, a)
        put(g, 16, 16 + i, C_EMBER if i == 3 else rgb, a - 20)
    put(g, 15, 15, C_ORANGE, 90)
    put(g, 17, 15, C_ORANGE, 90)
    put(g, 15, 17, C_DEEP, 70)
    put(g, 17, 17, C_DEEP, 70)
    return to_json("ember_spark", g)


def build_ember_wisp() -> dict:
    """向上飘的细余火丝：底部炭、顶部淡焰。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 18, 3.5, C_DEEP, 45, falloff=1.7)
    # 竖直飘带（略偏）
    column = [
        (16, 22, C_CHAR, 140),
        (16, 21, C_DEEP, 200),
        (16, 20, C_EMBER, 230),
        (16, 19, C_ORANGE, 240),
        (16, 18, C_BRIGHT, 255),
        (16, 17, C_HOT, 240),
        (16, 16, C_CORE, 220),
        (16, 15, C_HOT, 160),
        (16, 14, C_BRIGHT, 100),
        (17, 19, C_EMBER, 120),
        (15, 18, C_ORANGE, 110),
        (17, 16, C_ORANGE, 90),
        (15, 15, C_EMBER, 70),
        (17, 14, C_DEEP, 50),
        (16, 13, C_ORANGE, 55),
    ]
    hard_blob(g, column)
    return to_json("ember_wisp", g)


# ---------------------------------------------------------------------------
# 提示词 2：燃烧火焰碎片 / 爆炸微粒
# ---------------------------------------------------------------------------

def build_flame_shard() -> dict:
    """不规则火屑：硬朗锯齿轮廓，亮橙心、暗红边。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 5.5, C_EMBER, 45, falloff=2.0)
    # 斜向碎片外形
    hard_blob(g, [
        (14, 12, C_ORANGE, 180),
        (15, 12, C_BRIGHT, 220),
        (16, 12, C_HOT, 200),
        (13, 13, C_EMBER, 160),
        (14, 13, C_ORANGE, 230),
        (15, 13, C_HOT, 255),
        (16, 13, C_CORE, 255),
        (17, 13, C_BRIGHT, 210),
        (13, 14, C_DEEP, 180),
        (14, 14, C_ORANGE, 240),
        (15, 14, C_CORE, 255),
        (16, 14, C_HOT, 255),
        (17, 14, C_BRIGHT, 230),
        (18, 14, C_ORANGE, 150),
        (14, 15, C_EMBER, 200),
        (15, 15, C_BRIGHT, 250),
        (16, 15, C_HOT, 255),
        (17, 15, C_ORANGE, 220),
        (18, 15, C_EMBER, 140),
        (15, 16, C_ORANGE, 210),
        (16, 16, C_BRIGHT, 240),
        (17, 16, C_EMBER, 180),
        (18, 16, C_DEEP, 120),
        (16, 17, C_ORANGE, 170),
        (17, 17, C_DEEP, 140),
        (18, 17, C_CHAR, 100),
        (17, 18, C_CHAR, 90),
        (19, 15, C_DEEP, 80),
        (15, 11, C_HOT, 100),
        (17, 12, C_ORANGE, 110),
    ])
    return to_json("flame_shard", g)


def build_flame_fragment() -> dict:
    """爆炸火屑团：多块不规则灼热点 + 灰烬散点。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 7, C_DEEP, 35, falloff=2.1)

    # 主火块
    main = [
        (15, 14, C_ORANGE, 220), (16, 14, C_HOT, 255), (17, 14, C_BRIGHT, 200),
        (14, 15, C_EMBER, 180), (15, 15, C_HOT, 255), (16, 15, C_CORE, 255),
        (17, 15, C_HOT, 240), (18, 15, C_ORANGE, 160),
        (15, 16, C_BRIGHT, 230), (16, 16, C_HOT, 250), (17, 16, C_ORANGE, 200),
        (16, 17, C_EMBER, 160), (17, 17, C_DEEP, 120),
    ]
    hard_blob(g, main)

    # 旁侧碎火屑
    scraps = [
        (11, 12, C_BRIGHT, 200), (12, 12, C_ORANGE, 160), (11, 13, C_EMBER, 140),
        (21, 13, C_HOT, 220), (22, 13, C_ORANGE, 150), (21, 14, C_BRIGHT, 180),
        (13, 19, C_ORANGE, 190), (14, 19, C_EMBER, 150), (13, 20, C_DEEP, 110),
        (20, 18, C_BRIGHT, 170), (19, 19, C_ORANGE, 130),
        (18, 11, C_HOT, 140), (10, 16, C_EMBER, 100),
        (23, 17, C_DEEP, 90),
    ]
    hard_blob(g, scraps)

    # 零星灼热点
    for x, y in ((12, 15), (19, 12), (15, 20), (22, 16), (14, 11)):
        put(g, x, y, C_HOT, 200)
        put(g, x, y - 1 if y > 0 else y, C_ORANGE, 80)

    # 灰烬微粒
    for x, y in ((9, 14), (24, 15), (16, 22), (20, 21), (12, 21)):
        put(g, x, y, C_ASH, 150)
    put(g, 23, 20, C_ASH_PALE, 100)

    return to_json("flame_fragment", g)


def build_flame_sparkle() -> dict:
    """零星灼热光点：极小高亮 + 淡橙晕。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 3.2, C_ORANGE, 50, falloff=1.3)
    put(g, 16, 16, C_CORE, 255)
    put(g, 15, 16, C_HOT, 170)
    put(g, 17, 16, C_HOT, 170)
    put(g, 16, 15, C_BRIGHT, 160)
    put(g, 16, 17, C_ORANGE, 140)
    return to_json("flame_sparkle", g)


def build_ash_mote() -> dict:
    """灰烬微粒：冷灰为主，偶带暗红余温。"""
    g: dict[tuple[int, int], list[int]] = {}
    hard_blob(g, [
        (15, 15, C_ASH, 160),
        (16, 15, C_ASH_PALE, 200),
        (17, 15, C_ASH, 140),
        (15, 16, C_ASH, 180),
        (16, 16, C_ASH_PALE, 230),
        (17, 16, C_DEEP, 100),  # 余温
        (16, 17, C_ASH, 170),
        (15, 17, C_CHAR, 90),
        (18, 16, C_ASH, 80),
        (14, 16, C_ASH, 70),
    ])
    return to_json("ash_mote", g)


def build_flame_flare() -> dict:
    """火焰爆发微光：十字焰刺 + 橙红晕。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 10, C_DEEP, 50, falloff=2.0)
    soft_disk(g, 16, 16, 6.5, C_ORANGE, 110, falloff=1.6)
    for i in range(1, 9):
        a = 210 - i * 20
        rgb = C_HOT if i < 3 else (C_BRIGHT if i < 5 else C_ORANGE)
        put(g, 16 + i, 16, rgb, a)
        put(g, 16 - i, 16, rgb, a)
        put(g, 16, 16 - i, rgb, a)
        put(g, 16, 16 + i, C_EMBER if i > 5 else rgb, a - 15)
    for i in range(1, 5):
        a = 140 - i * 25
        put(g, 16 + i, 16 + i, C_ORANGE, a)
        put(g, 16 - i, 16 - i, C_ORANGE, a)
        put(g, 16 + i, 16 - i, C_EMBER, a - 15)
        put(g, 16 - i, 16 + i, C_EMBER, a - 15)
    put(g, 16, 16, C_CORE, 255)
    return to_json("flame_flare", g)


def build_flame_burst() -> dict:
    """爆炸散落：环状火屑 + 中心灼热 + 外围灰烬。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 16, 16, 5, C_EMBER, 55, falloff=1.7)
    soft_disk(g, 16, 16, 2.5, C_HOT, 160, falloff=1.2)
    put(g, 16, 16, C_CORE, 255)

    # 放射状硬火屑
    rays = [
        (16, 10, C_HOT, 230), (16, 9, C_BRIGHT, 160), (17, 10, C_ORANGE, 120),
        (22, 14, C_BRIGHT, 220), (23, 14, C_ORANGE, 150), (22, 15, C_HOT, 140),
        (21, 20, C_ORANGE, 200), (22, 21, C_EMBER, 130), (20, 21, C_BRIGHT, 110),
        (16, 23, C_BRIGHT, 190), (15, 24, C_EMBER, 120), (17, 23, C_ORANGE, 100),
        (10, 20, C_ORANGE, 180), (9, 21, C_DEEP, 110), (10, 19, C_EMBER, 100),
        (9, 13, C_HOT, 200), (8, 13, C_ORANGE, 130), (9, 14, C_BRIGHT, 120),
        (12, 11, C_BRIGHT, 150), (20, 11, C_ORANGE, 140),
        (13, 22, C_EMBER, 110), (19, 22, C_DEEP, 90),
    ]
    hard_blob(g, rays)

    # 外围灰烬
    for x, y in ((7, 16), (25, 16), (16, 7), (24, 22), (8, 22), (23, 9)):
        put(g, x, y, C_ASH, 130)
    put(g, 6, 18, C_ASH_PALE, 90)
    put(g, 26, 14, C_ASH_PALE, 85)

    return to_json("flame_burst", g)


def build_ember_trail() -> dict:
    """拖尾余烬条：适合弹道尾迹（斜向）。"""
    g: dict[tuple[int, int], list[int]] = {}
    soft_disk(g, 18, 14, 3.0, C_ORANGE, 50, falloff=1.5)
    trail = [
        (20, 12, C_CORE, 255),
        (19, 12, C_HOT, 220),
        (19, 13, C_BRIGHT, 240),
        (18, 13, C_HOT, 230),
        (18, 14, C_BRIGHT, 220),
        (17, 14, C_ORANGE, 200),
        (17, 15, C_ORANGE, 190),
        (16, 15, C_EMBER, 170),
        (16, 16, C_EMBER, 150),
        (15, 16, C_DEEP, 130),
        (15, 17, C_DEEP, 110),
        (14, 17, C_CHAR, 90),
        (14, 18, C_CHAR, 70),
        (13, 18, C_CHAR, 50),
        (20, 13, C_HOT, 160),
        (18, 15, C_EMBER, 100),
        (16, 17, C_DEEP, 80),
    ]
    hard_blob(g, trail)
    return to_json("ember_trail", g)


BUILDERS = [
    # 提示词 1
    lambda: build_ember_mote(0),
    lambda: build_ember_mote(1),
    lambda: build_ember_mote(2),
    build_ember_cinder,
    build_ember_glow,
    build_ember_spark,
    build_ember_wisp,
    build_ember_trail,
    # 提示词 2
    build_flame_shard,
    build_flame_fragment,
    build_flame_sparkle,
    build_ash_mote,
    build_flame_flare,
    build_flame_burst,
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

    print(f"已生成 {len(written)} 个余烬/火焰粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
