#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""粒子库宣传总览图生成器。

读取本库根目录 ``*.png``（排除输出文件自身），按**文件名字符升序**排成一张深色
背景宣传图，输出 ``粒子库/粒子库预览.png``。不加系列分组——粒子持续扩充时不必改脚本。

路径注意：``粒子库/`` 在双版本工作区是 junction。必须用 ``Path(__file__).absolute()``
（不要 ``resolve()``），否则会穿过 junction 指到错误目录。

用法（在 ``粒子库/`` 或任意 cwd）：

    python tool/gen_particle_showcase.py

主工程 ``工具链/gen_particle_showcase.py`` 仅做兼容转发。
远程仓：https://github.com/shuimo0413/Iron-Elden-Ring-Particle-library
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 本文件在 粒子库/tool/ → 上一级即粒子库根
PARTICLE_DIR = Path(__file__).absolute().parent.parent
# 输出与贴图同目录；读取时按文件名排除，避免重跑把自己当成粒子
OUTPUT_PATH = PARTICLE_DIR / "粒子库预览.png"

# 画布总宽（像素）；1920 适合发帖 / 视频封面
CANVAS_WIDTH = 1920
# 每行格子数；调大则格子更小、图更矮
COLUMNS_PER_ROW = 12
# 左右外边距（像素）
SIDE_MARGIN = 60
# 贴图放大倍数（最近邻，保留像素风）
SPRITE_SCALE = 4
# 格子内名称文字区高度（像素）
LABEL_HEIGHT = 24
# 光晕模糊半径（像素）；调大发光更柔更散
GLOW_BLUR_RADIUS = 10

BACKGROUND_TOP_COLOR = (10, 12, 28)
BACKGROUND_BOTTOM_COLOR = (4, 4, 12)
TILE_COLOR = (22, 24, 46)
TILE_BORDER_COLOR = (52, 58, 104)
TITLE_COLOR = (214, 226, 255)
SUBTITLE_COLOR = (140, 156, 210)
LABEL_COLOR = (150, 160, 200)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """优先微软雅黑（含中文），找不到则退回 PIL 默认字体。"""
    font_name = "msyhbd.ttc" if bold else "msyh.ttc"
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{font_name}", size)
    except OSError:
        return ImageFont.load_default()


def list_particle_pngs() -> list[Path]:
    """粒子库根目录下全部贴图，文件名字符升序；排除总览输出图本身。"""
    return sorted(
        path for path in PARTICLE_DIR.glob("*.png") if path.name != OUTPUT_PATH.name
    )


def render_tile(particle_path: Path, tile_size: int) -> Image.Image:
    """单个格子：深色底 + 模糊光晕 + 放大的原贴图。"""
    tile = Image.new("RGBA", (tile_size, tile_size), TILE_COLOR + (255,))
    sprite = Image.open(particle_path).convert("RGBA")
    sprite_size = sprite.width * SPRITE_SCALE
    sprite = sprite.resize((sprite_size, sprite_size), Image.NEAREST)
    offset = ((tile_size - sprite_size) // 2, (tile_size - sprite_size) // 2)

    glow_layer = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
    glow_layer.paste(sprite, offset, sprite)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(GLOW_BLUR_RADIUS))
    tile.alpha_composite(glow_layer)
    tile.alpha_composite(sprite, offset)
    return tile


def main() -> None:
    particle_paths = list_particle_pngs()
    if not particle_paths:
        raise SystemExit(f"未找到贴图：{PARTICLE_DIR}")

    cell_width = (CANVAS_WIDTH - SIDE_MARGIN * 2) // COLUMNS_PER_ROW
    tile_size = cell_width - 12
    cell_height = tile_size + LABEL_HEIGHT + 10
    header_height = 170
    footer_height = 60
    grid_top_gap = 12

    row_count = (len(particle_paths) + COLUMNS_PER_ROW - 1) // COLUMNS_PER_ROW
    canvas_height = header_height + grid_top_gap + row_count * cell_height + footer_height

    canvas = Image.new("RGBA", (CANVAS_WIDTH, canvas_height))
    gradient_draw = ImageDraw.Draw(canvas)
    for y in range(canvas_height):
        blend = y / max(1, canvas_height - 1)
        row_color = tuple(
            int(top + (bottom - top) * blend)
            for top, bottom in zip(BACKGROUND_TOP_COLOR, BACKGROUND_BOTTOM_COLOR)
        )
        gradient_draw.line([(0, y), (CANVAS_WIDTH, y)], fill=row_color + (255,))

    draw = ImageDraw.Draw(canvas)
    title_font = load_font(56, bold=True)
    subtitle_font = load_font(24)
    label_font = load_font(13)

    draw.text(
        (CANVAS_WIDTH // 2, 70),
        "Iron's Spells 'n Spellbooks: Elden Ring",
        font=title_font,
        fill=TITLE_COLOR,
        anchor="mm",
    )
    draw.text(
        (CANVAS_WIDTH // 2, 130),
        f"Iron的法术与魔法书：艾尔登法环 · 粒子库总览（共 {len(particle_paths)} 种 · 文件名升序）",
        font=subtitle_font,
        fill=SUBTITLE_COLOR,
        anchor="mm",
    )

    cursor_y = header_height + grid_top_gap
    for index, particle_path in enumerate(particle_paths):
        column = index % COLUMNS_PER_ROW
        row = index // COLUMNS_PER_ROW
        cell_x = SIDE_MARGIN + column * cell_width + (cell_width - tile_size) // 2
        cell_y = cursor_y + row * cell_height
        canvas.alpha_composite(render_tile(particle_path, tile_size), (cell_x, cell_y))
        draw.rectangle(
            [cell_x, cell_y, cell_x + tile_size - 1, cell_y + tile_size - 1],
            outline=TILE_BORDER_COLOR,
            width=1,
        )
        draw.text(
            (cell_x + tile_size // 2, cell_y + tile_size + LABEL_HEIGHT // 2 + 2),
            particle_path.stem,
            font=label_font,
            fill=LABEL_COLOR,
            anchor="mm",
        )

    draw.text(
        (CANVAS_WIDTH // 2, canvas_height - footer_height // 2),
        "Mod ID: iss_elden_ring · Minecraft 1.20.1 Forge / 1.21.1 NeoForge",
        font=subtitle_font,
        fill=SUBTITLE_COLOR,
        anchor="mm",
    )

    canvas.convert("RGB").save(OUTPUT_PATH, optimize=True)
    print(
        f"已输出 {OUTPUT_PATH}（{CANVAS_WIDTH}×{canvas_height}，"
        f"{len(particle_paths)} 张贴图，文件名升序）"
    )


if __name__ == "__main__":
    main()
