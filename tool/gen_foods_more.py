#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""农夫乐事风格 · 第二批 16×16 贴图（面点 / 卤味 / 河鲜 / 异域 / 下界末地 / 创意）。

复用 gen_foods.py 的材质系统、三层渐变着色与描边管线，只新增「器型原型」：
包、饼、饺、卷、串、片、块糕、挞、杯、叶包、酿菜、粥饭……
每道菜 = 一个原型 + 一套配色 + 点缀，保证同一风格下彼此可区分。

用法：
    python gen_foods_more.py --group 面点
    python gen_foods_more.py --preview
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen_foods as gf  # noqa: E402
from gen_foods import (  # noqa: E402
    H,
    MAT,
    W,
    blk,
    bowl,
    ell,
    hline,
    outline,
    plate,
    plate_wide,
    pot,
    put,
    row,
    shade,
    soup_bowl,
    to_art,
    vline,
)

# ---------------------------------------------------------------------------
# 追加材质
# ---------------------------------------------------------------------------
NEW_MAT = {
    # 面点
    "dough": (244, 224, 188),
    "dough_d": (216, 188, 144),
    "dough_g": (234, 200, 138),
    "batter": (240, 226, 182),
    "crust": (208, 148, 78),
    "crust_d": (166, 108, 56),
    "fried": (226, 168, 82),
    "fried_d": (188, 128, 52),
    "oil": (250, 216, 142),
    "sugar": (252, 246, 226),
    "sugar_b": (168, 92, 42),
    "sweet_bean": (122, 64, 54),
    "sweet_bean_l": (156, 88, 72),
    "pumpkin": (240, 158, 56),
    "mugwort": (98, 146, 68),
    "glutinous": (250, 244, 232),
    "osmanthus": (246, 198, 82),
    "sesame_b": (236, 228, 212),
    "chive_egg": (172, 200, 96),
    "pork_fill": (200, 122, 96),
    "shepherd": (112, 162, 76),
    # 卤味腌腊
    "braise": (124, 64, 42),
    "braise_l": (170, 98, 62),
    "braise_meat": (156, 78, 56),
    "braise_skin": (182, 108, 74),
    "egg_braised": (224, 198, 158),
    "tofu_braised": (172, 124, 78),
    "peanut": (218, 172, 116),
    "garlic_p": (240, 238, 216),
    "radish_p": (238, 224, 168),
    "xuelihong": (122, 120, 72),
    "pepper_p": (200, 74, 52),
    "kelp_knot": (64, 118, 86),
    "bacon_fat": (238, 214, 178),
    # 河鲜
    "fish_white": (244, 242, 234),
    "fish_skin": (152, 172, 182),
    "scallop": (240, 230, 212),
    "scallop_sh": (214, 176, 146),
    "crab_roe": (240, 150, 52),
    "crab_meat": (242, 238, 222),
    "squid": (238, 228, 220),
    "cuttle": (210, 198, 210),
    "roe_pink": (242, 152, 142),
    "clam_meat": (234, 198, 170),
    "fishball": (242, 238, 228),
    "shrimp_paste": (246, 170, 152),
    # 西式 / 地中海
    "cheese": (250, 208, 96),
    "cheese_d": (226, 172, 66),
    "butter": (252, 228, 152),
    "cream": (252, 244, 226),
    "tomato": (218, 72, 54),
    "olive": (88, 98, 60),
    "couscous": (240, 214, 142),
    "asparagus": (142, 174, 86),
    "bell": (228, 96, 64),
    "onion": (234, 224, 202),
    "herb": (88, 142, 78),
    "lamb": (188, 110, 96),
    "rabbit": (218, 168, 148),
    "trout": (240, 188, 152),
    "lemon": (246, 222, 90),
    "pastry": (230, 192, 134),
    "bean_stew": (190, 148, 98),
    "gravy": (142, 88, 54),
    # 东南亚
    "coconut": (252, 248, 238),
    "curry": (240, 178, 60),
    "lemongrass": (198, 216, 126),
    "pineapple": (246, 198, 72),
    "banana_leaf": (86, 140, 66),
    "banana_leaf_d": (58, 104, 52),
    "papaya": (208, 224, 144),
    "tamarind": (178, 112, 62),
    "rice_grain": (248, 244, 230),
    # 荒漠
    "cumin": (178, 134, 76),
    "naan": (228, 188, 122),
    "raisin": (110, 64, 48),
    "camel": (178, 114, 86),
    "dry_fruit": (198, 94, 66),
    "chickpea": (234, 210, 150),
    # 下界
    "crimson": (188, 52, 58),
    "crimson_d": (140, 34, 44),
    "warped": (58, 160, 150),
    "warped_d": (36, 112, 112),
    "lava": (242, 124, 36),
    "sulfur": (230, 214, 96),
    "nether_meat": (152, 48, 40),
    "nether_rot": (106, 64, 86),
    # 末地
    "chorus": (188, 148, 208),
    "chorus_d": (142, 100, 168),
    "phantom": (200, 206, 188),
    "end_stone": (234, 232, 202),
    "mycelium": (170, 160, 198),
    "starlight": (230, 210, 250),
    "void": (76, 62, 98),
    # 水果
    "banana": (244, 226, 132),
    "pear": (240, 232, 196),
    # 器皿扩充 —— 珐琅白锅 / 铜锅 / 漆器 / 玻璃杯 / 青瓷盘 / 椰壳
    "enamel": (236, 240, 244),
    "enamel_rim": (92, 138, 192),
    "copper": (198, 122, 66),
    "copper_rim": (246, 188, 112),
    "lacquer": (92, 46, 40),
    "lacquer_rim": (208, 148, 104),
    "glass_blue": (200, 224, 240),
    "glass_pink": (248, 212, 226),
    "porcelain": (246, 244, 238),
    "porcelain_rim": (208, 202, 192),
    "plate_cel": (158, 188, 166),
    "plate_cel_in": (198, 222, 204),
    "plate_cel_rim": (114, 146, 126),
    "coconut_shell": (122, 84, 50),
}
MAT.update(NEW_MAT)

PLATES = (plate, plate_wide, bowl, pot, soup_bowl)


