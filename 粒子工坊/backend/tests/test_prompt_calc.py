"""prompt_calc：首轮提示词、风格倾向、重试消息、尺寸冲突。"""

from common.constant.prompt_template import AUTO_TEXT
from server.calc import prompt_calc

OPTIONS = {"size": 32, "category": "glow", "palette": "cold_blue", "outline": "dark", "symmetry": "none", "variants": 2}


def test_build_prompt_contains_constraints():
    bundle = prompt_calc.build_prompt("一枚冰霜碎片", OPTIONS)
    assert "json" in bundle.system
    assert "尺寸：32×32" in bundle.user
    assert "四周 1px 内不得有像素" in bundle.user
    assert "颜色上限：16" in bundle.user
    assert "(24,40,82)" in bundle.user and "(214,240,255)" in bundle.user
    assert bundle.user.rstrip().endswith("一枚冰霜碎片")
    assert bundle.notes == []


def test_auto_options_render_as_model_decides():
    bundle = prompt_calc.build_prompt("火花", {**OPTIONS, "category": "auto", "palette": "auto"})
    assert bundle.user.count(AUTO_TEXT) == 2


def test_size_8_has_no_margin():
    bundle = prompt_calc.build_prompt("火花", {**OPTIONS, "size": 8})
    assert "8×8 可以画满" in bundle.user


def test_size_conflict_is_noted_and_buttons_win():
    bundle = prompt_calc.build_prompt("画一个 16x16 的火花", OPTIONS)
    assert "尺寸：32×32" in bundle.user
    assert len(bundle.notes) == 1 and "16x16" in bundle.notes[0]


def test_style_hint_appended():
    text = prompt_calc.apply_style_hint("用户消息", "偏简洁")
    assert text.endswith("偏简洁") and "【风格倾向】" in text
    assert prompt_calc.apply_style_hint("用户消息", "") == "用户消息"


def test_retry_message_puts_designer_feedback_first():
    message = prompt_calc.build_retry_message(["第 5 行长度 30，应为 32"], "整体再暗一档")
    lines = message.splitlines()
    assert lines[1].startswith("1. 设计者意见（优先）：整体再暗一档")
    assert lines[2].startswith("2. 第 5 行")
    assert lines[-1] == "请输出修正后的完整 json。"
