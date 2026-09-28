#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从图片提取 RGBA，输出与 ``render_pixel_art.py`` 兼容的像素 JSON。

典型用途：
1. 把现有粒子 / 物品 PNG 转成 ``name`` / ``width`` / ``height`` / ``pixels`` JSON；
2. 再交给大语言模型改画，或用 ``render_pixel_art.py`` 回导出 PNG。

默认跳过完全透明像素（``A == 0``），与仓库里手写像素 JSON 的稀疏写法一致。
需要 Pillow：``pip install Pillow``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_rgba_grid(image_path: Path) -> tuple[int, int, list[list[tuple[int, int, int, int]]]]:
    """读取图片并转为 ``height × width`` 的 RGBA 网格（每通道 0–255）。"""
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "缺少 Pillow。请先安装：pip install Pillow"
        ) from exc

    with Image.open(image_path) as image:
        rgba_image = image.convert("RGBA")
        width, height = rgba_image.size
        # Pillow 14 起 getdata 会删；get_flattened_data 直接给出 (R,G,B,A) 序列。
        if hasattr(rgba_image, "get_flattened_data"):
            raw_pixels = list(rgba_image.get_flattened_data())
        else:
            raw_pixels = list(rgba_image.getdata())

    if width <= 0 or height <= 0:
        raise ValueError(f"图片尺寸无效: {width}x{height}")
    if len(raw_pixels) != width * height:
        raise ValueError(
            f"像素数量与尺寸不符: 期望 {width * height}，实际 {len(raw_pixels)}"
        )

    grid: list[list[tuple[int, int, int, int]]] = []
    for row_index in range(height):
        row_start = row_index * width
        row = [
            (
                int(raw_pixels[row_start + column_index][0]),
                int(raw_pixels[row_start + column_index][1]),
                int(raw_pixels[row_start + column_index][2]),
                int(raw_pixels[row_start + column_index][3]),
            )
            for column_index in range(width)
        ]
        grid.append(row)
    return width, height, grid


def grid_to_pixel_art(
    name: str,
    width: int,
    height: int,
    grid: list[list[tuple[int, int, int, int]]],
    *,
    min_alpha: int,
) -> dict:
    """把网格打成像素画 JSON；``min_alpha`` 以下（不含）的像素不写入 ``pixels``。

    调大 ``min_alpha``：更稀疏、更像粒子描边；调到 0：保留全透明也写出。
    """
    if not 0 <= min_alpha <= 255:
        raise ValueError(f"min_alpha 必须在 0–255，当前: {min_alpha}")

    pixels: list[dict] = []
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = grid[y][x]
            if alpha < min_alpha:
                continue
            pixels.append(
                {
                    "x": x,
                    "y": y,
                    "rgba": [red, green, blue, alpha],
                }
            )

    return {
        "name": name,
        "width": width,
        "height": height,
        "pixels": pixels,
    }


def collect_unique_rgba(
    grid: list[list[tuple[int, int, int, int]]],
    *,
    min_alpha: int,
) -> list[tuple[int, int, int, int]]:
    """按首次出现顺序收集唯一 RGBA（同样受 ``min_alpha`` 过滤）。"""
    seen: set[tuple[int, int, int, int]] = set()
    unique_colors: list[tuple[int, int, int, int]] = []
    for row in grid:
        for rgba in row:
            if rgba[3] < min_alpha:
                continue
            if rgba in seen:
                continue
            seen.add(rgba)
            unique_colors.append(rgba)
    return unique_colors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从图片提取 RGBA，导出 render_pixel_art 兼容的像素 JSON"
    )
    parser.add_argument(
        "image",
        type=Path,
        help="输入图片路径（PNG / JPG / WebP 等，Pillow 能开的都可）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="输出 JSON 路径（默认：与图片同目录、<stem>.json）",
    )
    parser.add_argument(
        "--name",
        help="写入 JSON 的 name 字段（默认：图片文件名去掉后缀）",
    )
    parser.add_argument(
        "--min-alpha",
        type=int,
        default=1,
        help="写入 / 统计时的最低 alpha（默认 1=跳过完全透明；0=保留全部像素）",
    )
    parser.add_argument(
        "--unique",
        action="store_true",
        help="额外在 stderr 打印去重后的 RGBA 调色板",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON 缩进空格数（默认 2；0 表示紧凑单行）",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = parse_args()
    image_path = args.image
    if not image_path.is_file():
        print(f"错误: 找不到图片: {image_path}", file=sys.stderr)
        return 1

    try:
        width, height, grid = load_rgba_grid(image_path)
        art_name = args.name or image_path.stem
        art = grid_to_pixel_art(
            art_name,
            width,
            height,
            grid,
            min_alpha=args.min_alpha,
        )
    except (OSError, ValueError, ImportError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    output_path = args.output
    if output_path is None:
        output_path = image_path.with_suffix(".json")

    indent = None if args.indent <= 0 else args.indent
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(art, ensure_ascii=False, indent=indent) + "\n",
        encoding="utf-8",
    )

    written_count = len(art["pixels"])
    total_count = width * height
    print(
        f"已写入: {output_path.resolve()}\n"
        f"尺寸: {width}x{height}  name={art_name}\n"
        f"写出像素: {written_count}/{total_count}  (min_alpha={args.min_alpha})"
    )

    if args.unique:
        unique_colors = collect_unique_rgba(grid, min_alpha=args.min_alpha)
        print(f"唯一 RGBA 数: {len(unique_colors)}", file=sys.stderr)
        for red, green, blue, alpha in unique_colors:
            print(f"  [{red}, {green}, {blue}, {alpha}]", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
