#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第三批菜谱贴图：西式（意/德/北欧/俄/匈/法）、日式、韩式、东南亚扩充、
中东/中亚、各国汤品、甜品扩充、下界/末地续增、创意混搭。

复用 gen_foods.py 的着色/描边管线与 gen_foods_more.py 的原型库，
只追加材质与菜品条目。用法：

    python gen_foods_third.py --preview
    python gen_foods_third.py --group 日式 --preview
    python gen_foods_third.py --only 亲子丼
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen_foods as gf  # noqa: E402
import gen_foods_more as gm  # noqa: E402
from gen_foods import MAT, blk, bowl, ell, hline, plate, pot, put, row, vline  # noqa: E402
from render_pixel_art import save_png  # noqa: E402

# ---------------------------------------------------------------------------
# 追加材质（各国料理的酱汁 / 食材 / 器皿）
# ---------------------------------------------------------------------------
NEW_MAT = {
    # 意 / 法
    "tomato_s": (198, 84, 54),
    "pesto": (104, 140, 68),
    "wine": (126, 42, 56),
    "cheese_s": (236, 214, 150),
    "eggplant": (140, 88, 148),
    "zucchini": (146, 176, 92),
    "toast": (222, 176, 108),
    "duck": (190, 94, 76),
    "duck_skin": (216, 152, 118),
    "berry": (156, 52, 86),
    "onion_soup": (200, 152, 88),
    "butter_glaze": (244, 214, 142),
    # 德 / 北欧 / 俄 / 匈
    "sauerkraut": (204, 206, 152),
    "sausage": (178, 92, 74),
    "dill": (122, 166, 94),
    "salmon": (238, 140, 108),
    "salmon_d": (206, 96, 78),
    "lingonberry": (188, 58, 76),
    "venison": (150, 74, 62),
    "beet": (156, 48, 74),
    "borscht": (168, 54, 78),
    "honey": (238, 178, 64),
    "goulash": (176, 80, 46),
    "paprika": (208, 94, 44),
    "fish_dry": (196, 168, 132),
    # 日式
    "teriyaki": (126, 64, 38),
    "mackerel": (150, 176, 190),
    "miso": (170, 128, 78),
    "miso_glaze": (222, 190, 122),
    "dashi": (206, 176, 112),
    "sanma": (170, 186, 198),
    "sanma_belly": (208, 210, 198),
    "ume": (188, 74, 92),
    "yam": (234, 228, 210),
    "tamago": (246, 206, 96),
    "tamago_d": (212, 162, 58),
    "tamago_l": (252, 230, 150),
    "katsu": (208, 158, 98),
    "tempura": (238, 196, 124),
    "tempura_g": (222, 180, 96),
    "noodle": (246, 240, 214),
    "ginger_sauce": (200, 160, 88),
    # 韩式
    "gochujang": (188, 44, 40),
    "stone": (88, 86, 92),
    "stone_rim": (124, 122, 128),
    "stone_d": (58, 56, 62),
    "octopus": (188, 96, 104),
    "doenjang": (148, 112, 70),
    "kimchi": (208, 66, 52),
    "kimchi_j": (168, 44, 44),
    "honey_butter": (232, 186, 92),
    "radish_kimchi": (232, 150, 132),
    "beef_broth": (188, 142, 98),
    "ginseng_broth": (226, 208, 160),
    "sprout": (238, 232, 198),
    "jujube": (146, 58, 54),
    # 泰 / 越 / 马来
    "green_curry": (126, 162, 92),
    "red_curry": (192, 84, 62),
    "basil_pork": (152, 92, 62),
    "mango": (244, 186, 72),
    "tom_yum": (206, 96, 58),
    "tilapia": (208, 200, 176),
    "feet": (226, 176, 142),
    "pho": (206, 178, 124),
    "beef_raw": (176, 72, 66),
    "lime": (166, 198, 78),
    "sugarcane": (212, 198, 150),
    "tamarind": (168, 110, 54),
    "lemongrass_soup": (216, 196, 132),
    "sambal": (176, 52, 44),
    "coconut_curry": (232, 206, 150),
    "nyonya": (198, 108, 82),
    # 中东 / 中亚
    "harissa": (188, 62, 42),
    "chickpea_stew": (196, 158, 96),
    "date": (128, 74, 46),
    "date_stew": (146, 86, 52),
    "liver": (146, 86, 80),
    "lentil": (172, 132, 82),
    "apricot": (238, 160, 78),
    "apricot_stew": (204, 132, 74),
    "cumin_oil": (198, 150, 80),
    "hummus": (226, 210, 166),
    "pita": (230, 208, 166),
    "carrot": (232, 146, 58),
    # 汤品
    "corn": (246, 214, 104),
    "bitter": (154, 182, 108),
    "milk_broth": (238, 230, 212),
    "century": (74, 68, 60),
    "pumpkin_soup": (236, 164, 74),
    "mung": (150, 168, 96),
    "mung_soup": (186, 182, 120),
    "mung_d": (118, 136, 74),
    "bone_broth": (226, 214, 186),
    "cream_soup": (244, 232, 200),
    # 甜品
    "water_chestnut": (238, 232, 220),
    "jujube_d": (112, 42, 40),
    "kumquat": (246, 170, 48),
    "sweet_potato": (226, 146, 80),
    "sweet_potato_soup": (232, 178, 110),
    "peach_gum": (232, 206, 168),
    "red_bean": (146, 76, 66),
    "haw": (196, 60, 52),
    "matcha": (124, 158, 92),
    "matcha_d": (96, 128, 72),
    "agar": (232, 238, 230),
    "chestnut": (150, 96, 54),
    "walnut": (176, 132, 86),
    "persimmon": (208, 124, 54),
    "cocoa": (110, 78, 62),
    "tiramisu": (224, 198, 160),
    "panna": (250, 244, 230),
    "fig": (146, 82, 108),
    "rose": (216, 148, 160),
    # 下界 / 末地
    "sausage_w": (150, 96, 84),
    "crimson_curry": (186, 58, 60),
    "crimson_fried": (206, 78, 62),
    "chorus_meat": (196, 156, 204),
    "chorus_sauce": (172, 124, 190),
    # 创意
    "salted_yolk": (236, 162, 56),
    "sweet_sour": (206, 96, 52),
    "durian": (220, 194, 106),
    "lychee": (246, 226, 224),
    "apple": (198, 66, 58),
    "fig_glaze": (158, 88, 104),
    "peach": (238, 168, 142),
    "peach_stew": (216, 140, 116),
    "passion": (228, 178, 64),
    "apple_stew": (206, 150, 96),
}
MAT.update(NEW_MAT)


