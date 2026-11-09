"""compact_art_calc：校验、有限修复、转换、命名规范化、手改像素校验。"""

import json

from server.calc import compact_art_calc
from tests.art_factory import compact_square, compact_text


def _parse(text: str, **kwargs):
    params = {"size": 32, "max_colors": 16}
    params.update(kwargs)
    return compact_art_calc.parse_compact_art(text, **params)


def test_valid_art_parses_and_converts():
    result = _parse(compact_text())
    assert result.ok and not result.problems
    art = result.standard_art
    assert art["width"] == 32 and len(art["pixels"]) == 100
    assert {"x": 11, "y": 11, "rgba": [30, 40, 80, 255]} in art["pixels"]
    assert all(pixel["rgba"][3] > 0 for pixel in art["pixels"])


def test_row_length_off_by_two_is_repaired_with_warning():
    data = compact_square()
    data["rows"][3] = data["rows"][3] + ".."
    data["rows"][4] = data["rows"][4][:-1]
    result = _parse(json.dumps(data))
    assert result.ok
    assert len(result.warnings) == 2
    assert all(len(row) == 32 for row in result.compact["rows"])


def test_long_row_trims_dots_before_truncating():
    assert compact_art_calc._fix_row_length("..ab..", 4) == "..ab"
    assert compact_art_calc._fix_row_length(".abcd", 4) == "abcd"
    assert compact_art_calc._fix_row_length("abcdef", 4) == "abcd"


def test_row_length_off_by_more_than_two_fails():
    data = compact_square()
    data["rows"][5] = data["rows"][5][:27]
    result = _parse(json.dumps(data))
    assert not result.ok
    assert result.problems == ["第 6 行（y=5）长度 27，应为 32。"]


def test_row_count_repair_and_failure():
    data = compact_square()
    data["rows"] = data["rows"][:30]
    assert _parse(json.dumps(data)).ok
    data["rows"] = data["rows"][:20]
    result = _parse(json.dumps(data))
    assert not result.ok and "共 20 行" in result.problems[0]


def test_wrong_size_and_palette_problems():
    data = compact_square()
    data["width"] = 16
    data["palette"]["."] = [0, 0, 0, 255]
    data["palette"]["c"] = [0, 0, 300, 255]
    result = _parse(json.dumps(data))
    assert not result.ok
    assert len(result.problems) == 3


def test_too_many_colors_fails():
    data = compact_square()
    for index, char in enumerate("cdefghijklmnopq"):
        data["palette"][char] = [index, index, index, 255]
    result = _parse(json.dumps(data))
    assert not result.ok and "超过上限 16" in result.problems[0]


def test_unknown_char_in_rows():
    data = compact_square()
    data["rows"][15] = data["rows"][15][:15] + "z" + data["rows"][15][16:]
    result = _parse(json.dumps(data))
    assert not result.ok and "「z」" in result.problems[0]


def test_truncated_empty_and_invalid_json():
    assert "截断" in _parse(compact_text(), finish_reason="length").problems[0]
    assert "为空" in _parse("").problems[0]
    assert "不是合法的 json" in _parse("{oops").problems[0]
    assert "缺少字段" in _parse("{}").problems[0]


def test_truncated_by_thinking_asks_to_think_less():
    problem = _parse(compact_text(), finish_reason="length", reasoning_tokens=3900).problems[0]
    assert "思考用了 3900 token" in problem and "合并相近颜色" not in problem


def test_code_fence_is_stripped():
    result = _parse("```json\n" + compact_text() + "\n```")
    assert result.ok and any("代码块" in warning for warning in result.warnings)


def test_unused_palette_keys_reported():
    data = compact_square()
    data["palette"]["z"] = [1, 2, 3, 255]
    result = _parse(json.dumps(data))
    assert result.ok and result.unused_palette_keys == ["z"]


def test_name_normalization_and_duplicates():
    name, warning = compact_art_calc.normalize_particle_name("Frost Shard!")
    assert name == "frost_shard" and warning == "名称「Frost Shard!」已规范化为「frost_shard」"
    name, warning = compact_art_calc.normalize_particle_name("frost", {"frost", "frost_2"})
    assert name == "frost_3" and "重名" in warning
    assert compact_art_calc.normalize_particle_name("", fallback_name="fallback")[0] == "fallback"


def test_validate_standard_art():
    good = {"name": "x", "width": 8, "height": 8, "pixels": [{"x": 1, "y": 1, "rgba": [1, 2, 3, 255]}]}
    assert compact_art_calc.validate_standard_art(good, size=8) == []
    assert compact_art_calc.validate_standard_art(good, size=16) == ["尺寸必须是 16×16"]
    bad = {**good, "pixels": [{"x": 9, "y": 1, "rgba": [1, 2, 3]}, {"x": 1, "y": 1, "rgba": [1, 2, 3, 4]}]}
    assert len(compact_art_calc.validate_standard_art(bad, size=8)) == 2
