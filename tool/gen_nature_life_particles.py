#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「自然生命魔法」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

提示词对应：
    嫩绿与草绿微光、细小叶片碎片、花瓣碎屑、漂浮花粉光点、柔和青绿光晕；
    硬朗像素边缘、有限配色、透明背景、画面居中。

配色（共 9 色）：
    叶片：深草绿 → 草绿 → 嫩绿 → 黄绿高光
    光晕：青绿 → 浅青绿
    花瓣：淡粉 → 粉白
    花粉：暖黄白
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

SIZE = 32
CENTER = 16

# 叶片四阶：轮廓深绿保证硬边可读，内部逐级提亮
C_LEAF_DEEP = (38, 110, 52)
C_LEAF_GRASS = (72, 160, 64)
C_LEAF_FRESH = (130, 210, 90)
C_LEAF_LIGHT = (200, 240, 140)
# 柔和青绿光晕（只用低 alpha 做底晕，不抢叶片轮廓）
C_GLOW_TEAL = (60, 200, 160)
C_GLOW_PALE = (160, 245, 210)
# 花瓣碎屑
C_PETAL_PINK = (240, 160, 190)
C_PETAL_PALE = (255, 225, 235)
# 花粉光点
C_POLLEN = (255, 250, 200)

Grid = dict[tuple[int, int], list[int]]


def put(grid: Grid, x: int, y: int, rgb: tuple[int, int, int], alpha: int) -> None:
    """写入像素；同格取更高 alpha，保证后画的弱晕不会盖掉实体像素。"""
    if not (0 <= x < SIZE and 0 <= y < SIZE):
        return
    alpha = max(0, min(255, int(alpha)))
    if alpha <= 0:
        return
    key = (x, y)
    if key not in grid or alpha >= grid[key][3]:
        grid[key] = [rgb[0], rgb[1], rgb[2], alpha]


def soft_disk(grid: Grid, cx: float, cy: float, radius: float,
              rgb: tuple[int, int, int], alpha_core: int, falloff: float = 1.8) -> None:
    """柔和圆形光晕：alpha 按到圆心距离做幂次衰减（falloff 越大边缘越快变淡）。"""
    radius_ceil = int(math.ceil(radius)) + 1
    for dy in range(-radius_ceil, radius_ceil + 1):
        for dx in range(-radius_ceil, radius_ceil + 1):
            x, y = int(cx) + dx, int(cy) + dy
            distance = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if distance > radius:
                continue
            closeness = 1.0 - distance / radius
            put(grid, x, y, rgb, int(alpha_core * closeness ** falloff))