def stone_bowl(g):
    """石锅：粗陶深灰，用于石锅拌饭。"""
    for y, hw in [(8, 6), (9, 6), (10, 6), (11, 6), (12, 5), (13, 5), (14, 4)]:
        row(g, y, hw, "stone")
    row(g, 8, 6, "stone_rim")
    blk(g, 6, 15, 4, 1, "stone_d")


def don_bowl(g, grain="rice_grain", tops=(), sauce=None, bowl_fn=None):
    """丼饭：木碗 + 堆高的饭 + 大块浇头 + 酱汁线。"""
    (bowl_fn or bowl)(g)
    ell(g, 7.5, 7.8, 5.4, 3.0, grain)
    for x, y, w, h, m in tops:
        blk(g, x, y, w, h, m)
    if sauce:
        hline(g, 5, 9, 8, sauce)
        put(g, 4, 9, sauce)


gm.ARCH["don"] = don_bowl
gm.ARCH["stone_bowl"] = stone_bowl
gm.ARCH["pot_celadon"] = gm.ARCH["casserole"]  # 占位，防止误用

SPEC: list[tuple[str, str, str, dict]] = []


def G(group):
    def add(name, arch, **kw):
        SPEC.append((group, name, arch, kw))

    return add


# ===========================================================================
# 五、西式风味
# ===========================================================================
m = G("西式·意德北欧")

# ---- 意式 ----
m("番茄罗勒烩鸡腿", "casserole", body="copper", rim="copper_rim", broth="tomato_s",
  items=[(2, 6, "chicken_br"), (6, 5, "pesto"), (9, 7, "chicken_br")])
m("玛格丽特焗番茄肉盏", "tart", shell="tomato", rim="cheese_d", fill="cheese_s")
m("奶油蘑菇意式炖鸡", "casserole", body="enamel", rim="enamel_rim", broth="cream",
  items=[(2, 6, "chicken_br"), (6, 5, "mushroom"), (9, 7, "chicken")])
m("红酒炖牛肉", "casserole", body="pot", broth="wine",
  items=[(2, 6, "beef"), (6, 5, "mushroom"), (9, 7, "beef")])
m("意式肉丸番茄煲", "casserole", body="pot_celadon", broth="tomato_s",
  items=[(2, 6, "shepherd"), (6, 5, "tomato"), (9, 7, "shepherd")])
m("焗茄子芝士卷", "roll", wrapper="eggplant", char="cheese_d", fill="cheese", r=2.3)
m("青酱虾仁烩土豆", "plate", base="pesto",
  items=[(2, 6, 3, 2, "potato"), (7, 7, 3, 2, "shrimp"), (5, 4, 2, 2, "potato")])
