"""color_stat_calc：颜色计数、排序、首次出现、半透明统计。"""

from server.calc import color_stat_calc

RED = (255, 0, 0, 255)
BLUE = (0, 0, 255, 128)
CLEAR = (0, 0, 0, 0)


def test_palette_sorted_by_count_then_first_seen():
    grid = [[BLUE, RED, RED], [CLEAR, RED, BLUE]]
    palette = color_stat_calc.build_palette(grid, min_alpha=1)
    assert [entry.rgba for entry in palette] == [RED, BLUE]
    assert palette[0].count == 3 and palette[0].first_index == 1
    assert palette[1].hex == "#0000FF80"


def test_min_alpha_zero_includes_transparent():
    grid = [[CLEAR, RED]]
    assert len(color_stat_calc.build_palette(grid, min_alpha=0)) == 2
    assert len(color_stat_calc.build_palette(grid, min_alpha=1)) == 1


def test_semi_transparent_count():
    grid = [[BLUE, RED, CLEAR, BLUE]]
    assert color_stat_calc.count_semi_transparent(grid, min_alpha=1) == 2