# ---------------------------------------------------------------------------
# 几何原语
# ---------------------------------------------------------------------------
def _seg_d(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def capsule(g, x0, y0, x1, y1, r, m):
    for y in range(H):
        for x in range(W):
            if _seg_d(x + 0.5, y + 0.5, x0, y0, x1, y1) <= r:
                put(g, x, y, m)


def rows_shape(g, table, m):
    for y, hw in table:
        row(g, y, hw, m)


def blob(g, cx, cy, rx, ry, m):
    ell(g, cx, cy, rx, ry, m)


def sprinkle(g, pts, m):
    for x, y in pts:
        put(g, x, y, m)


# ---------------------------------------------------------------------------
# 器型原型
# ---------------------------------------------------------------------------
def A_bun(g, skin="dough", dark="dough_d", pleat=True, bite=None, gloss=None, tall=True):
    """发面包子 / 青团 / 麻团 / 发糕（圆顶）。"""
    table = [(4, 2), (5, 4), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5), (11, 4)]
    if not tall:
        table = [(6, 3), (7, 5), (8, 5), (9, 5), (10, 5), (11, 4)]
    rows_shape(g, table, skin)
    row(g, table[-1][0], table[-1][1], dark)
    if pleat:
        put(g, 7, table[0][0] - 1, skin)
        put(g, 8, table[0][0] - 1, skin)
        for x, y in [(6, 4), (9, 4), (5, 5), (10, 5)]:
            put(g, x, y, dark)
    if bite:
        blk(g, 8, 9, 3, 2, bite)
        put(g, 9, 8, bite)
    if gloss:
        put(g, 5, 6, gloss)


def A_steamed_bun(g, skin="dough", top="pork_fill", dot=None):
    """开口包（豆沙包 / 素菜包）：顶上露一点馅。"""
    A_bun(g, skin=skin, dark="dough_d", pleat=False)
    blob(g, 7.5, 5.0, 2.2, 1.2, top)
    if dot:
        put(g, 7, 5, dot)
        put(g, 8, 4, dot)


