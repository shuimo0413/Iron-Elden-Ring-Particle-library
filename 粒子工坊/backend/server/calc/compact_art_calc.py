"""紧凑像素 JSON：校验、有限自动修复、转标准像素 JSON；手改像素 JSON 的校验。

紧凑格式：{name, width, height, palette: {字符: [R,G,B,A]}, rows: [字符串...]}，"." 固定表示透明。
标准格式：{name, width, height, pixels: [{x, y, rgba}]}，与 粒子库/tool/origin_json/ 一致。

所有失败原因都写成可直接回传给模型的中文句子。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

TRANSPARENT_CHAR = "."
# 行长 / 行数与要求相差不超过这个值时自动修复，超过则判失败重试
MAX_AUTO_REPAIR_DIFF = 2
# 同类问题最多列出几条，避免回传消息过长
MAX_LISTED_PROBLEMS = 10

_NAME_INVALID_CHARS = re.compile(r"[^a-z0-9_]+")
_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass
class CompactParseResult:
    ok: bool
    # 修复后的紧凑 JSON（成功时）
    compact: dict[str, Any] | None = None
    # 标准像素 JSON（成功时）
    standard_art: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    # 回传给模型的问题列表（失败时）
    problems: list[str] = field(default_factory=list)
    # palette 中定义了但没用到的键
    unused_palette_keys: list[str] = field(default_factory=list)


def parse_compact_art(
    raw_text: str,
    *,
    size: int,
    max_colors: int,
    finish_reason: str | None = None,
    reasoning_tokens: int = 0,
    existing_names: frozenset[str] | set[str] = frozenset(),
    fallback_name: str = "particle",
) -> CompactParseResult:
    """按顺序校验紧凑 JSON；能修的修并记警告，修不了的列成问题。"""
    warnings: list[str] = []

    if finish_reason == "length":
        if reasoning_tokens > 0:
            return _fail(
                [f"输出被截断：思考用了 {reasoning_tokens} token，json 没写完。请少推敲，尽快按格式输出完整 json。"]
            )
        return _fail(["输出被截断（超过长度上限）。请精简：合并相近颜色、减少调色板键，只输出 json。"])
    text = (raw_text or "").strip()
    if not text:
        return _fail(["返回内容为空，请输出完整的 json 对象。"])

    fenced = _CODE_FENCE.sub("", text).strip()
    if fenced != text:
        warnings.append("返回内容带有代码块标记，已自动去除")
        text = fenced

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return _fail([f"不是合法的 json：第 {exc.lineno} 行第 {exc.colno} 列附近 {exc.msg}。"])
    if not isinstance(data, dict):
        return _fail(["顶层必须是 json 对象。"])

    missing = [key for key in ("name", "width", "height", "palette", "rows") if key not in data]
    if missing:
        return _fail([f"缺少字段：{', '.join(missing)}。"])

    problems: list[str] = []
    width, height = data["width"], data["height"]
    if not isinstance(width, int) or not isinstance(height, int) or isinstance(width, bool):
        return _fail(["width / height 必须是整数。"])
    if width != size or height != size:
        problems.append(f"width / height 为 {width}×{height}，应为 {size}×{size}。")

    palette, palette_problems = _parse_palette(data["palette"], max_colors)
    problems.extend(palette_problems)

    rows = data["rows"]
    if not isinstance(rows, list) or not all(isinstance(row, str) for row in rows):
        problems.append("rows 必须是字符串数组。")
    if problems:
        return _fail(problems, warnings)

    rows, row_problems = _repair_rows(rows, size, warnings)
    if row_problems:
        return _fail(row_problems, warnings)

    char_problems = _check_row_chars(rows, palette)
    if char_problems:
        return _fail(char_problems, warnings)

    name, name_warning = normalize_particle_name(data["name"], existing_names, fallback_name)
    if name_warning:
        warnings.append(name_warning)

    compact = {"name": name, "width": size, "height": size, "palette": palette, "rows": rows}
    used_keys = {char for row in rows for char in row if char != TRANSPARENT_CHAR}
    unused = sorted(key for key in palette if key not in used_keys)
    return CompactParseResult(
        ok=True,
        compact=compact,
        standard_art=to_standard_art(compact),
        warnings=warnings,
        unused_palette_keys=unused,
    )


def to_standard_art(compact: dict[str, Any]) -> dict[str, Any]:
    """紧凑格式 → 标准格式；跳过透明像素。"""
    palette = compact["palette"]
    pixels = []
    for y, row in enumerate(compact["rows"]):
        for x, char in enumerate(row):
            if char == TRANSPARENT_CHAR:
                continue
            pixels.append({"x": x, "y": y, "rgba": list(palette[char])})
    return {"name": compact["name"], "width": compact["width"], "height": compact["height"], "pixels": pixels}


def normalize_particle_name(
    raw_name: Any,
    existing_names: frozenset[str] | set[str] = frozenset(),
    fallback_name: str = "particle",
) -> tuple[str, str | None]:
    """转小写、非法字符换下划线、重名加 _2 / _3 后缀；返回 (规范名, 警告或 None)。"""
    original = raw_name if isinstance(raw_name, str) else ""
    name = _NAME_INVALID_CHARS.sub("_", original.strip().lower()).strip("_")
    name = re.sub(r"_+", "_", name) or fallback_name
    reasons: list[str] = []
    if name != original:
        reasons.append(f"名称「{original}」已规范化为「{name}」")
    if name in existing_names:
        suffix = 2
        while f"{name}_{suffix}" in existing_names:
            suffix += 1
        reasons.append(f"与库内粒子重名，已改为「{name}_{suffix}」")
        name = f"{name}_{suffix}"
    return name, ("；".join(reasons) if reasons else None)


def validate_standard_art(art: Any, *, size: int) -> list[str]:
    """校验标准像素 JSON（手改后批准用）；返回问题列表，空表示合法。"""
    if not isinstance(art, dict):
        return ["像素数据必须是对象"]
    if art.get("width") != size or art.get("height") != size:
        return [f"尺寸必须是 {size}×{size}"]
    pixels = art.get("pixels")
    if not isinstance(pixels, list):
        return ["pixels 必须是数组"]
    problems: list[str] = []
    seen: set[tuple[int, int]] = set()
    for index, pixel in enumerate(pixels):
        if not isinstance(pixel, dict):
            problems.append(f"pixels[{index}] 必须是对象")
            continue
        x, y, rgba = pixel.get("x"), pixel.get("y"), pixel.get("rgba")
        if not (isinstance(x, int) and isinstance(y, int) and 0 <= x < size and 0 <= y < size):
            problems.append(f"pixels[{index}] 坐标越界")
        elif (x, y) in seen:
            problems.append(f"pixels[{index}] 坐标 ({x},{y}) 重复")
        else:
            seen.add((x, y))
        if not _is_rgba(rgba):
            problems.append(f"pixels[{index}].rgba 必须是 4 个 0–255 的整数")
        if len(problems) >= MAX_LISTED_PROBLEMS:
            break
    return problems


def _fail(problems: list[str], warnings: list[str] | None = None) -> CompactParseResult:
    return CompactParseResult(ok=False, problems=problems, warnings=list(warnings or []))


def _is_rgba(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(channel, int) and not isinstance(channel, bool) and 0 <= channel <= 255 for channel in value)
    )


def _parse_palette(raw_palette: Any, max_colors: int) -> tuple[dict[str, list[int]], list[str]]:
    if not isinstance(raw_palette, dict) or not raw_palette:
        return {}, ["palette 必须是非空对象。"]
    problems: list[str] = []
    palette: dict[str, list[int]] = {}
    for key, value in raw_palette.items():
        if len(key) != 1 or key == TRANSPARENT_CHAR or key.isspace():
            problems.append(f"palette 键「{key}」不合法：必须是单个可见字符，且不能是 \".\"。")
            continue
        if not _is_rgba(value):
            problems.append(f"palette「{key}」的值必须是 [R,G,B,A]，每项 0–255 的整数。")
            continue
        palette[key] = list(value)
    if len(raw_palette) > max_colors:
        problems.append(f"palette 有 {len(raw_palette)} 种颜色，超过上限 {max_colors}，请合并相近颜色。")
    return palette, problems[:MAX_LISTED_PROBLEMS]


def _repair_rows(rows: list[str], size: int, warnings: list[str]) -> tuple[list[str], list[str]]:
    """行数 / 行长相差 ≤ MAX_AUTO_REPAIR_DIFF 时修复，否则返回问题。"""
    rows = list(rows)
    row_diff = len(rows) - size
    if abs(row_diff) > MAX_AUTO_REPAIR_DIFF:
        return rows, [f"rows 共 {len(rows)} 行，应为 {size} 行。"]
    if row_diff < 0:
        rows.extend([TRANSPARENT_CHAR * size] * (-row_diff))
        warnings.append(f"rows 少 {-row_diff} 行，已在底部补透明行")
    elif row_diff > 0:
        rows = rows[:size]
        warnings.append(f"rows 多 {row_diff} 行，已裁掉底部多余行")

    problems: list[str] = []
    repaired: list[str] = []
    for index, row in enumerate(rows):
        diff = len(row) - size
        if diff == 0:
            repaired.append(row)
            continue
        if abs(diff) > MAX_AUTO_REPAIR_DIFF:
            if len(problems) < MAX_LISTED_PROBLEMS:
                problems.append(f"第 {index + 1} 行（y={index}）长度 {len(row)}，应为 {size}。")
            repaired.append(row)
            continue
        repaired.append(_fix_row_length(row, size))
        action = "右侧补透明" if diff < 0 else "裁掉多余字符"
        warnings.append(f"第 {index + 1} 行长度 {len(row)}，已{action}")
    return repaired, problems


def _fix_row_length(row: str, size: int) -> str:
    """短了右侧补 "."；长了优先裁右端 "."，再裁左端 "."，都裁不掉才从右侧截断。"""
    if len(row) < size:
        return row + TRANSPARENT_CHAR * (size - len(row))
    while len(row) > size and row.endswith(TRANSPARENT_CHAR):
        row = row[:-1]
    while len(row) > size and row.startswith(TRANSPARENT_CHAR):
        row = row[1:]
    return row[:size]


def _check_row_chars(rows: list[str], palette: dict[str, list[int]]) -> list[str]:
    problems: list[str] = []
    for index, row in enumerate(rows):
        for column, char in enumerate(row):
            if char != TRANSPARENT_CHAR and char not in palette:
                problems.append(f"第 {index + 1} 行（y={index}）第 {column} 列出现调色板外的字符「{char}」。")
                break
        if len(problems) >= MAX_LISTED_PROBLEMS:
            break
    return problems
