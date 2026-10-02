#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「小蝴蝶」32×32 两帧振翅粒子 JSON，并调用 render_pixel_art 导出 PNG。

提示词对应：
    Minecraft 风格单只小蝴蝶、正面略俯视、左右对称、无五官、躯干只有一小段像素、
    硬像素纯色平涂、透明背景、无渐变无阴影无复杂纹理；
    第 1 帧 ``*_flap_0`` 双翅完全张开，第 2 帧 ``*_flap_1`` 双翅向上合拢。

配色变体（共用同一套草图，只换调色板）：
    ``butterfly_flap_*``         淡蓝 + 浅紫
    ``butterfly_orange_flap_*``  暖橙 + 浅黄

绘制方式：
    每帧只手绘左半边（16 列 ASCII），右半边水平镜像，保证左右对称；
    躯干占中线第 15~16 列。两帧躯干与触角位置完全一致，
    循环播放时只有翅膀开合，身体不会跳动。

字符含义：
    ``o`` 描边    ``b`` 翼面主色    ``p`` 翼斑    ``k`` 躯干 / 触角    ``.`` 透明
"""

from __future__ import annotations

import json
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

SIZE = 32
HALF_WIDTH = SIZE // 2

# 深紫描边：只做一圈外轮廓让小尺寸剪影在亮背景上也看得清，不做内阴影
C_OUTLINE_VIOLET = (92, 78, 150, 255)
# 淡蓝翼面：主色，偏粉蓝不刺眼
C_WING_PALE_BLUE = (158, 206, 246, 255)
# 浅紫翼斑：与淡蓝等亮度，纯色块拼接不形成渐变
C_WING_LIGHT_PURPLE = (196, 168, 238, 255)
# 躯干 / 触角：比描边更深一点，作为整只蝴蝶的视觉中轴
C_BODY_DARK_VIOLET = (66, 54, 104, 255)

PALETTE_BLUE_PURPLE = {
    "o": C_OUTLINE_VIOLET,
    "b": C_WING_PALE_BLUE,
    "p": C_WING_LIGHT_PURPLE,
    "k": C_BODY_DARK_VIOLET,
}

# 深橙褐描边：比翼面暗一档，暖色系里保持轮廓清晰，又不像纯黑那样发脏
C_OUTLINE_BURNT_ORANGE = (150, 72, 28, 255)
# 暖橙翼面：主色，饱和偏高，远看像帝王蝶的橙
C_WING_WARM_ORANGE = (244, 146, 52, 255)
# 浅黄翼斑：比橙亮，在翼面上跳出来作为点缀
C_WING_LIGHT_YELLOW = (255, 226, 120, 255)
# 躯干 / 触角：深咖啡色，作为整只蝴蝶的视觉中轴
C_BODY_DARK_BROWN = (84, 44, 22, 255)

PALETTE_ORANGE_YELLOW = {
    "o": C_OUTLINE_BURNT_ORANGE,
    "b": C_WING_WARM_ORANGE,
    "p": C_WING_LIGHT_YELLOW,
    "k": C_BODY_DARK_BROWN,
}

# ---------------------------------------------------------------------------
# 两帧左半边草图（每行 16 列，第 15 列紧贴中线；草图首行即画布 y=0）
# ---------------------------------------------------------------------------

# 第 1 帧：双翅完全张开，前翅宽大偏上，后翅较小偏下，翼面带翼斑色块
FRAME_WINGS_OPEN = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "...........k....",
    "............k...",
    "...oooo......k..",
    "..obbbbooo....k.",
    ".obbbbbbbbooo..k",
    ".obppbbbbbbbbook",
    ".obpppbbbbbbbbok",
    ".obpppbbbbbbbbok",
    "..obpbbbbbbbbbok",
    "..obbbbbbbbbbbok",
    "...oobbbbbbbbook",
    ".....oooobbbbbok",
    "....obbppoobbbok",
    "...obbppppbbbbok",
    "...obbpppbbbbbok",
    "....obbbbbbbbo.k",
    ".....obbbbbbo...",
    "......oooooo....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]

# 第 2 帧：双翅向上合拢，翼面竖直收窄、翼尖指向上方；
# 前翅之间在中线附近留出 1 格缝隙，让触角仍能露出来
FRAME_WINGS_CLOSED = [
    "................",
    "................",
    "..........oo....",
    ".........obbo...",
    "........obbbo...",
    "........obbbbok.",
    "........obppbok.",
    ".......obpppbok.",
    ".......obpppbbo.",
    ".......obbppbbok",
    ".......obbbbbbok",
    ".......obbbbbbok",
    "........obbbbbok",
    "........obbbbbok",
    "........oobbbbok",
    ".........obbbbok",
    ".........oobbbok",
    ".........obppbok",
    ".........obppbok",
    ".........obbbbok",
    "..........obbo.k",
    "...........oo...",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]

# (名称, 草图, 调色板)
FRAMES = [
    ("butterfly_flap_0", FRAME_WINGS_OPEN, PALETTE_BLUE_PURPLE),
    ("butterfly_flap_1", FRAME_WINGS_CLOSED, PALETTE_BLUE_PURPLE),
    ("butterfly_orange_flap_0", FRAME_WINGS_OPEN, PALETTE_ORANGE_YELLOW),
    ("butterfly_orange_flap_1", FRAME_WINGS_CLOSED, PALETTE_ORANGE_YELLOW),
]


def build_frame(name: str, left_half_rows: list[str], palette: dict[str, tuple[int, int, int, int]]) -> dict:
    """把左半边草图镜像成完整 32×32 蝴蝶，输出 render_pixel_art 所需 JSON 结构。"""
    if len(left_half_rows) != SIZE:
        raise ValueError(f"{name} 应有 {SIZE} 行，实际 {len(left_half_rows)}")
    pixels: list[dict] = []
    for pixel_y, row_text in enumerate(left_half_rows):
        if len(row_text) != HALF_WIDTH:
            raise ValueError(f"{name} 第 {pixel_y} 行长度应为 {HALF_WIDTH}，实际 {len(row_text)}")
        for column, symbol in enumerate(row_text):
            if symbol == ".":
                continue
            rgba = list(palette[symbol])
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

    written: list[str] = []
    for name, rows, palette in FRAMES:
        data = build_frame(name, rows, palette)
        json_path = origin / f"{name}.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        art = load_pixel_art(json_path)
        png_path = library / f"{name}.png"
        save_png(art, png_path, scale=1)
        written.append(f"{name}: {len(data['pixels'])} px → {png_path.name}")

    print(f"已生成 {len(written)} 张蝴蝶粒子：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