m("烤番茄蒜香面包盏", "tart", shell="toast", rim="crust_d", fill="tomato")
m("香草烤小土豆配培根", "plate", base="butter_glaze",
  items=[(2, 6, 3, 2, "potato"), (7, 5, 3, 2, "potato"),
         (4, 8, 3, 1, "bacon_fat"), (9, 8, 2, 1, "bacon_fat")])

# ---- 德式 ----
m("德式咸猪肘配酸椰菜", "plate", base="sauerkraut",
  items=[(2, 6, 4, 3, "pork_red"), (7, 7, 4, 2, "pork_red"), (5, 5, 2, 2, "bone")])
m("香肠土豆炖锅", "casserole", body="lacquer", rim="lacquer_rim", broth="gravy",
  items=[(2, 6, "sausage"), (6, 5, "potato"), (9, 7, "sausage")])
m("酸椰菜炖猪肉", "casserole", body="enamel", rim="enamel_rim", broth="sauerkraut",
  items=[(2, 6, "pork"), (6, 5, "pork_red"), (9, 7, "sauerkraut")])
m("黑森林炖果肉煲", "casserole", body="pot_dark", broth="wine",
  items=[(2, 6, "pork"), (6, 5, "berry"), (9, 7, "berry")])
m("土豆培根团子", "balls", m="potato", edge="bacon_fat", n=4, base="gravy")
m("苹果烤猪排", "plate", base="gravy",
  items=[(2, 6, 4, 3, "pork_red"), (7, 5, 3, 2, "apple"), (4, 4, 2, 1, "bone")])

# ---- 北欧 ----
m("盐渍三文鱼配莳萝酱", "plate", base=None,
  items=[(2, 5, 5, 4, "salmon"), (7, 6, 5, 3, "salmon_d"),
         (4, 4, 2, 1, "dill"), (10, 5, 2, 1, "dill")])
m("莳萝奶油炖鱼", "casserole", body="enamel", rim="enamel_rim", broth="cream",
  items=[(2, 6, "fish_white"), (6, 5, "dill"), (9, 7, "fish_white")])
m("烤三文鱼排配柠檬土豆", "plate", base="butter_glaze",
  items=[(2, 5, 4, 4, "salmon"), (7, 7, 3, 2, "potato"), (10, 5, 2, 2, "lemon")])
m("越橘酱炖鹿肉", "casserole", body="copper", rim="copper_rim", broth="lingonberry",
  items=[(2, 6, "venison"), (6, 5, "venison"), (9, 7, "berry")])
m("北欧风干鱼块", "jerky", meat="fish_dry", fat="fish_gold")

# ---- 俄式 ----
m("俄式红菜炖牛肉", "casserole", body="pot", broth="borscht",
  items=[(2, 6, "beet"), (6, 5, "beef"), (9, 7, "beet")])
m("奶油酸黄瓜炖肉", "casserole", body="pot_celadon", broth="cream",
  items=[(2, 6, "pickle"), (6, 5, "pork"), (9, 7, "pickle_dark")])
m("烤土豆肉盅", "stuffed", veg="potato", fill="pork", shape="round")
m("蜂蜜烤猪肉", "plate", base="honey",
  items=[(2, 6, 4, 3, "pork_red"), (7, 5, 4, 3, "pork_red")])
m("腌酸黄瓜拼盘", "plate", base="broth_pale",
  items=[(2, 7, 4, 2, "pickle_dark"), (7, 6, 4, 2, "pickle"), (4, 5, 3, 1, "pickle_dark")])
m("俄式蘑菇肉饺", "dumpling", skin="dough", hint="mushroom")

# ---- 匈牙利 ----
m("匈牙利红烩牛肉", "casserole", body="pot", broth="goulash",
  items=[(2, 6, "beef"), (6, 5, "potato"), (9, 7, "beef")])
m("甜椒炖猪肉", "casserole", body="copper", rim="copper_rim", broth="paprika",
  items=[(2, 6, "pork"), (6, 5, "bell"), (9, 7, "pork_red")])

# ---- 法式 ----
m("法式奶油煎鸡", "plate", base="cream",
  items=[(2, 6, 4, 3, "chicken_br"), (7, 7, 3, 2, "chicken_br"), (5, 5, 2, 1, "herb")])
m("普罗旺斯杂菜煲", "casserole", body="enamel", rim="enamel_rim", broth="tomato_s",
  items=[(2, 6, "eggplant"), (6, 5, "zucchini"), (9, 7, "tomato")])
m("香煎鸭胸配莓果酱汁", "plate", base="berry",
  items=[(2, 6, 6, 3, "duck"), (9, 5, 3, 2, "berry"), (3, 5, 4, 1, "duck_skin")])
m("洋葱焗肉汤盅", "casserole", body="enamel", rim="enamel_rim", broth="onion_soup",
  items=[(3, 5, "cheese"), (7, 5, "toast"), (10, 6, "herb")])

