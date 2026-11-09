"""提示词拼装：按钮选项 + 描述 → system / user 消息；重试 / 打回消息；尺寸冲突检测。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from common.constant.canvas_size import get_canvas_spec
from common.constant.particle_option import (
    AUTO,
    CATEGORY_OPTIONS,
    OUTLINE_OPTIONS,
    PALETTE_OPTIONS,
    SYMMETRY_OPTIONS,
    find_option,
)
from common.constant.prompt_template import (
    AUTO_TEXT,
    HUMAN_FEEDBACK_LABEL,
    MARGIN_NONE_TEXT,
    MARGIN_TEXT_TEMPLATE,
    PALETTE_ANCHOR_TEMPLATE,
    RETRY_FOOTER,
    RETRY_HEADER,
    SIZE_CONFLICT_NOTE,
    STYLE_HINT_TEMPLATE,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)

# 描述里的 "16x16" / "16×16" / "16*16"；只认两边相等的方形尺寸
_SIZE_PATTERN = re.compile(r"(\d{1,3})\s*[x×X*]\s*(\d{1,3})")


@dataclass
class PromptBundle:
    system: str
    user: str
    notes: list[str] = field(default_factory=list)


def build_prompt(description: str, options: dict) -> PromptBundle:
    """按钮 + 描述 → 首轮提示词。按钮优先，描述中的冲突尺寸只记 notes。"""
    size = int(options["size"])
    spec = get_canvas_spec(size)
    margin_text = MARGIN_TEXT_TEMPLATE.format(margin=spec.margin_px) if spec.margin_px > 0 else MARGIN_NONE_TEXT
    user = USER_PROMPT_TEMPLATE.format(
        size=size,
        margin_text=margin_text,
        max_colors=spec.max_colors,
        category_text=_option_text(CATEGORY_OPTIONS, options["category"]),
        palette_text=_palette_text(options["palette"]),
        outline_text=_option_text(OUTLINE_OPTIONS, options["outline"]),
        symmetry_text=_option_text(SYMMETRY_OPTIONS, options["symmetry"]),
        guide=spec.guide,
        description=description.strip(),
    )
    return PromptBundle(system=SYSTEM_PROMPT, user=user, notes=detect_size_conflicts(description, size))


def apply_style_hint(user_prompt: str, style_hint: str | None) -> str:
    """多变体时在 user 消息末尾追加不同的风格倾向。"""
    if not style_hint:
        return user_prompt
    return user_prompt + STYLE_HINT_TEMPLATE.format(style_hint=style_hint)


def build_retry_message(problems: list[str], human_feedback: str | None = None) -> str:
    """重试 / 打回消息：设计者意见放最前面，其后是编号的问题列表。"""
    lines = [RETRY_HEADER]
    number = 1
    if human_feedback and human_feedback.strip():
        lines.append(f"{number}. {HUMAN_FEEDBACK_LABEL}{human_feedback.strip()}")
        number += 1
    for problem in problems:
        lines.append(f"{number}. {problem}")
        number += 1
    lines.append(RETRY_FOOTER)
    return "\n".join(lines)


def detect_size_conflicts(description: str, size: int) -> list[str]:
    """只检测描述里明确写出的方形尺寸；与按钮不一致时返回一条提示。"""
    notes: list[str] = []
    for match in _SIZE_PATTERN.finditer(description):
        width, height = int(match.group(1)), int(match.group(2))
        if width == height and width != size:
            notes.append(SIZE_CONFLICT_NOTE.format(found=match.group(0), size=size))
    return notes


def render_messages_text(messages: list[dict]) -> str:
    """把对话历史拼成可读文本，写 prompt.txt 留档。"""
    blocks = [f"===== {message['role']} =====\n{message['content']}" for message in messages]
    return "\n\n".join(blocks) + "\n"


def _option_text(options, value: str) -> str:
    if value == AUTO:
        return AUTO_TEXT
    item = find_option(options, value)
    if item is None:
        return AUTO_TEXT
    return item.prompt_text or item.label


def _palette_text(value: str) -> str:
    if value == AUTO:
        return AUTO_TEXT
    item = find_option(PALETTE_OPTIONS, value)
    if item is None:
        return AUTO_TEXT
    if not item.anchors:
        return item.label
    anchors = " → ".join(f"({r},{g},{b})" for r, g, b in item.anchors)
    return PALETTE_ANCHOR_TEMPLATE.format(label=item.label, anchors=anchors)
