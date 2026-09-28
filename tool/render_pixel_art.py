#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从像素画 JSON 读取 RGBA 数据，控制台预览并导出 PNG。

典型流程（给大语言模型 / 人工画像素用）：
1. 让模型按 ``name`` / ``width`` / ``height`` / ``pixels[{x,y,rgba}]`` 格式输出 JSON；
2. 把 JSON 存到本目录旁或任意路径；
3. 运行本脚本组装 PNG（粒子入库存图常用 ``--png-scale 1``）。

本文件归属独立仓库「粒子库」的 ``tool/``；主工程 ``工具链/render_pixel_art.py`` 仅做兼容转发。
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import zlib
from pathlib import Path


RESET = "\033[0m"
ALPHA_VISIBLE = 128  # alpha 低于此值视为透明（仅控制台）
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def enable_windows_ansi() -> None:
    """在 Windows 上尽量开启 ANSI 真彩色支持。"""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def list_json_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.json") if p.is_file())


def load_pixel_art(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    required = ("width", "height", "pixels")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"JSON 缺少字段: {', '.join(missing)}")

    width = int(data["width"])
    height = int(data["height"])
    if width <= 0 or height <= 0:
        raise ValueError("width / height 必须为正整数")

    pixels = data["pixels"]
    if not isinstance(pixels, list):
        raise ValueError("pixels 必须是数组")

    grid: list[list[tuple[int, int, int, int] | None]] = [
        [None for _ in range(width)] for _ in range(height)
    ]

    for i, item in enumerate(pixels):
        if not isinstance(item, dict):
            raise ValueError(f"pixels[{i}] 必须是对象，例如 {{\"x\":0,\"y\":0,\"rgba\":[255,0,0,255]}}")

        try:
            x = int(item["x"])
            y = int(item["y"])
            rgba = item["rgba"]
        except KeyError as exc:
            raise ValueError(f"pixels[{i}] 缺少字段: {exc}") from exc

        if not (isinstance(rgba, list) and len(rgba) == 4):
            raise ValueError(f"pixels[{i}].rgba 必须是长度为 4 的数组 [R,G,B,A]")

        r, g, b, a = (int(v) for v in rgba)
        for channel, name in ((r, "R"), (g, "G"), (b, "B"), (a, "A")):
            if not 0 <= channel <= 255:
                raise ValueError(f"pixels[{i}].rgba {name} 超出 0-255: {channel}")

        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(f"pixels[{i}] 坐标越界: ({x}, {y})，画布为 {width}x{height}")

        grid[y][x] = (r, g, b, a)

    return {
        "name": data.get("name", path.stem),
        "width": width,
        "height": height,
        "grid": grid,
    }


def rgba_to_cell(rgba: tuple[int, int, int, int] | None) -> str:
    if rgba is None or rgba[3] < ALPHA_VISIBLE:
        return "  "

    r, g, b, _ = rgba
    # 用背景色块渲染，比前景字符更「方」、更像像素
    return f"\033[48;2;{r};{g};{b}m  {RESET}"


def render(art: dict, scale: int = 1) -> str:
    title = f"名称: {art['name']}"
    size = f"尺寸: {art['width']} x {art['height']}"
    if scale > 1:
        size += f"  (放大 x{scale})"

    lines = [title, size, "-" * (art["width"] * 2 * scale + 4)]

    for row in art["grid"]:
        row_text = "".join(rgba_to_cell(cell) * scale for cell in row)
        for _ in range(scale):
            lines.append(row_text)

    return "\n".join(lines)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk = chunk_type + data
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)


def save_png(art: dict, output_path: Path, scale: int = 16) -> Path:
    """把像素网格写成 RGBA PNG（最近邻放大），无需第三方库。"""
    width = art["width"]
    height = art["height"]
    out_w = width * scale
    out_h = height * scale
    grid = art["grid"]

    raw = bytearray()
    for y in range(out_h):
        raw.append(0)  # filter: None
        src_y = y // scale
        for x in range(out_w):
            src_x = x // scale
            cell = grid[src_y][src_x]
            if cell is None:
                raw.extend((0, 0, 0, 0))
            else:
                raw.extend(cell)

    ihdr = struct.pack(">IIBBBBB", out_w, out_h, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png = (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _png_chunk(b"IEND", b"")
    )

    output_path.write_bytes(png)
    return output_path


def choose_json(files: list[Path]) -> Path:
    if not files:
        raise FileNotFoundError("当前目录下没有 .json 文件")

    if len(files) == 1:
        return files[0]

    print("当前目录可用的像素画 JSON：")
    for idx, path in enumerate(files, start=1):
        print(f"  [{idx}] {path.name}")

    while True:
        raw = input("请选择编号（回车=1）: ").strip()
        if raw == "":
            return files[0]
        if raw.isdigit() and 1 <= int(raw) <= len(files):
            return files[int(raw) - 1]
        print("输入无效，请重新选择。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="读取 JSON 中的 RGBA 像素数据并在控制台渲染")
    parser.add_argument(
        "file",
        nargs="?",
        help="JSON 文件名或路径（默认：交互选择当前目录下的 json）",
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=int,
        default=2,
        help="控制台像素放大倍数，默认 2",
    )
    parser.add_argument(
        "--png-scale",
        type=int,
        default=16,
        help="导出 PNG 时每个逻辑像素放大倍数，默认 16",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="PNG 输出文件名（默认：<name>.png，保存在当前目录）",
    )
    return parser.parse_args()


def main() -> int:
    enable_windows_ansi()
    # Windows 控制台默认编码常导致中文乱码
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = parse_args()

    if args.scale < 1:
        print("scale 必须 >= 1", file=sys.stderr)
        return 1
    if args.png_scale < 1:
        print("png-scale 必须 >= 1", file=sys.stderr)
        return 1

    cwd = Path.cwd()

    try:
        if args.file:
            path = Path(args.file)
            if not path.is_file():
                # 允许只写文件名，从当前目录找
                candidate = cwd / args.file
                if candidate.is_file():
                    path = candidate
                else:
                    raise FileNotFoundError(f"找不到文件: {args.file}")
        else:
            path = choose_json(list_json_files(cwd))

        art = load_pixel_art(path)
        print(render(art, scale=args.scale))

        out_name = args.output or f"{art['name']}.png"
        out_path = Path(out_name)
        if not out_path.is_absolute():
            out_path = cwd / out_path

        saved = save_png(art, out_path, scale=args.png_scale)
        print(f"\n来源: {path.resolve()}")
        print(f"已保存 PNG: {saved.resolve()}  ({art['width'] * args.png_scale}x{art['height'] * args.png_scale})")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