# ===========================================================================
# 六、日式
# ===========================================================================
m = G("日式")
m("照烧鸡腿排", "plate", base="teriyaki",
  items=[(2, 6, 5, 3, "chicken_br"), (8, 7, 4, 2, "chicken_br")])
m("寿喜烧牛肉煲", "casserole", body="pot_dark", broth="soy",
  items=[(2, 6, "beef"), (6, 5, "tofu_white"), (9, 7, "greens")])
m("味噌青花鱼", "fish", skin="mackerel", belly="miso_glaze",
  garnish=[(4, 6, "ginger"), (9, 6, "scallion")])
m("姜汁烧猪肉", "plate", base="ginger_sauce",
  items=[(2, 6, 5, 3, "pork_red"), (8, 7, 3, 2, "pork"), (5, 4, 2, 1, "ginger")])
m("亲子丼", "don",
  tops=[(2, 6, 4, 2, "chicken_br"), (7, 5, 3, 2, "egg"), (5, 4, 2, 1, "onion")],
  sauce="soy")
m("牛肉丼", "don",
  tops=[(2, 6, 4, 2, "beef"), (7, 5, 3, 2, "onion"), (9, 7, 2, 1, "scallion")],
  sauce="soy")
m("日式萝卜炖牛腩", "casserole", body="pot_celadon", broth="soy",
  items=[(2, 6, "radish"), (6, 5, "beef"), (9, 7, "radish")])
m("关东煮拼盘", "soup", broth="dashi",
  items=[(3, 7, 2, 2, "radish"), (7, 8, 2, 2, "egg_braised"), (10, 7, 1, 2, "kelp_knot")])
m("天妇罗拼盘", "plate", base="oil",
  items=[(2, 6, 4, 2, "tempura"), (7, 5, 3, 2, "tempura_g"), (5, 8, 3, 1, "tempura")])
m("盐烤秋刀鱼", "fish", skin="sanma", belly="sanma_belly",
  garnish=[(4, 6, "lemon"), (9, 6, "salt")] if "salt" in MAT else [(4, 6, "lemon")])
m("梅子蒸鸡肉", "plate", base="cream",
  items=[(2, 6, 4, 3, "chicken"), (7, 6, 3, 2, "chicken"), (5, 4, 2, 2, "ume")])
m("菌菇味噌汤煮肉片", "soup", broth="miso",
  items=[(3, 7, 2, 2, "mushroom"), (7, 8, 2, 2, "pork"), (10, 7, 1, 2, "greens")])
m("山药泥拌肉糜", "porridge", body="yam", sheen="cream",
  dots=[(4, 8, "pork"), (8, 7, "pork"), (10, 9, "scallion")])
m("西京烧鳕鱼", "fish", skin="miso_glaze", belly="fish_white",
  garnish=[(4, 6, "ginger")])
m("玉子烧", "block", body="tamago", band="tamago_d", top="tamago_l")
m("咖喱猪排饭", "don",
  tops=[(2, 6, 5, 2, "curry"), (7, 4, 3, 3, "katsu"), (10, 7, 2, 1, "katsu")],
  sauce="curry")

# ===========================================================================
# 七、韩式
# ===========================================================================
m = G("韩式")
m("韩式辣酱炒五花肉", "plate", base="gochujang",
  items=[(2, 6, 4, 3, "pork_red"), (7, 7, 4, 2, "bacon_fat"), (4, 4, 3, 1, "pork")])
m("安东炖鸡", "casserole", body="lacquer", rim="lacquer_rim", broth="soy",
  items=[(2, 6, "chicken_br"), (6, 5, "potato"), (9, 7, "chicken")])
m("石锅拌饭", "don", bowl_fn=stone_bowl,
  tops=[(2, 6, 3, 2, "greens"), (5, 5, 3, 2, "carrot"), (8, 7, 3, 2, "beef"),
         (9, 4, 2, 2, "egg")], sauce="gochujang")
m("辣炒章鱼", "plate", base="gochujang",
  items=[(2, 6, 4, 3, "octopus"), (7, 7, 3, 2, "octopus"), (5, 4, 2, 1, "scallion")])
m("大酱炖排骨", "casserole", body="pot_dark", broth="doenjang",
  items=[(2, 6, "pork"), (6, 5, "bone"), (9, 7, "pork_red")])
m("韩式土豆排骨汤", "casserole", body="pot", broth="beef_broth",
  items=[(2, 6, "potato"), (6, 5, "pork"), (9, 7, "bone")])
m("辣白菜炖豆腐", "casserole", body="enamel", rim="enamel_rim", broth="kimchi",
  items=[(2, 6, "tofu_white"), (6, 5, "kimchi"), (9, 7, "kimchi_j")])