def leaf(grid: Grid, cx: float, cy: float, length: float, width: float, angle_degrees: float,
         fill_rgb: tuple[int, int, int] = C_LEAF_FRESH,
         edge_rgb: tuple[int, int, int] = C_LEAF_DEEP,
         vein_rgb: tuple[int, int, int] = C_LEAF_LIGHT) -> None:
    """尖头叶片：沿主轴 u∈[0,1]，半宽 = width/2 · sin(πu)^0.75（两端尖、中段饱满）。

    外圈一像素用 edge_rgb 做硬轮廓，主轴一像素用 vein_rgb 做叶脉高光，
    叶片向光一侧（v<0）多提亮一档，避免纯平涂。
    """
    angle = math.radians(angle_degrees)
    axis_x, axis_y = math.cos(angle), math.sin(angle)
    normal_x, normal_y = -axis_y, axis_x
    start_x = cx - axis_x * length / 2
    start_y = cy - axis_y * length / 2

    def local_coords(px: float, py: float) -> tuple[float, float, float]:
        rel_x, rel_y = px - start_x, py - start_y
        along = (rel_x * axis_x + rel_y * axis_y) / length
        across = rel_x * normal_x + rel_y * normal_y
        half_width = (width / 2) * math.sin(math.pi * along) if 0 < along < 1 else 0.0
        return along, across, half_width

    inside: set[tuple[int, int]] = set()
    reach = int(length / 2 + width) + 2
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            x, y = int(cx) + dx, int(cy) + dy
            along, across, half_width = local_coords(x + 0.5, y + 0.5)
            if half_width > 0.35 and abs(across) <= half_width:
                inside.add((x, y))

    for x, y in inside:
        is_edge = any((x + ox, y + oy) not in inside for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        along, across, half_width = local_coords(x + 0.5, y + 0.5)
        if is_edge:
            put(grid, x, y, edge_rgb, 235)
        elif abs(across) < 0.55 and 0.12 < along < 0.9:
            put(grid, x, y, vein_rgb, 250)
        elif across < 0:
            put(grid, x, y, fill_rgb, 245)
        else:
            put(grid, x, y, C_LEAF_GRASS, 240)

    # 叶柄：从根部沿主轴反方向伸出 stem_pixels 像素，让叶片轮廓一眼可辨
    stem_pixels = 2 if length >= 10 else 1
    for step in range(1, stem_pixels + 1):
        put(grid, int(start_x - axis_x * (step - 0.5)), int(start_y - axis_y * (step - 0.5)), edge_rgb, 230)


def petal(grid: Grid, cx: float, cy: float, length: float, width: float, angle_degrees: float) -> None:
    """花瓣碎屑：圆头水滴形，尖端朝 angle 反方向（花心），粉色外缘 + 粉白内心。"""
    angle = math.radians(angle_degrees)
    axis_x, axis_y = math.cos(angle), math.sin(angle)
    normal_x, normal_y = -axis_y, axis_x
    start_x = cx - axis_x * length / 2
    start_y = cy - axis_y * length / 2
    inside: set[tuple[int, int]] = set()
    reach = int(length + width) + 2
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            x, y = int(cx) + dx, int(cy) + dy
            rel_x, rel_y = x + 0.5 - start_x, y + 0.5 - start_y
            along = (rel_x * axis_x + rel_y * axis_y) / length
            across = rel_x * normal_x + rel_y * normal_y
            if not 0 < along < 1:
                continue
            # a^0.9·√(1-a²)：根部尖、头部圆；除以 0.52（该函数峰值）归一到 width/2
            half_width = (width / 2) * (along ** 0.9) * math.sqrt(1 - along * along) / 0.52
            if half_width > 0.35 and abs(across) <= half_width:
                inside.add((x, y))
    for x, y in inside:
        is_edge = any((x + ox, y + oy) not in inside for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        put(grid, x, y, C_PETAL_PINK if is_edge else C_PETAL_PALE, 235 if is_edge else 250)


def pollen(grid: Grid, x: int, y: int, size: int) -> None:
    """花粉光点：size 0=单点，1=小十字，2=十字 + 青绿微晕。"""
    put(grid, x, y, C_POLLEN, 255 if size >= 1 else 200)
    if size >= 1:
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(grid, x + ox, y + oy, C_LEAF_LIGHT, 150)
    if size >= 2:
        soft_disk(grid, x + 0.5, y + 0.5, 3.0, C_GLOW_TEAL, 70, falloff=1.3)


def to_json(name: str, grid: Grid) -> dict:
    pixels = [{"x": x, "y": y, "rgba": rgba} for (x, y), rgba in sorted(grid.items()) if rgba[3] > 0]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


# ---------------------------------------------------------------------------
# 主精灵：自然生命魔法粒子（叶 + 花瓣 + 花粉 + 青绿晕合成）
# ---------------------------------------------------------------------------


def build_nature_bloom() -> dict:
    """主精灵：青绿光晕中心一枚嫩叶，周围飘散小叶片、花瓣碎屑与花粉光点。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 14, C_GLOW_TEAL, 95, falloff=1.9)
    soft_disk(grid, CENTER, CENTER, 8, C_GLOW_PALE, 120, falloff=1.6)
    leaf(grid, CENTER, CENTER, 14, 8, -45)
    leaf(grid, 7.5, 21.5, 8, 4.5, 15, fill_rgb=C_LEAF_GRASS)
    leaf(grid, 24.5, 8.5, 7, 4, 115, fill_rgb=C_LEAF_GRASS)
    petal(grid, 23.5, 23, 7, 5, 40)
    petal(grid, 8.5, 8.5, 6, 4.5, -140)
    for x, y, size in ((5, 14, 1), (27, 15, 1), (15, 4, 0), (17, 27, 1), (12, 26, 0),
                       (20, 4, 0), (28, 26, 0), (3, 9, 0), (4, 27, 0)):
        pollen(grid, x, y, size)
    return to_json("nature_bloom", grid)


# ---------------------------------------------------------------------------
# 可单独发射的组件粒子
# ---------------------------------------------------------------------------


def build_nature_leaf() -> dict:
    """单片嫩叶碎片（带叶脉与淡青晕），适合旋转飘落。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 11, C_GLOW_TEAL, 75, falloff=2.0)
    leaf(grid, CENTER, CENTER, 18, 9, -40)
    return to_json("nature_leaf", grid)


def build_nature_leaf_small() -> dict:
    """细小叶片碎片：两片草绿小叶错开，做密集飘散用。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 9, C_GLOW_TEAL, 60, falloff=2.0)
    leaf(grid, 14, 14, 10, 5, -60)
    leaf(grid, 20, 20, 8, 4.5, 15, fill_rgb=C_LEAF_GRASS)
    return to_json("nature_leaf_small", grid)


def build_nature_petal() -> dict:
    """花瓣碎屑：三枚大小不一的淡粉花瓣。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 10, C_GLOW_TEAL, 60, falloff=2.0)
    petal(grid, 15, 13, 10, 7, -30)
    petal(grid, 22, 21, 7, 5, 60)
    petal(grid, 9.5, 21, 6, 4.5, 160)
    return to_json("nature_petal", grid)