def A_flower_roll(g, skin="dough", dark="dough_d", green="greens"):
    """葱油花卷：横放的卷，葱花层夹在中间，两端捏出卷头。"""
    capsule(g, 2.8, 8.6, 13.2, 8.6, 2.8, skin)
    hline(g, 3, 12, 9, dark)
    for x in range(3, 13):
        put(g, x, 8 if (x // 2) % 2 == 0 else 7, green)
    # 两端卷头
    put(g, 2, 7, dark)
    put(g, 2, 10, dark)
    put(g, 13, 7, dark)
    put(g, 13, 10, dark)


def A_panpie(g, skin="dough_g", crust="crust", fill="chive_egg", gloss="oil"):
    """馅饼：厚圆饼 + 焦斑 + 咬口露馅。"""
    ell(g, 7.5, 8.6, 6.3, 3.3, skin)
    ell(g, 7.5, 8.3, 5.4, 2.4, skin)
    for x, y in [(3, 7), (6, 6), (10, 7), (5, 9), (11, 5)]:
        put(g, x, y, crust)
    blk(g, 9, 9, 3, 2, fill)
    put(g, 10, 8, fill)
    put(g, 4, 6, gloss)


def A_flatcake(g, dough="dough", char="crust", thick=3.2, fold=None, dots=()):
    """薄饼 / 馕 / 煎饼：扁平圆盘 + 焦斑。"""
    ell(g, 7.5, 8.8, 6.5, thick, dough)
    for x, y in [(4, 7), (7, 6), (10, 8), (5, 9), (11, 6), (3, 9), (9, 10)]:
        if (x, y) in g:
            put(g, x, y, char)
    if fold:
        hline(g, 2, 13, 9, fold)
    for x, y in dots:
        put(g, x, y, "sesame_b")


def A_dumpling(g, skin="dough", dark="dough_d", hint=None, rowy=7):
    """饺子 / 蒸饺：鼓肚 + 顶端捏褶。"""
    ell(g, 7.5, 9.2, 5.6, 2.7, skin)
    hline(g, 3, 12, rowy, dark)
    for x in (3, 5, 7, 9, 11):
        put(g, x, rowy - 1, dark)
        put(g, x, rowy, skin)
    if hint:
        put(g, 7, 10, hint)
        put(g, 8, 10, hint)


def A_wonton(g, broth="broth_pale", skin="dough", dark="dough_d", green="greens"):
    """馄饨（汤）：碗里漂三只。"""
    soup_bowl(g)
    for x, y in [(3, 8), (6, 7), (9, 8)]:
        blk(g, x, y, 3, 2, skin)
        put(g, x + 1, y + 1, dark)
        put(g, x + 2, y, green)


def A_tangyuan(g, skin="glutinous", broth="broth_pale", dot="sesame_b"):
    """汤圆：碗里滚三颗。"""
    soup_bowl(g)
    for x, y in [(3, 8), (6, 9), (9, 8)]:
        blk(g, x, y, 2, 2, skin)
    put(g, 3, 9, dot)
    put(g, 10, 8, dot)


def A_siumai(g, skin="dough", fill="pork_fill", roe="crab_roe"):
    """烧麦：小圆身 + 开口罩褶 + 顶部橙黄。"""
    blob(g, 7.5, 9.4, 4.6, 2.2, skin)
    for y, hw in [(5, 4), (6, 4), (7, 4)]:
        row(g, y, hw, skin)
    blob(g, 7.5, 5.8, 2.6, 1.4, fill)
    put(g, 7, 5, roe)
    put(g, 8, 6, roe)
    hline(g, 4, 11, 7, "dough_d")


def A_roll(g, wrapper="dough_g", char="crust", fill="greens", r=2.3):
    """春卷 / 卷饼：斜放圆柱 + 端头露馅。"""
    capsule(g, 3.2, 11.0, 11.4, 5.8, r, wrapper)
    for t in (0.32, 0.58, 0.84):
        x = int(3.2 + t * 8.2)
        y = int(11.0 - t * 5.2)
        put(g, x, y - 1, char)
        put(g, x, y + 1, char)
    blk(g, 2, 10, 2, 2, fill)


def A_block(g, body="sugar_b", band=None, top=None, x0=3, y0=6, w=10, h=6):
    """方块糕 / 冻：圆角块 + 分层。"""
    blk(g, x0, y0, w, h, body)
    for x, y in [(x0, y0), (x0 + w - 1, y0), (x0, y0 + h - 1), (x0 + w - 1, y0 + h - 1)]:
        g.pop((x, y), None)
    if top:
        hline(g, x0, x0 + w - 1, y0, top)
    if band:
        hline(g, x0, x0 + w - 1, y0 + h // 2, band)


def A_tart(g, shell="pastry", rim="crust_d", fill="gravy", lattice=False):
    """派 / 挞：酥皮圈 + 馅。"""
    ell(g, 7.5, 9.2, 6.3, 3.4, shell)
    ell(g, 7.5, 9.0, 4.8, 2.4, fill)
    if lattice:
        for x in (5, 8, 11):
            vline(g, x, 7, 11, rim)


def A_cup(g, layers, glass="bowl_white"):
    """杯装甜品：玻璃杯 + 分层。"""
    for y, hw in [(4, 4), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5), (11, 4), (12, 3)]:
        row(g, y, hw, glass)
    for y0, y1, m in layers:
        for y in range(y0, y1 + 1):
            row(g, y, 4, m)


def A_slices(g, meat="braise_meat", fat="braise_skin", n=4, base="braise", plate_fn=plate, holes=None):
    """卤味片 / 酱肉片：斜叠的厚片；holes 可给藕片/糕点打孔。"""
    plate_fn(g)
    ell(g, 7.5, 9.8, 5.2, 2.4, base)
    pts = [(2, 8), (5, 6), (8, 7), (10, 5)][:n]
    for x, y in pts:
        blk(g, x, y, 4, 3, meat)
        hline(g, x, x + 3, y, fat)
        if holes:
            put(g, x + 1, y + 1, holes)
            put(g, x + 2, y + 2, holes)


def A_chunks(g, meat="braise_meat", fat="braise_skin", base="braise", pts=None):
    """卤块 / 腊块：不规则肉块。"""
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.4, base)
    for x, y in (pts or [(2, 7), (6, 5), (9, 8), (4, 9)]):
        blk(g, x, y, 3, 2, meat)
        put(g, x, y, fat)


def A_jerky(g, meat="nether_meat", fat="braise_skin", n=3):
    """风干肉 / 肉脯：木砧板上几条斜肉干。"""
    ell(g, 7.5, 12.2, 6.6, 2.3, "plate")
    hline(g, 4, 11, 14, "plate_rim")
    for x in (4, 7, 10):
        put(g, x, 13, "grain")
    for i, (x, y) in enumerate([(3, 5), (7, 4), (5, 8)][:n]):
        capsule(g, x, y + 4, x + 5, y, 1.2, meat)
        put(g, x + 2, y + 2, fat)


def A_skewer(g, chunks, stick="bamboo", base=None):
    """烤串：斜竹签 + 三块料。"""
    if base:
        plate(g)
        ell(g, 7.5, 10.0, 5.0, 2.2, base)
    for i in range(12):
        put(g, 3 + i, 13 - i, stick)
    for (x, y, m) in chunks:
        blk(g, x, y, 3, 3, m)


def A_leaf(g, leaf="banana_leaf", spine="banana_leaf_d", content="pork_red"):
    """叶包（荷叶 / 芭蕉叶）：大叶片 + 中间露出的内容。"""
    ell(g, 7.5, 8.8, 6.4, 3.8, leaf)
    hline(g, 2, 13, 9, spine)
    blk(g, 4, 7, 8, 3, content)


def A_stuffed(g, veg="bell", fill="pork", shape="round"):
    """酿菜：蔬菜外壳 + 塞肉。"""
    if shape == "round":
        blob(g, 7.5, 8.6, 4.6, 3.4, veg)
    else:
        blk(g, 3, 6, 10, 5, veg)
    blob(g, 7.5, 8.6, 2.4, 1.8, fill)


def A_rice(g, grain="rice_grain", tops=(), bowl_fn=bowl):
    """碗装饭：小山 + 浇头。"""
    bowl_fn(g)
    ell(g, 7.5, 8.2, 5.2, 2.8, grain)
    for x, y, m in tops:
        blk(g, x, y, 2, 2, m)


def A_porridge(g, body="glutinous", sheen="cream", dots=()):
    """粥 / 羹：碗 + 稠面 + 反光。"""
    bowl(g)
    ell(g, 7.5, 8.8, 5.0, 2.2, body)
    hline(g, 5, 9, 7, sheen)
    for x, y, m in dots:
        put(g, x, y, m)


def A_salad(g, base="greens", shreds=(), plate_fn=plate):
    """凉拌：盘里堆丝。"""
    plate_fn(g)
    ell(g, 7.5, 9.4, 5.4, 2.8, base)
    for x, y, w, m in shreds:
        hline(g, x, x + w, y, m)


def A_fish_whole(g, skin="fish_skin", belly="fish_white", fin=None, garnish=None):
    """整鱼（清蒸 / 香煎）：鱼身 + 尾鳍。"""
    plate_wide(g)
    ell(g, 8.6, 9.0, 4.6, 2.6, skin)
    ell(g, 8.6, 9.6, 4.0, 1.6, belly)
    blk(g, 1, 8, 2, 3, skin)
    put(g, 1, 7, skin)
    put(g, 1, 11, skin)
    put(g, 7, 8, "bean")
    if fin:
        hline(g, 6, 11, 7, fin)
    for x, y, m in garnish or ():
        put(g, x, y, m)


def A_casserole(g, body="pot", rim="pot_rim", broth="broth", items=()):
    """煲类：锅 + 汤 + 料。"""
    pot(g, body, rim)
    ell(g, 7.5, 7.2, 5.0, 2.2, broth)
    for x, y, m in items:
        blk(g, x, y, 2, 2, m)


def plate_celadon(g):
    """青瓷盘：青绿釉面，和木盘/白盘拉开区分。"""
    ell(g, 7.5, 12.4, 6.7, 2.5, "plate_cel")
    hline(g, 5, 10, 14, "plate_cel_rim")
    ell(g, 7.5, 12.0, 5.3, 1.7, "plate_cel_in")


def bowl_porcelain(g):
    """白瓷碗：奶白瓷身 + 浅灰沿，甜品/米饭专用。"""
    for y, hw in [(9, 6), (10, 6), (11, 5), (12, 5), (13, 4), (14, 3)]:
        row(g, y, hw, "porcelain")
    row(g, 9, 6, "porcelain_rim")
    blk(g, 6, 15, 4, 1, "porcelain_rim")


ARCH = {
    "bun": A_bun,
    "steamed_bun": A_steamed_bun,
    "flower_roll": A_flower_roll,
    "panpie": A_panpie,
    "flatcake": A_flatcake,
    "dumpling": A_dumpling,
    "wonton": A_wonton,
    "tangyuan": A_tangyuan,
    "siumai": A_siumai,
    "roll": A_roll,
    "block": A_block,
    "tart": A_tart,
    "cup": A_cup,
    "slices": A_slices,
    "chunks": A_chunks,
    "jerky": A_jerky,
    "skewer": A_skewer,
    "leaf": A_leaf,
    "stuffed": A_stuffed,
    "rice": A_rice,
    "porridge": A_porridge,
    "salad": A_salad,
    "fish": A_fish_whole,
    "casserole": A_casserole,
}


# ---------------------------------------------------------------------------
# 第二批原型：通用盘装配 + 小球 / 结 / 条 / 蒜瓣
# ---------------------------------------------------------------------------
def A_plate(g, base=None, items=(), plate_fn=plate):
    """通用盘中菜：底盘 + 逐块摆放（块坐标由菜品表指定）。"""
    plate_fn(g)
    if base:
        ell(g, 7.5, 9.8, 5.2, 2.4, base)
    for x, y, w, h, m in items:
        blk(g, x, y, w, h, m)


def A_balls(g, m="egg_braised", edge="braise", n=4, base="braise", plate_fn=plate):
    """卤蛋 / 丸子：几颗小圆球。"""
    plate_fn(g)
    if base:
        ell(g, 7.5, 9.8, 5.0, 2.3, base)
    for x, y in [(2, 7), (5, 5), (8, 7), (10, 5)][:n]:
        blk(g, x, y, 2, 2, m)
        put(g, x, y, edge)


def A_knots(g, m="kelp_knot", base="braise"):
    """海带结：方块打结。"""
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.3, base)
    for x, y in [(2, 7), (6, 5), (9, 8)]:
        blk(g, x, y, 3, 2, m)
        put(g, x + 1, y, "braise")


