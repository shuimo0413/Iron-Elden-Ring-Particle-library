"""测试用紧凑像素 JSON 构造器。"""

from __future__ import annotations

import json


def square_rows(size: int, start: int, end: int, outline_char: str = "a", fill_char: str = "b") -> list[str]:
    """画一个 [start, end) 的实心方块：外圈 outline_char，内部 fill_char，其余透明。"""
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            if start <= x < end and start <= y < end:
                on_edge = x in (start, end - 1) or y in (start, end - 1)
                row.append(outline_char if on_edge else fill_char)
            else:
                row.append(".")
        rows.append("".join(row))
    return rows


def compact_square(size: int = 32, name: str = "test_square", start: int = 11, end: int = 21) -> dict:
    return {
        "name": name,
        "width": size,
        "height": size,
        "palette": {"a": [30, 40, 80, 255], "b": [150, 190, 255, 255]},
        "rows": square_rows(size, start, end),
    }


def compact_text(**kwargs) -> str:
    return json.dumps(compact_square(**kwargs))