m("芝士辣炒鸡", "plate", base="gochujang",
  items=[(2, 6, 4, 3, "chicken_br"), (7, 7, 3, 2, "cheese"), (5, 4, 2, 1, "chili")])
m("蜂蜜黄油烤排骨", "plate", base="honey_butter",
  items=[(2, 6, 5, 3, "pork_red"), (8, 6, 3, 2, "pork_red")])
m("韩式腌渍辣萝卜", "chunks", meat="radish_kimchi", fat="kimchi_j", base="kimchi")
m("海带牛肉汤", "soup", broth="beef_broth",
  items=[(3, 7, 2, 2, "kelp"), (7, 8, 2, 2, "beef"), (10, 7, 1, 2, "kelp")])
m("参鸡汤", "soup", broth="ginseng_broth",
  items=[(4, 7, 4, 3, "chicken"), (9, 8, 1, 1, "jujube")])
m("甜辣炸鸡块", "plate", base="gochujang",
  items=[(2, 6, 3, 2, "fried"), (6, 7, 3, 2, "fried"), (9, 5, 3, 2, "fried")])
m("豆芽炒肉", "plate", base="soy_light",
  items=[(2, 7, 3, 1, "sprout"), (6, 6, 3, 1, "sprout"), (9, 8, 3, 1, "sprout"),
         (4, 8, 4, 1, "pork")])

# ===========================================================================
# 八、东南亚 & 热带扩充
# ===========================================================================
m = G("东南亚·泰越马来")
m("泰式青咖喱鸡", "casserole", body="pot_celadon", broth="green_curry",
  items=[(2, 6, "chicken_br"), (6, 5, "herb"), (9, 7, "chicken")])
m("红咖喱牛腩", "casserole", body="copper", rim="copper_rim", broth="red_curry",
  items=[(2, 6, "beef"), (6, 5, "coconut"), (9, 7, "beef")])
m("香茅柠檬蒸鱼", "fish", skin="fish_skin", belly="fish_white",
  garnish=[(4, 6, "lemongrass"), (9, 6, "lemon")])
m("泰式打抛猪肉碎", "plate", base="basil_pork",
  items=[(2, 7, 4, 2, "pork"), (7, 6, 3, 2, "pork_red"), (4, 5, 2, 1, "chili")])
m("椰香烤凤梨虾", "plate", base="coconut",
  items=[(2, 6, 4, 3, "pineapple"), (7, 7, 3, 2, "shrimp"), (5, 4, 2, 1, "shrimp")])
m("芒果炒虾仁", "plate", base="butter_glaze",
  items=[(2, 6, 4, 3, "mango"), (7, 7, 3, 2, "shrimp"), (5, 4, 2, 1, "mango")])
m("泰式酸辣凤爪煲", "casserole", body="pot", broth="tom_yum",
  items=[(2, 6, "feet"), (6, 5, "chili"), (9, 7, "feet")])
m("烤罗非鱼配青柠酱", "fish", skin="tilapia", belly="fish_white",
  garnish=[(4, 6, "lime"), (9, 6, "herb")])
m("泰式椰浆南瓜羹", "porridge", body="pumpkin_soup", sheen="coconut",
  dots=[(4, 8, "pumpkin"), (8, 7, "coconut"), (10, 9, "pumpkin")])

m("越式香茅烤猪肉", "skewer", base="lemongrass_soup",
  chunks=[(4, 9, "pork_red"), (6, 7, "pork_red"), (8, 5, "lemongrass")])
m("越南牛肉河粉煲", "casserole", body="enamel", rim="enamel_rim", broth="pho",
  items=[(2, 5, "beef"), (6, 5, "chili"), (9, 6, "herb"), (4, 7, "beef")])
m("青柠腌牛肉沙拉", "salad", base="beef_raw",
  shreds=[(3, 6, 4, "lime"), (6, 8, 3, "herb"), (2, 9, 3, "onion")])
m("甘蔗虾", "skewer", stick="sugarcane",
  chunks=[(4, 9, "shrimp_d"), (6, 7, "shrimp"), (8, 5, "shrimp_d")])
m("越式酸辣罗非鱼", "casserole", body="pot", broth="tamarind",
  items=[(2, 6, "tilapia"), (6, 5, "chili"), (9, 7, "tilapia")])
m("香茅姜炖鸡", "casserole", body="lacquer", rim="lacquer_rim", broth="lemongrass_soup",
  items=[(2, 6, "chicken_br"), (6, 5, "ginger"), (9, 7, "chicken")])

m("叁巴酱炒虾", "plate", base="sambal",
  items=[(2, 6, 3, 2, "shrimp"), (6, 7, 3, 2, "shrimp"), (9, 5, 3, 2, "shrimp")])