def A_strips(g, m="radish_p", m2="radish", base=None, pts=None, vertical=True):
    """腌菜条：竖条堆叠。"""
    plate(g)
    if base:
        ell(g, 7.5, 9.8, 5.0, 2.3, base)
    for x, y, n in (pts or [(2, 6, 4), (5, 4, 4), (8, 7, 3), (10, 5, 4)]):
        vline(g, x, y, y + n - 1, m)
        put(g, x + 1, y + 1, m2)


def A_bulbs(g, m="garlic_p", dark="dough_d"):
    """糖蒜：蒜瓣。"""
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.3, "broth_pale")
    for x, y in [(3, 7), (6, 5), (9, 8)]:
        blk(g, x, y, 2, 3, m)
        put(g, x, y, dark)
        put(g, x + 1, y + 2, dark)


def A_scallop(g, shell="scallop_sh", meat="scallop"):
    """扇贝：扇形壳 + 贝肉。"""
    plate(g)
    for x, y in [(2, 7), (6, 5), (9, 8)]:
        blk(g, x, y, 3, 2, shell)
        put(g, x + 1, y, meat)
        put(g, x, y + 1, shell)


def A_soup(g, broth="broth", items=(), sheen=None):
    """清汤：汤碗 + 汤面浮料。"""
    soup_bowl(g)
    for x, y, w, h, m in items:
        blk(g, x, y, w, h, m)
    if sheen:
        hline(g, 5, 9, 10, sheen)


def A_naan_meat(g):
    """馕夹肉：上下两层面饼夹肉，肉边露出。"""
    ell(g, 7.5, 9.8, 6.4, 2.6, "naan")
    blk(g, 2, 7, 12, 2, "lamb")
    ell(g, 7.5, 7.2, 5.4, 1.8, "naan")
    hline(g, 3, 12, 6, "crust")


ARCH.update(
    {
        "plate": A_plate,
        "balls": A_balls,
        "knots": A_knots,
        "strips": A_strips,
        "bulbs": A_bulbs,
        "scallop": A_scallop,
        "soup": A_soup,
        "naan_meat": A_naan_meat,
    }
)


# ---------------------------------------------------------------------------
# 菜品表： (分组, 菜名, 原型, 参数)
# ---------------------------------------------------------------------------
SPEC: list[tuple[str, str, str, dict]] = []


def G(group):
    def add(name, arch, **kw):
        SPEC.append((group, name, arch, kw))

    return add


# ---------------- 面食、点心、小吃 ----------------
m = G("面点")
m("韭菜鸡蛋馅饼", "panpie", fill="chive_egg")
m("萝卜丝饼", "panpie", skin="dough", crust="crust_d", fill="radish_p")
m("鲜肉锅盔", "panpie", skin="crust", crust="crust_d", fill="pork_fill")
m("葱油花卷", "flower_roll")
m("荠菜馄饨", "wonton", green="shepherd")
m("鲜肉小汤包", "bun", bite="pork_fill", gloss="oil")
m("南瓜饼", "panpie", skin="pumpkin", crust="crust_d", fill="sweet_bean_l")
m("艾草青团", "bun", skin="mugwort", dark="mugwort", pleat=False, gloss="herb")
m("芝麻汤圆", "tangyuan")
m("鲜肉烧麦", "siumai")
m("荠菜春卷", "roll", fill="shepherd")
m("红糖发糕", "bun", skin="sugar_b", dark="sweet_bean", gloss="sugar")
m("酥皮豆沙饼", "panpie", skin="pastry", crust="crust_d", fill="sweet_bean")
m("菜团子", "bun", skin="dough_g", dark="shepherd", bite="shepherd")
m("杂粮煎饼", "flatcake", dough="batter", thick=2.4, fold="dough_d")
m("虾仁蒸饺", "dumpling", hint="shrimp")
m("香菇素菜包", "steamed_bun", top="mushroom_e", dot="greens")
m("桂花糯米藕", "slices", meat="lotus", fat="glutinous", n=4, holes="braise")
m("麻团", "bun", skin="fried", dark="fried_d", pleat=False, tall=False)
m("炸糖糕", "bun", skin="fried", dark="fried_d", pleat=False, tall=False, gloss="sugar")