def build_nature_flower() -> dict:
    """五瓣小花：粉白花瓣 + 暖黄花心，外围一圈青绿微晕。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 13, C_GLOW_TEAL, 85, falloff=2.0)
    for index in range(5):
        angle_degrees = -90 + index * 72
        rad = math.radians(angle_degrees)
        petal(grid, CENTER + math.cos(rad) * 4.2, CENTER + math.sin(rad) * 4.2, 6.5, 5, angle_degrees)
    soft_disk(grid, CENTER, CENTER, 2.2, C_POLLEN, 255, falloff=0.3)
    put(grid, CENTER - 1, CENTER - 1, C_LEAF_LIGHT, 255)
    return to_json("nature_flower", grid)


def build_nature_pollen() -> dict:
    """漂浮花粉光点散射。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 12, C_GLOW_TEAL, 60, falloff=2.2)
    for x, y, size in ((16, 16, 2), (10, 11, 1), (22, 12, 1), (12, 22, 1), (21, 21, 0),
                       (7, 17, 0), (25, 17, 0), (16, 8, 0), (18, 25, 1), (13, 15, 0),
                       (20, 15, 0), (24, 24, 0), (8, 8, 0), (23, 7, 0)):
        pollen(grid, x, y, size)
    return to_json("nature_pollen", grid)


def build_nature_glow() -> dict:
    """柔和青绿光晕球（拖尾 / 治疗芯）。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 14, C_GLOW_TEAL, 110, falloff=1.8)
    soft_disk(grid, CENTER, CENTER, 9, C_GLOW_PALE, 170, falloff=1.4)
    soft_disk(grid, CENTER, CENTER, 5.5, C_LEAF_LIGHT, 230, falloff=1.0)
    soft_disk(grid, CENTER, CENTER, 2.5, C_POLLEN, 255, falloff=0.6)
    return to_json("nature_glow", grid)


def build_nature_sparkle() -> dict:
    """嫩绿微光十字闪烁。"""
    grid: Grid = {}
    soft_disk(grid, CENTER, CENTER, 5, C_GLOW_TEAL, 70, falloff=1.5)
    put(grid, CENTER, CENTER, C_POLLEN, 255)
    for step in range(1, 4):
        alpha = 230 - step * 50
        rgb = C_LEAF_LIGHT if step == 1 else C_LEAF_FRESH
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(grid, CENTER + ox * step, CENTER + oy * step, rgb, alpha)
    for ox, oy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
        put(grid, CENTER + ox, CENTER + oy, C_LEAF_GRASS, 110)
    return to_json("nature_sparkle", grid)


def build_nature_mote(index: int) -> dict:
    """漂浮生命微粒：0 单点、1 小十字、2 带青绿晕的小叶芽。"""
    grid: Grid = {}
    if index == 0:
        pollen(grid, CENTER, CENTER, 0)
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(grid, CENTER + ox, CENTER + oy, C_LEAF_FRESH, 90)
    elif index == 1:
        soft_disk(grid, CENTER, CENTER, 3.5, C_GLOW_TEAL, 70, falloff=1.5)
        pollen(grid, CENTER, CENTER, 1)
    else:
        soft_disk(grid, CENTER, CENTER, 7, C_GLOW_TEAL, 80, falloff=1.8)
        leaf(grid, CENTER, CENTER, 9, 5, -45)
    return to_json(f"nature_mote_{index}", grid)


BUILDERS = [
    build_nature_bloom,
    build_nature_leaf,
    build_nature_leaf_small,
    build_nature_petal,
    build_nature_flower,
    build_nature_pollen,
    build_nature_glow,
    build_nature_sparkle,
    lambda: build_nature_mote(0),
    lambda: build_nature_mote(1),
    lambda: build_nature_mote(2),
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

    print(f"已生成 {len(written)} 个自然生命粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