m("椰浆辣焖鸡块", "casserole", body="copper", rim="copper_rim", broth="coconut_curry",
  items=[(2, 6, "chicken_br"), (6, 5, "chili"), (9, 7, "chicken")])
m("娘惹豆腐煲", "casserole", body="enamel", rim="enamel_rim", broth="nyonya",
  items=[(2, 6, "tofu_white"), (6, 5, "shrimp"), (9, 7, "tofu")])

# ===========================================================================
# 九、荒漠 / 干草原 / 中东
# ===========================================================================
m = G("荒漠·中东")
m("烤羊肉配哈里萨辣酱", "plate", base="harissa",
  items=[(2, 6, 4, 3, "lamb"), (7, 7, 4, 2, "lamb"), (5, 4, 2, 1, "herb")])
m("鹰嘴豆炖羊肉", "casserole", body="pot", broth="chickpea_stew",
  items=[(2, 6, "lamb"), (6, 5, "chickpea"), (9, 7, "lamb")])
m("椰枣焖牛肉", "casserole", body="pot_dark", broth="date_stew",
  items=[(2, 6, "beef"), (6, 5, "date"), (9, 7, "beef")])
m("孜然洋葱烤羊肝", "skewer", base="cumin_oil",
  chunks=[(4, 9, "liver"), (6, 7, "onion"), (8, 5, "liver")])
m("扁豆肉糜煲", "casserole", body="pot_celadon", broth="lentil",
  items=[(2, 6, "lentil"), (6, 5, "pork"), (9, 7, "lentil")])
m("烤馕包烤羊肉", "naan_meat")
m("杏干炖羊肉", "casserole", body="copper", rim="copper_rim", broth="apricot_stew",
  items=[(2, 6, "lamb"), (6, 5, "apricot"), (9, 7, "lamb")])
m("孜然土豆烤牛肉", "plate", base="cumin_oil",
  items=[(2, 6, 3, 2, "potato"), (6, 7, 3, 2, "beef"), (9, 5, 3, 2, "potato")])
m("鹰嘴豆泥拼盘", "plate", base="hummus",
  items=[(2, 7, 4, 2, "chickpea"), (7, 5, 4, 2, "pita"), (4, 5, 2, 1, "olive")])
m("中亚抓饭", "rice", grain="rice_grain",
  tops=[(3, 6, "lamb"), (7, 5, "carrot"), (9, 7, "raisin")])

# ===========================================================================
# 十、汤、羹、粥
# ===========================================================================
m = G("汤羹·续")
m("玉米排骨汤", "soup", broth="broth_pale",
  items=[(3, 7, 2, 2, "corn"), (7, 8, 2, 2, "pork"), (10, 7, 1, 2, "corn")])
m("番茄牛肉汤", "soup", broth="tomato_s",
  items=[(3, 7, 2, 2, "tomato"), (7, 8, 2, 2, "beef"), (10, 7, 1, 2, "tomato")])
m("菌菇鸡汤", "soup", broth="broth",
  items=[(3, 7, 2, 2, "mushroom"), (7, 8, 2, 2, "chicken"), (10, 7, 1, 2, "mushroom_e")])
m("苦瓜排骨汤", "soup", broth="broth_pale",
  items=[(3, 7, 2, 2, "bitter"), (7, 8, 2, 2, "pork"), (10, 7, 1, 2, "bitter")])
m("鲫鱼豆腐汤", "soup", broth="milk_broth",
  items=[(3, 7, 2, 2, "fish_white"), (7, 8, 2, 2, "tofu_white"), (10, 7, 1, 2, "scallion")])
m("百合莲子粥", "porridge", body="rice_grain", sheen="cream",
  dots=[(4, 8, "lily"), (8, 7, "lotus"), (10, 9, "lily")])
m("皮蛋瘦肉粥", "porridge", body="rice_grain", sheen="cream",
  dots=[(4, 8, "century"), (8, 7, "pork"), (10, 9, "century")])
m("南瓜小米粥", "porridge", body="pumpkin_soup", sheen="cream",
  dots=[(4, 8, "pumpkin"), (8, 7, "pumpkin"), (10, 9, "couscous")])
m("银耳莲子羹", "porridge", body="glutinous", sheen="cream",
  dots=[(4, 8, "lotus"), (8, 7, "ginkgo"), (10, 9, "lotus")])
m("绿豆百合汤", "soup", broth="mung_soup",
  items=[(3, 7, 2, 2, "mung"), (7, 8, 2, 2, "lily"), (10, 7, 1, 2, "mung")])
m("味噌菌菇汤", "soup", broth="miso",
  items=[(3, 7, 2, 2, "mushroom"), (7, 8, 2, 2, "tofu_white"), (10, 7, 1, 2, "mushroom_e")])