# ---------------- 卤味、腌腊、风干 ----------------
m = G("卤味")
m("卤猪耳", "slices", meat="braise_skin", fat="pork_pale")
m("卤豆干", "slices", meat="tofu_braised", fat="tofu")
m("卤藕片", "slices", meat="lotus", fat="braise_l")
m("卤鹌鹑蛋", "balls", m="egg_braised", edge="braise_l")
m("风干腊鱼", "fish", skin="cured", belly="fish_gold", fin="crust")
m("腊鸭块", "chunks", meat="cured", fat="braise_skin")
m("酱牛肉片", "slices", meat="braise_meat", fat="braise_l")
m("腌萝卜条", "strips", m="radish_p", m2="radish")
m("腌雪里蕻", "strips", m="xuelihong", m2="pickle_dark")
m("泡椒木耳", "plate", base="chili_oil",
  items=[(2, 7, 3, 2, "fungus"), (6, 5, 2, 2, "fungus"), (9, 8, 3, 2, "fungus"),
         (4, 5, 2, 2, "pepper_p"), (8, 6, 2, 2, "pepper_p")])
m("五香卤花生", "plate", base="braise",
  items=[(2, 7, 2, 2, "peanut"), (5, 5, 2, 2, "peanut"), (8, 7, 2, 2, "peanut"),
         (10, 5, 2, 2, "peanut"), (4, 9, 2, 2, "peanut")])
m("卤海带结", "knots")
m("风干鸡", "chunks", meat="chicken_br", fat="cured",
  pts=[(2, 6), (6, 5), (9, 7), (4, 9)])
m("酱鸭", "chunks", meat="soy_chicken", fat="braise_skin",
  pts=[(2, 6), (6, 4), (9, 7), (4, 9)])
m("糖蒜", "bulbs")

# ---------------- 河鲜海味 ----------------
m = G("河鲜")
m("清蒸鲈鱼", "fish", skin="fish_skin", belly="fish_white",
  garnish=[(4, 6, "ginger"), (9, 6, "ginger"), (6, 5, "celery")])
m("香辣花蛤煲", "casserole", broth="chili_oil",
  items=[(2, 6, "clam"), (6, 5, "clam"), (9, 7, "clam"), (4, 8, "shrimp")])
m("虾滑羹", "porridge", body="shrimp_paste", sheen="cream",
  dots=[(4, 8, "greens"), (9, 7, "chili")])
m("葱油扇贝", "scallop")
m("墨鱼小炒", "plate", base="soy_light",
  items=[(2, 7, 3, 1, "cuttle"), (6, 5, 3, 1, "cuttle"), (9, 8, 3, 1, "cuttle"),
         (4, 9, 3, 1, "celery"), (8, 6, 2, 1, "chili")])
m("杂鱼锅", "casserole", body="lacquer", rim="lacquer_rim", broth="soy",
  items=[(2, 6, "fish_gold"), (6, 5, "fish_gold"), (9, 7, "fish_white")])
m("虾仁豆腐煲", "casserole", body="enamel", rim="enamel_rim", broth="broth_pale",
  items=[(2, 6, "tofu_white"), (6, 5, "shrimp"), (9, 7, "tofu_white")])
m("海带鱼丸锅", "casserole", body="pot_celadon", broth="broth",
  items=[(2, 6, "fishball"), (6, 5, "kelp"), (9, 7, "fishball")])
m("香煎鱿鱼须", "plate", base="soy",
  items=[(2, 7, 2, 3, "squid"), (6, 5, 2, 3, "squid"), (9, 8, 2, 3, "squid"),
         (4, 5, 2, 2, "chili")])
m("蟹肉豆腐羹", "porridge", body="crab_meat", sheen="cream",
  dots=[(4, 8, "crab_roe"), (9, 7, "celery")])
m("白灼蛏子", "plate", base="broth_pale",
  items=[(2, 7, 4, 2, "clam"), (7, 5, 4, 2, "clam"), (5, 9, 4, 1, "clam_sh"),
         (3, 5, 2, 2, "celery")])
m("酸菜鱼片煲", "casserole", body="copper", rim="copper_rim", broth="chili_oil",
  items=[(2, 6, "pickle"), (6, 5, "fish_white"), (9, 7, "fish_white")])
m("海菜丸子汤", "porridge", body="broth", sheen="cream",
  dots=[(4, 8, "kelp"), (9, 7, "fishball")])
m("椒盐小虾", "plate", base="soy_light",
  items=[(2, 7, 3, 2, "shrimp"), (6, 5, 3, 2, "shrimp"), (9, 8, 3, 2, "shrimp"),
         (4, 5, 2, 1, "chili"), (10, 5, 2, 1, "garlic")])
m("蟹黄蒸蛋", "porridge", body="egg", sheen="cream",
  dots=[(5, 8, "crab_roe"), (8, 7, "crab_roe"), (10, 9, "crab_roe")])

# ---------------- 西式 / 地中海 / 游牧 ----------------
m = G("西式")
m("香草羊肉卷", "roll", wrapper="pastry", char="crust_d", fill="lamb")
m("焗蘑菇虾仁", "tart", shell="cream", rim="cheese_d", fill="cheese",
  lattice=False)
m("奶油韭葱炖菜", "casserole", body="enamel", rim="enamel_rim", broth="cream",
  items=[(2, 6, "herb"), (6, 5, "cream"), (9, 7, "herb")])
m("香草番茄焗豆", "tart", shell="cream", rim="cheese_d", fill="bean_stew")
m("烤羊排配洋葱", "plate", base="gravy",
  items=[(2, 6, 4, 2, "lamb"), (7, 8, 4, 2, "lamb"), (4, 5, 2, 2, "bone"),
         (9, 5, 2, 2, "onion")])
