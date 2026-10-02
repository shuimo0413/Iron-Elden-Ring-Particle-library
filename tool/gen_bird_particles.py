#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「远景飞鸟」32×32 循环振翅粒子 JSON，并调用 render_pixel_art 导出 PNG。

包含两组三帧动画：正视 ``bird_flap_0~2``、纯侧面朝左 ``bird_side_flap_0~2``（侧视说明见下方分节）。

提示词对应：
    Minecraft 风格远景小鸟剪影、无五官、硬像素纯色平涂、深灰黑主体 + 少量灰褐点缀、
    透明背景、无渐变无羽毛细节；三帧依次为 翅膀上扬 → 两侧平展 → 向下压。

绘制方式：
    每帧只手绘左半边（16 列 ASCII），右半边水平镜像，保证剪影左右对称；
    身体落在中线第 14~17 列。各帧带竖直偏移，让身体中心大致对齐、
    循环播放时只有轻微上下起伏（模拟振翅时躯干的颠簸），不会整只跳动。

字符含义：
    ``#`` 深灰黑主体    ``b`` 灰褐点缀    ``.`` 透明
"""

from __future__ import annotations

import json
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

SIZE = 32
HALF_WIDTH = SIZE // 2

# 深灰黑主体：不用纯黑，贴到天空背景上边缘不至于死黑发脏
C_BODY_DARK = (34, 32, 36, 255)
# 灰褐点缀：只在翅根 / 翼面零星几格，提示羽色但不形成渐变
C_ACCENT_BROWN = (92, 76, 62, 255)

PALETTE = {
    "#": C_BODY_DARK,
    "b": C_ACCENT_BROWN,
}

# ---------------------------------------------------------------------------
# 三帧左半边草图（每行 16 列，第 15 列紧贴中线）
# ---------------------------------------------------------------------------

# 第 1 帧：翅膀向上展开（V 形），翼尖在左上
FRAME_WINGS_UP = [
    ".#..............",
    ".##.............",
    "..##............",
    "..###...........",
    "...###..........",
    "...####.........",
    "....####........",
    "....b####.......",
    ".....#####......",
    "......#####....#",
    ".......#####..##",
    "........########",
    ".........#######",
    "...........b####",
    ".............###",
    "..............##",
    "..............##",
    "...............#",
    "..............##",
    "..............#.",
]

# 第 2 帧：翅膀向两侧平展，翼尖略微下垂，滑翔振翅中段
FRAME_WINGS_LEVEL = [
    "...............#",
    "..............##",
    "..........######",
    "....############",
    "..#####b########",
    ".###.....#######",
    "##...........###",
    "..............##",
    "..............##",
    "...............#",
    "..............##",
    "..............#.",
]

# 第 3 帧：翅膀向下压（倒 V 形），翼尖在左下
FRAME_WINGS_DOWN = [
    "...............#",
    "..............##",
    "...........#####",
    ".........#######",
    "........########",
    ".......#####.###",
    "......#####...##",
    ".....####b....##",
    ".....####......#",
    "....####......##",
    "....###.......#.",
    "...###..........",
    "...##...........",
    "..##............",
    "..#.............",
]

# (名称, 草图, 首行所在 y)；首行 y 决定身体竖直位置，三帧头部约在 13~14 行
FRAMES = [
    ("bird_flap_0", FRAME_WINGS_UP, 5),
    ("bird_flap_1", FRAME_WINGS_LEVEL, 13),
    ("bird_flap_2", FRAME_WINGS_DOWN, 12),
]

# ---------------------------------------------------------------------------
# 侧视飞鸟：纯侧面、朝左飞、深灰褐单色剪影
# ---------------------------------------------------------------------------
# 侧视左右不对称，不能镜像；改用「水平像素段」(y, 起始 x, 结束 x，含两端) 描形。
# 身体 / 头 / 尾三帧共用，只替换翅膀段；每帧再整体竖直平移，
# 让躯干只上下起伏 ±2 像素（振翅颠簸），不会大幅跳动。

# 深灰褐单色：比正视版主体略偏暖，侧面剪影仍保持低饱和远景感
C_SIDE_DARK_BROWN = (70, 58, 50, 255)

# 躯干基准（未平移）：左端尖头、背部平直、右端扇形尾羽略上翘
SIDE_BODY_SPANS = [
    (14, 6, 8),     # 头顶
    (15, 5, 9),     # 头部
    (15, 12, 18),   # 背部隆起（翅根所在）
    (16, 4, 23),    # 尖喙 + 躯干上沿
    (17, 5, 27),    # 躯干 + 尾羽上缘
    (18, 8, 21),    # 腹部
    (18, 24, 28),   # 尾羽下叶，与腹部间留缺口形成分叉感
    (19, 11, 17),   # 腹底
]

# 第 1 帧：翅膀向上扬起，从背部翅根斜向后上方收尖
SIDE_WING_UP_SPANS = [
    (14, 11, 17),
    (13, 11, 17),
    (12, 12, 18),
    (11, 12, 18),
    (10, 13, 19),
    (9, 13, 19),
    (8, 14, 19),
    (7, 15, 20),
    (6, 16, 20),
    (5, 18, 20),
    (4, 19, 20),
    (3, 20, 20),
]

# 第 2 帧：翅膀水平展开；纯侧面时翼面近乎侧对镜头，只露出背上一条向后伸出的翼板
SIDE_WING_LEVEL_SPANS = [
    (13, 13, 18),
    (14, 10, 26),
    (15, 10, 22),
]

# 第 3 帧：翅膀向下压，从腹侧向后下方收尖
SIDE_WING_DOWN_SPANS = [
    (19, 11, 18),
    (20, 12, 18),
    (21, 12, 18),
    (22, 13, 19),
    (23, 14, 19),
    (24, 15, 19),
    (25, 17, 19),
    (26, 18, 19),
]

# (名称, 翅膀段, 整帧竖直偏移 像素)；正值下移，翅膀上扬时下移让剪影整体居中
SIDE_FRAMES = [
    ("bird_side_flap_0", SIDE_WING_UP_SPANS, 2),
    ("bird_side_flap_1", SIDE_WING_LEVEL_SPANS, 0),
    ("bird_side_flap_2", SIDE_WING_DOWN_SPANS, -2),
]


def build_side_frame(name: str, wing_spans: list[tuple[int, int, int]], vertical_offset: int) -> dict:
    """合并躯干段与翅膀段并整体平移，输出单色侧视剪影 JSON。"""
    filled: set[tuple[int, int]] = set()
    for span_y, start_x, end_x in SIDE_BODY_SPANS + wing_spans:
        pixel_y = span_y + vertical_offset
        if not 0 <= pixel_y < SIZE:
            raise ValueError(f"{name} 像素段 y={pixel_y} 超出画布")
        for pixel_x in range(start_x, end_x + 1):
            filled.add((pixel_x, pixel_y))
    pixels = [
        {"x": pixel_x, "y": pixel_y, "rgba": list(C_SIDE_DARK_BROWN)}
        for pixel_x, pixel_y in sorted(filled, key=lambda point: (point[1], point[0]))
    ]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


def build_frame(name: str, left_half_rows: list[str], top_row_y: int) -> dict:
    """把左半边草图镜像成完整 32×32 剪影，输出 render_pixel_art 所需 JSON 结构。"""
    pixels: list[dict] = []
    for row_offset, row_text in enumerate(left_half_rows):
        if len(row_text) != HALF_WIDTH:
            raise ValueError(f"{name} 第 {row_offset} 行长度应为 {HALF_WIDTH}，实际 {len(row_text)}")
        pixel_y = top_row_y + row_offset
        for column, symbol in enumerate(row_text):
            if symbol == ".":
                continue
            rgba = list(PALETTE[symbol])
            mirrored_column = SIZE - 1 - column
            pixels.append({"x": column, "y": pixel_y, "rgba": rgba})
            pixels.append({"x": mirrored_column, "y": pixel_y, "rgba": rgba})
    pixels.sort(key=lambda pixel: (pixel["y"], pixel["x"]))
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


def main() -> int:
    tool_dir = Path(__file__).absolute().parent
    origin = tool_dir / "origin_json"
    library = tool_dir.parent
    origin.mkdir(parents=True, exist_ok=True)

    frame_datas = [build_frame(name, rows, top_row_y) for name, rows, top_row_y in FRAMES]
    frame_datas += [build_side_frame(name, wing_spans, offset) for name, wing_spans, offset in SIDE_FRAMES]

    written: list[str] = []
    for data in frame_datas:
        name = data["name"]
        json_path = origin / f"{name}.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        art = load_pixel_art(json_path)
        png_path = library / f"{name}.png"
        save_png(art, png_path, scale=1)
        written.append(f"{name}: {len(data['pixels'])} px → {png_path.name}")

    print(f"已生成 {len(written)} 张飞鸟粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