m("蛤蜊味噌汤", "soup", broth="miso",
  items=[(3, 7, 2, 2, "clam"), (7, 8, 2, 2, "clam_sh"), (10, 7, 1, 2, "scallion")])
m("辣白菜豆腐汤", "soup", broth="kimchi",
  items=[(3, 7, 2, 2, "tofu_white"), (7, 8, 2, 2, "kimchi"), (10, 7, 1, 2, "kimchi_j")])
m("牛骨浓汤", "soup", broth="bone_broth",
  items=[(3, 7, 2, 2, "beef"), (7, 8, 2, 2, "bone"), (10, 7, 1, 2, "scallion")])
m("椰浆鸡汤", "soup", broth="coconut",
  items=[(3, 7, 2, 2, "chicken"), (7, 8, 2, 2, "mushroom"), (10, 7, 1, 2, "chili")])
m("红菜汤", "soup", broth="borscht",
  items=[(3, 7, 2, 2, "beet"), (7, 8, 2, 2, "pork"), (10, 7, 1, 2, "cream")])
m("番茄豆子浓汤", "soup", broth="tomato_s",
  items=[(3, 7, 2, 2, "bean"), (7, 8, 2, 2, "tomato"), (10, 7, 1, 2, "bean_stew")])

# ===========================================================================
# 十一、甜品、蜜饯、果食
# ===========================================================================
m = G("甜品·中外")
m("桂花马蹄糕", "block", body="water_chestnut", band="osmanthus", top="sugar")
m("枣泥糕", "block", body="jujube", band="jujube_d", top="sesame_b")
m("绿豆糕", "block", body="mung", band="mung_d", top="sugar")
m("糖渍金桔", "cup", glass="glass_blue", layers=[(5, 7, "kumquat"), (8, 11, "honey")])
m("莲子百合冻", "cup", glass="glass_blue", layers=[(5, 7, "lotus"), (8, 11, "agar")])
m("红薯糖水", "soup", broth="sweet_potato_soup",
  items=[(3, 7, 2, 2, "sweet_potato"), (7, 8, 2, 2, "sweet_potato"), (10, 7, 1, 2, "ginger")])
m("桃胶雪梨羹", "porridge", body="peach_gum", sheen="cream",
  dots=[(4, 8, "pear"), (8, 7, "peach_gum"), (10, 9, "pear")])
m("豆沙凉糕", "block", body="red_bean", band="glutinous", top="sugar")
m("山楂雪丽球", "balls", m="haw", edge="sugar", n=4, base=None)
m("抹茶布丁", "cup", glass="glass_blue", layers=[(5, 7, "matcha"), (8, 11, "matcha_d")])
m("红豆寒天冻", "cup", glass="glass_pink", layers=[(5, 7, "red_bean"), (8, 10, "agar"), (11, 11, "red_bean")])
m("栗子蜜煮", "rice", grain="chestnut", bowl_fn=gm.bowl_porcelain,
  tops=[(4, 6, "honey"), (8, 6, "chestnut")])
m("红豆冰羹", "cup", glass="glass_blue", layers=[(5, 7, "red_bean"), (8, 11, "agar")])
m("柿饼卷核桃", "roll", wrapper="persimmon", char="jujube_d", fill="walnut", r=2.2)
m("提拉米苏冻", "cup", glass="porcelain", layers=[(5, 6, "cocoa"), (7, 10, "tiramisu"), (11, 11, "cocoa")])
m("意式奶冻", "cup", glass="glass_pink", layers=[(5, 7, "panna"), (8, 11, "berry")])
m("椰浆芒果冻", "cup", glass="glass_blue", layers=[(5, 7, "mango"), (8, 11, "coconut")])
m("椰香香蕉糕", "block", body="banana", band="coconut", top="coconut")
m("椰枣果仁球", "balls", m="date", edge="walnut", n=4, base="honey")
m("玫瑰蜜渍无花果", "cup", glass="glass_pink", layers=[(5, 7, "fig"), (8, 11, "rose")])

# ===========================================================================
# 十二、下界
# ===========================================================================
m = G("下界·续")
m("扭曲菌菇烤肠", "skewer", chunks=[(4, 9, "sausage_w"), (6, 7, "warped"), (8, 5, "sausage_w")])
m("绯红菌菇咖喱肉煲", "casserole", body="pot_dark", broth="crimson_curry",
  items=[(2, 6, "nether_meat"), (6, 5, "crimson"), (9, 7, "nether_meat")])
m("下界岩熏腊排骨", "jerky", meat="nether_meat", fat="crimson_d")
m("扭曲菌菇豆腐羹", "porridge", body="warped", sheen="cream",
  dots=[(4, 8, "tofu_white"), (8, 7, "warped_d"), (10, 9, "tofu_white")])