m("芝士焗芦笋", "tart", shell="cream", rim="cheese", fill="asparagus")
m("洋葱牛肉派", "tart", shell="pastry", rim="crust_d", fill="gravy", lattice=True)
m("蒜香黄油虾", "plate", base="butter",
  items=[(2, 7, 3, 2, "shrimp"), (6, 5, 3, 2, "shrimp"), (9, 8, 3, 2, "shrimp"),
         (3, 5, 2, 1, "garlic"), (10, 5, 2, 1, "garlic")])
m("蔬菜古斯米", "rice", grain="couscous",
  tops=[(3, 6, "tomato"), (7, 5, "herb"), (9, 7, "olive")])
m("烟熏肉洋葱挞", "tart", shell="pastry", rim="crust_d", fill="onion")
m("柠檬香煎鳟鱼", "fish", skin="trout", belly="fish_white",
  garnish=[(4, 6, "lemon"), (9, 6, "herb"), (6, 5, "lemon")])
m("菠菜芝士卷", "roll", wrapper="pastry", char="crust_d", fill="greens")
m("烤彩椒肉糜", "stuffed", veg="bell", fill="pork")
m("香草炖兔肉", "casserole", body="pot_dark", broth="gravy",
  items=[(2, 6, "rabbit"), (6, 5, "herb"), (9, 7, "rabbit")])
m("橄榄肉丁煲", "casserole", body="pot_celadon", broth="gravy",
  items=[(2, 6, "olive"), (6, 5, "pork"), (9, 7, "olive")])

# ---------------- 东南亚 / 热带 ----------------
m = G("东南亚")
m("香茅烤鸡", "plate", base="curry",
  items=[(2, 6, 3, 2, "chicken_br"), (6, 8, 3, 2, "chicken_br"),
         (9, 5, 3, 2, "chicken_br"), (4, 5, 2, 1, "lemongrass")])
m("椰浆咖喱鱼", "casserole", body="copper", rim="copper_rim", broth="curry",
  items=[(2, 6, "fish_gold"), (6, 5, "coconut"), (9, 7, "fish_gold")])
m("酸辣虾汤", "porridge", body="chili_oil", sheen="oil",
  dots=[(4, 8, "shrimp"), (9, 7, "shrimp"), (6, 6, "lemongrass")])
m("菠萝炒肉", "plate", base="curry",
  items=[(2, 7, 3, 2, "pineapple"), (6, 5, 3, 2, "pork"), (9, 8, 3, 2, "pineapple"),
         (4, 5, 2, 1, "chili")])
m("芭蕉叶包烤肉", "leaf", content="pork_red")
m("椰香菌菇煲", "casserole", body="lacquer", rim="lacquer_rim", broth="coconut",
  items=[(2, 6, "mushroom"), (6, 5, "coconut"), (9, 7, "oyster")])
m("青木瓜沙拉", "salad", base="papaya",
  shreds=[(3, 6, 4, "greens"), (6, 8, 3, "chili"), (2, 9, 3, "peanut")])
m("香茅烤虾", "skewer", base="curry",
  chunks=[(4, 9, "shrimp"), (6, 7, "shrimp"), (8, 5, "shrimp")])
m("椰浆杂粮饭", "rice", grain="rice_grain",
  tops=[(3, 6, "coconut"), (8, 7, "coconut")])
m("酸辣笋汤", "porridge", body="chili_oil", sheen="oil",
  dots=[(4, 8, "bamboo"), (9, 7, "bamboo"), (6, 6, "chili")])

# ---------------- 荒漠 / 干草原 ----------------
m = G("荒漠")
m("孜然烤羊腰", "skewer", base="gravy",
  chunks=[(4, 9, "lamb"), (6, 7, "lamb"), (8, 5, "lamb")])
m("风干肉糜饭", "rice", grain="rice_grain",
  tops=[(3, 6, "nether_meat"), (7, 5, "pork_red"), (9, 7, "cumin")])
m("洋葱孜然炖牛肉", "casserole", body="copper", rim="copper_rim", broth="gravy",
  items=[(2, 6, "beef"), (6, 5, "onion"), (9, 7, "beef")])
m("烤杂粮馕夹肉", "naan_meat")
m("葡萄干肉饭", "rice", grain="rice_grain",
  tops=[(3, 6, "raisin"), (7, 5, "lamb"), (9, 7, "raisin")])
m("香草干豆炖肉", "casserole", broth="bean_stew",
  items=[(2, 6, "chickpea"), (6, 5, "pork"), (9, 7, "herb")])
m("烤驼肉串", "skewer", base="gravy",
  chunks=[(4, 9, "camel"), (6, 7, "camel"), (8, 5, "cumin")])
m("沙漠果干拼盘", "plate", base="gravy",
  items=[(2, 7, 3, 2, "dry_fruit"), (6, 5, 3, 2, "raisin"), (9, 8, 3, 2, "chickpea"),
         (4, 5, 2, 1, "cumin")])

# ---------------- 汤、羹、粥 ----------------
m = G("汤羹")
m("冬瓜海米汤", "soup", broth="broth_pale",
  items=[(3, 8, 2, 2, "melon"), (7, 7, 2, 2, "melon"), (10, 8, 1, 1, "shrimp")])
m("黄花菜菌汤", "soup", broth="broth",
  items=[(3, 7, 2, 2, "lily"), (7, 8, 2, 2, "mushroom"), (10, 7, 1, 2, "lily")])
m("丝瓜虾仁汤", "soup", broth="broth_pale",
  items=[(3, 7, 2, 2, "loofah"), (7, 8, 2, 2, "shrimp"), (10, 7, 1, 2, "loofah")])
m("白果小米粥", "porridge", body="couscous", sheen="cream",
  dots=[(4, 8, "ginkgo"), (8, 7, "ginkgo"), (10, 9, "ginkgo")])
m("青菜瘦肉粥", "porridge", body="rice_grain", sheen="cream",
  dots=[(4, 8, "greens"), (8, 7, "pork"), (10, 9, "greens")])
m("荷叶粥", "porridge", body="rice_grain", sheen="herb",
  dots=[(4, 8, "herb"), (9, 7, "herb")])
m("花生银耳羹", "porridge", body="cream", sheen="glutinous",
  dots=[(4, 8, "peanut"), (8, 7, "glutinous"), (10, 9, "peanut")])
