"""art_check_calc：透明边、覆盖率、颜色数、对称、孤立像素、描边。"""

from common.constant.canvas_size import get_canvas_spec
from server.calc import art_check_calc, compact_art_calc
from tests.art_factory import compact_square

SPEC_32 = get_canvas_spec(32)


def _art(**kwargs):
    return compact_art_calc.to_standard_art(compact_square(**kwargs))


def _item(report, rule):
    return next(item for item in report.items if item.rule == rule)


def test_centered_square_passes_all_hard_rules():
    report = art_check_calc.check_art(_art(), spec=SPEC_32, symmetry="mirror_x", outline="dark")
    assert report.passed and report.problems == []
    assert _item(report, "symmetry").passed
    assert _item(report, "outline").passed


def test_margin_violation_lists_coordinates():
    report = art_check_calc.check_art(_art(start=0, end=10), spec=SPEC_32)
    assert not report.passed
    margin = _item(report, "margin")
    assert not margin.passed and margin.detail["count"] == 19
    assert "(0,0)" in margin.message and " 等" in margin.message


def test_coverage_bounds():
    tiny = art_check_calc.check_art(_art(start=15, end=16), spec=SPEC_32)
    assert not _item(tiny, "coverage").passed
    huge = art_check_calc.check_art(_art(start=1, end=31), spec=SPEC_32)
    assert not _item(huge, "coverage").passed


def test_color_count_limit():
    art = _art()
    for index, pixel in enumerate(art["pixels"]):
        pixel["rgba"] = [index % 256, 0, 0, 255]
    report = art_check_calc.check_art(art, spec=SPEC_32)
    assert not _item(report, "colors").passed


def test_asymmetric_shape_fails_symmetry():
    art = _art(start=4, end=14)
    report = art_check_calc.check_art(art, spec=SPEC_32, symmetry="mirror_x")
    assert not _item(report, "symmetry").passed
    rotational = art_check_calc.check_art(_art(), spec=SPEC_32, symmetry="rotational")
    assert _item(rotational, "symmetry").passed


def test_isolated_pixels_and_unused_palette_are_hints():
    art = _art()
    art["pixels"].append({"x": 3, "y": 3, "rgba": [255, 0, 0, 255]})
    report = art_check_calc.check_art(art, spec=SPEC_32, unused_palette_keys=["z"])
    isolated = _item(report, "isolated")
    assert isolated.level == art_check_calc.HINT and isolated.detail["count"] == 1
    assert _item(report, "unused_palette").level == art_check_calc.HINT


def test_isolated_check_disabled_for_size_8():
    art = compact_art_calc.to_standard_art(compact_square(size=8, start=2, end=6))
    report = art_check_calc.check_art(art, spec=get_canvas_spec(8))
    assert all(item.rule != "isolated" for item in report.items)