m("绯红菌菇炸丸子", "balls", m="crimson_fried", edge="crimson", n=4, base="lava")
m("硫磺风味烤菌菇串", "skewer", chunks=[(4, 9, "fungus"), (6, 7, "sulfur"), (8, 5, "fungus")])
m("下界菌菇椰浆炖鸡", "casserole", body="pot_dark", broth="coconut_curry",
  items=[(2, 6, "chicken"), (6, 5, "crimson"), (9, 7, "chicken_br")])
m("扭曲菌菇蜜肉卷", "roll", wrapper="warped", char="warped_d", fill="honey", r=2.3)

# ===========================================================================
# 十三、末地
# ===========================================================================
m = G("末地·续")
m("颂果腌肉条", "jerky", meat="chorus_meat", fat="chorus_d")
m("幻翼肉烤串", "skewer", chunks=[(4, 9, "phantom"), (6, 7, "mycelium"), (8, 5, "phantom")])
m("菌丝凉拌幻翼丝", "salad", base="mycelium",
  shreds=[(3, 6, 4, "phantom"), (6, 8, 3, "chorus"), (2, 9, 3, "starlight")])
m("颂果酸奶冻", "cup", glass="glass_blue", layers=[(5, 7, "chorus"), (8, 11, "cream")])
m("幻翼肉焗颂果", "casserole", body="pot_dark", broth="chorus_sauce",
  items=[(2, 6, "phantom"), (6, 5, "chorus"), (9, 7, "phantom")])
m("星光菌丝羹", "porridge", body="mycelium", sheen="starlight",
  dots=[(4, 8, "starlight"), (8, 7, "chorus"), (10, 9, "starlight")])
m("颂果菌菇丸子煲", "casserole", body="lacquer", rim="lacquer_rim", broth="chorus_sauce",
  items=[(2, 6, "fishball"), (6, 5, "chorus"), (9, 7, "mycelium")])
m("幻翼风干肉条配颂果酱", "jerky", meat="phantom", fat="chorus")

# ===========================================================================
# 十四、创意混搭
# ===========================================================================
m = G("创意·续")
m("咸蛋黄焗茭白", "plate", base="salted_yolk",
  items=[(2, 6, 3, 2, "bamboo"), (6, 7, 3, 2, "bamboo"), (9, 5, 3, 2, "salted_yolk")])
m("菠萝咕咾肉", "plate", base="sweet_sour",
  items=[(2, 6, 3, 2, "pineapple"), (6, 7, 3, 2, "pork_red"), (9, 5, 3, 2, "bell")])
m("榴莲焖鸡", "casserole", body="pot", broth="durian",
  items=[(2, 6, "chicken_br"), (6, 5, "durian"), (9, 7, "chicken")])
m("荔枝炒虾仁", "plate", base="butter_glaze",
  items=[(2, 6, 3, 2, "lychee"), (6, 7, 3, 2, "shrimp"), (9, 5, 3, 2, "lychee")])
m("苹果炖猪肉", "casserole", body="pot_celadon", broth="apple_stew",
  items=[(2, 6, "pork"), (6, 5, "apple"), (9, 7, "pork_red")])
m("无花果烤肉排", "plate", base="fig_glaze",
  items=[(2, 6, 5, 3, "pork_red"), (8, 6, 3, 2, "fig")])
m("南瓜酿肉", "stuffed", veg="pumpkin", fill="pork", shape="round")
m("芋头烧鸡块", "casserole", body="pot_dark", broth="soy",
  items=[(2, 6, "taro"), (6, 5, "chicken_br"), (9, 7, "taro")])
m("紫苏桃子焖肉", "casserole", body="lacquer", rim="lacquer_rim", broth="peach_stew",
  items=[(2, 6, "pork"), (6, 5, "peach"), (9, 7, "perilla")])
m("玉米菌菇肉煲", "casserole", body="enamel", rim="enamel_rim", broth="broth",
  items=[(2, 6, "corn"), (6, 5, "mushroom"), (9, 7, "pork")])
m("莲子炒鸡丁", "plate", base="soy_light",
  items=[(2, 6, 3, 2, "lotus"), (6, 7, 3, 2, "chicken_br"), (9, 5, 3, 2, "lotus")])
m("百香果煎鸡胸", "plate", base="passion",
  items=[(2, 6, 5, 3, "chicken_br"), (8, 7, 3, 2, "passion")])


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
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
        art = gm.build(name, arch, kw)
        items.append((name, art))
        save_png(art, out_dir / f"{name}.png", scale=1)

    print(f"共 {len(items)} 张")
    if args.preview and items:
        gm.preview_sheet(items, HERE.parent / "_third_preview.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