m("雪梨百合羹", "porridge", body="cream", sheen="pear",
  dots=[(4, 8, "pear"), (9, 7, "glutinous"), (10, 9, "pear")])
m("紫菜虾丸汤", "soup", broth="broth",
  items=[(3, 7, 2, 2, "laver"), (7, 8, 2, 2, "fishball"), (10, 7, 1, 2, "laver")])
m("酸菜豆腐汤", "soup", broth="broth_pale",
  items=[(3, 7, 2, 2, "pickle"), (7, 8, 2, 2, "tofu_white"), (10, 7, 1, 2, "pickle")])
m("马蹄糖水", "soup", broth="broth",
  items=[(3, 8, 2, 2, "chest_w"), (7, 7, 2, 2, "chest_w"), (10, 8, 1, 1, "radish")])

# ---------------- 甜品、蜜饯、果食 ----------------
m = G("甜品")
m("桂花糖藕", "slices", meat="lotus", fat="sugar", holes="braise", plate_fn=plate_celadon)
m("陈皮山楂糕", "block", body="dry_fruit", top="sugar", h=5)
m("红枣银耳冻", "cup", glass="glass_blue", layers=[(5, 7, "dry_fruit"), (8, 9, "glutinous"), (10, 11, "pear")])
m("芒果糯米饭", "rice", grain="glutinous", bowl_fn=bowl_porcelain,
  tops=[(3, 6, "banana"), (7, 5, "banana"), (9, 7, "coconut")])
m("椰子冻", "cup", glass="coconut_shell", layers=[(5, 7, "coconut"), (8, 11, "coconut")])
m("话梅渍浆果", "cup", glass="glass_pink", layers=[(5, 7, "raisin"), (8, 9, "dry_fruit"), (10, 11, "chorus")])
m("蜜渍雪梨", "cup", glass="porcelain", layers=[(5, 7, "pear"), (8, 11, "broth")])
m("芝麻核桃糕", "block", body="peanut", band="crust_d", top="sesame_b", h=5)
m("香蕉酥饼", "tart", shell="pastry", rim="crust_d", fill="banana")
m("荔枝果冻", "cup", glass="glass_pink", layers=[(5, 7, "radish"), (8, 11, "chorus")])

# ---------------- 下界 ----------------
m = G("下界")
m("绯红菌腊味煲", "casserole", broth="crimson", body="pot_dark",
  items=[(2, 6, "nether_meat"), (6, 5, "crimson"), (9, 7, "nether_meat")])
m("扭曲菌菇肉丸汤", "soup", broth="warped",
  items=[(3, 7, 2, 2, "fishball"), (7, 8, 2, 2, "warped"), (10, 7, 1, 2, "fishball")])
m("岩浆熏肉干", "jerky", meat="nether_meat", fat="lava")
m("下界菌菇馅饼", "panpie", skin="crust", crust="crust_d", fill="crimson")
m("绯红菌海鲜煲", "casserole", broth="crimson", body="pot_dark",
  items=[(2, 6, "shrimp"), (6, 5, "crimson"), (9, 7, "clam")])
m("硫磺熏豆干", "slices", meat="tofu_braised", fat="sulfur")
m("扭曲菌菇芝士焗菜", "tart", shell="cream", rim="cheese_d", fill="cheese")
m("下界果干肉卷", "roll", wrapper="crust", char="crust_d", fill="nether_meat", r=2.2)

# ---------------- 末地 ----------------
m = G("末地")
m("颂果糯米羹", "porridge", body="chorus", sheen="starlight",
  dots=[(4, 8, "chorus_d"), (9, 7, "starlight")])
m("幻翼肉脯", "jerky", meat="phantom", fat="mycelium")
m("颂果果冻", "cup", glass="glass_blue", layers=[(5, 7, "chorus"), (8, 11, "starlight")])
m("幻翼菌菇卷", "roll", wrapper="pastry", char="crust_d", fill="mycelium")
m("星光颂果糕", "block", body="chorus", band="starlight", top="end_stone", h=5)
m("末地凉拌菌丝", "salad", base="mycelium",
  shreds=[(3, 6, 4, "chorus"), (6, 8, 3, "starlight"), (2, 9, 3, "mycelium")])
m("幻翼肉沙拉", "salad", base="phantom",
  shreds=[(3, 6, 4, "herb"), (6, 8, 3, "mycelium"), (2, 9, 3, "phantom")])
m("颂果炖肉", "casserole", broth="void", body="pot_dark",
  items=[(2, 6, "pork"), (6, 5, "chorus"), (9, 7, "pork")])

# ---------------- 创意混搭 ----------------
m = G("创意")
m("土豆蘑菇酿肉", "stuffed", veg="potato", fill="pork")
m("葫芦塞肉", "stuffed", veg="melon", fill="pork")
m("荷叶包鸡", "leaf", content="chicken_br")
m("笋干菌菇素煲", "casserole", body="pot_celadon", broth="broth_pale",
  items=[(2, 6, "bamboo"), (6, 5, "mushroom"), (9, 7, "oyster")])
m("花生炖猪蹄", "casserole", broth="soy",
  items=[(2, 6, "pork"), (6, 5, "peanut"), (9, 7, "pork")])
m("紫苏豆腐煲", "casserole", body="enamel", rim="enamel_rim", broth="soy",
  items=[(2, 6, "tofu_white"), (6, 5, "perilla"), (9, 7, "tofu_white")])
m("荠菜肉丸子", "balls", m="shepherd", edge="pork", n=4, base="broth_pale")
m("香芋泥肉卷", "roll", wrapper="taro", char="chorus_d", fill="pork")
m("秋葵炒肉片", "plate", base="soy_light",
  items=[(2, 7, 2, 3, "greens"), (5, 5, 2, 3, "greens"), (9, 8, 2, 3, "greens"),
         (4, 9, 3, 1, "pork"), (8, 5, 3, 1, "pork"), (11, 6, 2, 1, "pork")])
m("玉米笋小炒", "plate", base="soy_light",
  items=[(2, 7, 2, 3, "potato"), (6, 5, 2, 3, "potato"), (9, 8, 2, 3, "potato"),
         (4, 9, 3, 1, "celery"), (8, 5, 3, 1, "greens")])


# ---------------------------------------------------------------------------
# 点缀层（同 gen_foods 的做法：只给列，行由剪影顶端自动算）
# ---------------------------------------------------------------------------
GARNISH2: dict[str, tuple[tuple[int, int, str], ...]] = {
    "清蒸鲈鱼": ((2, 0, "scallion"), (12, 0, "chili")),
    "椒盐小虾": ((2, 1, "chili"), (11, 1, "scallion")),
    "白灼蛏子": ((2, 1, "chili"), (11, 1, "scallion")),
    "葱油扇贝": ((2, 1, "scallion"), (10, 1, "chili")),
    "卤猪耳": ((2, 1, "chili"), (11, 1, "scallion")),
    "酱牛肉片": ((2, 1, "scallion"), (11, 1, "chili")),
    "卤豆干": ((2, 1, "chili"), (11, 1, "scallion")),
    "桂花糖藕": ((3, 1, "osmanthus"), (10, 1, "osmanthus")),
    "桂花糯米藕": ((3, 1, "osmanthus"), (10, 1, "osmanthus")),
    "艾草青团": ((4, 1, "glutinous"), (10, 1, "herb")),
    "麻团": ((4, 1, "sesame_b"), (9, 1, "sesame_b"), (7, 0, "sesame_b"), (11, 0, "sesame_b")),
    "炸糖糕": ((4, 1, "sugar"), (9, 1, "sugar")),
    "红糖发糕": ((4, 1, "sugar"), (9, 1, "sugar_b")),
    "芝麻汤圆": ((4, 0, "sesame_b"), (10, 0, "sesame_b")),
    "荠菜馄饨": ((3, 0, "sesame_b"), (11, 0, "scallion")),
    "葱油花卷": ((3, 1, "greens"), (11, 1, "greens")),
    "鲜肉烧麦": ((3, 0, "crab_roe"), (11, 0, "scallion")),
    "烤羊排配洋葱": ((2, 1, "herb"), (12, 1, "chili")),
    "香茅烤鸡": ((2, 1, "chili"), (12, 1, "lemongrass")),
    "菠萝炒肉": ((2, 1, "chili"), (12, 1, "greens")),
    "孜然烤羊腰": ((2, 1, "cumin"), (12, 1, "cumin")),
    "烤驼肉串": ((2, 1, "cumin"), (12, 1, "cumin")),
    "香茅烤虾": ((2, 1, "chili"), (12, 1, "lemongrass")),
    "青木瓜沙拉": ((2, 1, "chili"), (11, 1, "peanut")),
    "冬瓜海米汤": ((4, 0, "scallion"), (10, 0, "chili")),
    "丝瓜虾仁汤": ((4, 0, "scallion"), (10, 0, "chili")),
    "酸菜豆腐汤": ((4, 0, "chili"), (10, 0, "scallion")),
    "马蹄糖水": ((4, 0, "osmanthus"), (10, 0, "osmanthus")),
    "芒果糯米饭": ((4, 1, "coconut"), (9, 1, "osmanthus")),
    "椰子冻": ((4, 1, "coconut"), (9, 1, "coconut")),
    "荔枝果冻": ((4, 1, "radish"), (9, 1, "chorus")),
    "绯红菌腊味煲": ((2, 1, "crimson"), (12, 1, "lava")),
    "下界菌菇馅饼": ((2, 1, "crimson"), (12, 1, "lava")),
    "颂果糯米羹": ((4, 0, "starlight"), (10, 0, "chorus")),
    "星光颂果糕": ((4, 1, "starlight"), (9, 1, "chorus")),
    "荷叶包鸡": ((2, 1, "scallion"), (12, 1, "chili")),
    "花生炖猪蹄": ((2, 1, "scallion"), (12, 1, "chili")),
    "紫苏豆腐煲": ((2, 1, "perilla"), (12, 1, "chili")),
    "秋葵炒肉片": ((2, 1, "chili"), (12, 1, "garlic")),
    "玉米笋小炒": ((2, 1, "chili"), (12, 1, "garlic")),
    "荠菜肉丸子": ((2, 1, "chili"), (11, 1, "scallion")),
}


def apply_garnish(g, name):
    for x, dy, mat in GARNISH2.get(name, ()):
        y = gf.top_at(g, x)
        if y is not None:
            put(g, x, y + dy, mat)


def build(name: str, arch: str, kw: dict) -> dict:
    g = {}
    ARCH[arch](g, **kw)
    apply_garnish(g, name)
    px = shade(g)
    outline(g, px)
    return to_art(px)


def preview_sheet(items, out, scale=6, cols=7):
    from PIL import Image, ImageDraw, ImageFont

    cell, gap, pad, label_h = 16 * scale, 8, 10, 18
    rows = math.ceil(len(items) / cols)
    w = pad * 2 + cols * cell + (cols - 1) * gap
    h = pad * 2 + rows * (cell + label_h) + (rows - 1) * gap
    img = Image.new("RGB", (w, h), (52, 52, 58))
    draw = ImageDraw.Draw(img)
    font = None
    for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if Path(fp).exists():
            font = ImageFont.truetype(fp, 12)
            break
    for i, (name, art) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cell + gap)
        y = pad + r * (cell + label_h + gap)
        tile = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        for yy in range(16):
            for xx in range(16):
                rgba = art["grid"][yy][xx]
                if rgba:
                    tile.putpixel((xx, yy), rgba)
        big = tile.resize((cell, cell), Image.NEAREST)
        img.paste(big, (x, y), big)
        if font:
            tw = draw.textlength(name, font=font)
            draw.text((x + (cell - tw) / 2, y + cell + 3), name, fill=(230, 230, 234), font=font)
    img.save(out)
    print(f"预览: {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    out_dir = HERE.parent / "foods"
    out_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for group, name, arch, kw in SPEC:
        if args.group and args.group not in group:
            continue
        if args.only and args.only not in name:
            continue
        art = build(name, arch, kw)
        gf.save_png(art, out_dir / f"{name}.png", scale=1)
        items.append((name, art))
        print(f"[{group}] {name}.png")

    print(f"共 {len(items)} 张")
    if args.preview:
        preview_sheet(items, HERE.parent / "_more_preview.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



