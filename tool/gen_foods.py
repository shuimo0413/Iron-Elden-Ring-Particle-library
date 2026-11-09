#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""农夫乐事风格 · 中式热菜 16×16 物品贴图生成器（30 道）。

只负责出 PNG，不生成 JSON / 不写注册代码。
像素排布全部手写（盘子 / 碗 / 砂锅 / 汤碗 四套器皿 + 各自的菜码），
明暗由统一的左上光源自动着色，最后沿剪影外侧描一圈暗边。

用法：
    python gen_foods.py            # 输出到 ../foods/
    python gen_foods.py --preview  # 额外生成预览拼图
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from render_pixel_art import save_png  # noqa: E402

W = H = 16

# ---------------------------------------------------------------------------
# 材质调色板：每格只存材质名，明暗在着色阶段按「是否贴边」推
# ---------------------------------------------------------------------------
MAT: dict[str, tuple[int, int, int]] = {
    # 器皿 —— 木盘 / 木碗（暖橡木，带木纹）/ 陶锅
    "plate": (186, 128, 70),
    "plate_rim": (128, 82, 44),
    "plate_in": (226, 184, 124),
    "grain": (150, 100, 54),
    "bowl_white": (206, 150, 92),
    "bowl": (178, 118, 62),
    "bowl_rim": (238, 200, 142),
    "bowl_dark": (114, 72, 40),
    "pot": (204, 100, 58),
    "pot_dark": (100, 76, 66),
    "pot_celadon": (108, 144, 120),
    "pot_rim": (242, 226, 200),
    # 酱汁 / 汤汁
    "soy": (88, 50, 34),
    "soy_light": (146, 94, 54),
    "chili_oil": (198, 86, 50),
    "broth": (230, 194, 126),
    "broth_pale": (240, 226, 190),
    # 肉类
    "pork": (224, 132, 108),
    "pork_red": (178, 76, 54),
    "pork_pale": (246, 208, 188),
    "cured": (200, 88, 58),
    "chicken": (246, 214, 148),
    "chicken_br": (208, 148, 76),
    "soy_chicken": (172, 86, 40),
    "beef": (142, 62, 50),
    "fish": (240, 240, 234),
    "fish_gold": (228, 166, 88),
    "fish_pink": (246, 184, 172),
    "shrimp": (246, 118, 78),
    "shrimp_d": (198, 66, 46),
    "egg": (252, 214, 86),
    "egg_d": (228, 170, 48),
    "bone": (248, 244, 232),
    # 素料
    "tofu": (234, 202, 142),
    "tofu_white": (252, 248, 234),
    "bamboo": (238, 224, 156),
    "celery": (126, 190, 74),
    "chive": (68, 150, 58),
    "greens": (94, 172, 70),
    "scallion": (136, 214, 96),
    "chili": (224, 56, 46),
    "sesame": (252, 248, 238),
    "mushroom": (126, 82, 54),
    "mushroom_e": (186, 140, 100),
    "oyster": (208, 198, 182),
    "fungus": (60, 50, 48),
    "kelp": (58, 114, 82),
    "laver": (52, 48, 66),
    "radish": (248, 246, 238),
    "radish_dry": (212, 158, 80),
    "potato": (236, 192, 100),
    "taro": (204, 194, 214),
    "lotus": (244, 234, 212),
    "ginkgo": (250, 240, 172),
    "lily": (226, 172, 62),
    "perilla": (150, 72, 140),
    "pickle": (180, 194, 108),
    "pickle_dark": (96, 110, 60),
    "chest_w": (250, 242, 222),
    "melon": (172, 218, 170),
    "loofah": (116, 172, 80),
    "clam": (234, 214, 192),
    "clam_sh": (204, 158, 126),
    "ginger": (242, 214, 148),
    "garlic": (252, 248, 236),
    "bean": (44, 36, 32),
}

OUTLINE = (78, 48, 30)

# ---------------------------------------------------------------------------
# 基础绘制原语
# ---------------------------------------------------------------------------
Grid = dict[tuple[int, int], str]


def put(g: Grid, x: int, y: int, m: str) -> None:
    if 0 <= x < W and 0 <= y < H:
        g[(x, y)] = m


def blk(g: Grid, x: int, y: int, w: int, h: int, m: str) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            put(g, xx, yy, m)


def ell(g: Grid, cx: float, cy: float, rx: float, ry: float, m: str) -> None:
    for y in range(H):
        for x in range(W):
            dx = (x + 0.5 - cx) / rx
            dy = (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                put(g, x, y, m)


def hline(g: Grid, x0: int, x1: int, y: int, m: str) -> None:
    for x in range(min(x0, x1), max(x0, x1) + 1):
        put(g, x, y, m)


def vline(g: Grid, x: int, y0: int, y1: int, m: str) -> None:
    for y in range(min(y0, y1), max(y0, y1) + 1):
        put(g, x, y, m)


def diag(g: Grid, x: int, y: int, n: int, m: str, dx: int = 1, dy: int = 1) -> None:
    for i in range(n):
        put(g, x + dx * i, y + dy * i, m)


def row(g: Grid, y: int, half: int, m: str) -> None:
    """以 x=7.5 为中心、半宽 half 铺一行。"""
    blk(g, 8 - half, y, half * 2, 1, m)


# ---------------------------------------------------------------------------
# 器皿
# ---------------------------------------------------------------------------
def plate(g: Grid) -> None:
    """浅口木盘：木色盘身 + 木纹 + 略微下压的暗沿，中心是亮的内底。"""
    ell(g, 7.5, 12.4, 6.7, 2.5, "plate")
    hline(g, 5, 10, 14, "plate_rim")
    ell(g, 7.5, 12.0, 5.3, 1.7, "plate_in")
    for x in (4, 7, 10):
        put(g, x, 13, "grain")
    for x, y in ((3, 11), (12, 11), (6, 14)):
        put(g, x, y, "grain")


def plate_wide(g: Grid) -> None:
    """更宽的木深盘（汤汁多、堆得矮的菜用）。"""
    ell(g, 7.5, 12.0, 7.0, 2.9, "plate")
    hline(g, 4, 11, 14, "plate_rim")
    ell(g, 7.5, 11.6, 5.6, 1.9, "plate_in")
    for x in (3, 6, 9, 12):
        put(g, x, 12, "grain")
    for x, y in ((2, 10), (13, 10), (5, 14), (10, 14)):
        put(g, x, y, "grain")


def bowl(g: Grid) -> None:
    """木碗：碗身暖木色，竖向木纹，亮口沿 + 木底足。"""
    for y, hw in [(9, 6), (10, 6), (11, 5), (12, 5), (13, 4), (14, 3)]:
        row(g, y, hw, "bowl")
    for x, y in ((4, 11), (4, 12), (10, 10), (10, 11), (7, 13)):
        put(g, x, y, "grain")
    row(g, 9, 6, "bowl_rim")
    blk(g, 6, 15, 4, 1, "bowl_dark")


def pot(g: Grid, body: str = "pot", rim: str = "pot_rim") -> None:
    """砂锅：陶色锅身 + 米白釉口（釉口是关键，否则整口锅糊成一团棕）。"""
    for y, hw in [(9, 6), (10, 6), (11, 6), (12, 5), (13, 5), (14, 4)]:
        row(g, y, hw, body)
    row(g, 8, 6, rim)
    put(g, 1, 9, rim)
    put(g, 1, 10, body)
    put(g, 14, 9, rim)
    put(g, 14, 10, body)


def soup_bowl(g: Grid) -> None:
    """白瓷汤碗：碗身 + 汤面（蓝色碗口替代厚重棕边）。"""
    for y, hw in [(9, 6), (10, 6), (11, 5), (12, 5), (13, 4), (14, 3)]:
        row(g, y, hw, "bowl_white")
    row(g, 9, 6, "plate_rim")
    blk(g, 6, 15, 4, 1, "plate_rim")
    ell(g, 7.5, 9.8, 4.7, 1.0, "broth")
    hline(g, 3, 12, 9, "plate_rim")
    ell(g, 7.5, 10.1, 4.3, 0.7, "broth")


# ---------------------------------------------------------------------------
# 目视反馈用的预览
# ---------------------------------------------------------------------------
def shade(g: Grid) -> dict[tuple[int, int], tuple[int, int, int, int]]:
    """左上方单光源 + 深度渐变着色。

    三层明暗叠加，让每个色块内部有连续的多级过渡，而不是「亮边/暗边」两档：
      1. 贴边明暗：顶/左边缘提亮，底/右边缘压暗（块与块之间自然分界）；
      2. 纵向光衰减：越靠上的行整体越亮（环境光从上往下衰减）；
      3. 深度渐变：同一材质内部离边界越深越暗（BFS 距离，模拟内阴影/AO）。
    """
    from collections import deque

    depth: dict[tuple[int, int], int] = {}
    q: deque[tuple[int, int]] = deque()
    for (x, y), m in g.items():
        if any(g.get((x + ox, y + oy)) != m for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            depth[(x, y)] = 0
            q.append((x, y))
    while q:
        x, y = q.popleft()
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + ox, y + oy)
            if n in g and n not in depth:
                depth[n] = depth[(x, y)] + 1
                q.append(n)

    out: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    for (x, y), m in g.items():
        base = MAT[m]
        up = g.get((x, y - 1)) != m
        dn = g.get((x, y + 1)) != m
        lf = g.get((x - 1, y)) != m
        rt = g.get((x + 1, y)) != m
        s = 1.0
        if up:
            s += 0.16
        if lf:
            s += 0.08
        if dn:
            s -= 0.13
        if rt:
            s -= 0.07
        if up and lf:
            s += 0.07
        if dn and rt:
            s -= 0.04
        s += 0.05 * (8 - y) / 8.0          # 纵向光衰减
        s -= 0.032 * min(depth[(x, y)], 3)  # 深度渐变（内部 AO，弱化避免发闷）
        if s >= 1.0:
            k = (s - 1.0) * 1.35
            c = tuple(int(min(255.0, base[i] + (255 - base[i]) * k)) for i in range(3))
        else:
            c = tuple(int(max(0.0, base[i] * s * 1.03)) for i in range(3))
        # 饱和度提升（农夫乐事式的鲜艳感）：HSV 空间拉饱和、微提亮
        import colorsys
        hh, ss, vv = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
        ss = min(1.0, ss * 1.28 + 0.03)
        vv = min(1.0, vv * 1.04)
        c = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(hh, ss, vv))
        c = tuple(max(0, min(255, v)) for v in c)
        out[(x, y)] = (c[0], c[1], c[2], 255)
    return out


def outline(g: Grid, px: dict) -> None:
    """沿剪影描一圈「带食材色相的暖调暗边」。

    不用统一黑/棕：先把相邻像素的平均色压暗，再与暖棕基色混合。
    这样米饭的边是米色暗调、青菜的边是绿褐暗调，整体统一又不会发黑发硬。
    """
    ring: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for (x, y) in g:
        here = px[(x, y)][:3]
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + ox, y + oy
            if (nx, ny) not in g and 0 <= nx < W and 0 <= ny < H:
                ring.setdefault((nx, ny), []).append(here)
    for (x, y), cols in ring.items():
        n = len(cols)
        avg = tuple(sum(c[i] for c in cols) / n for i in range(3))
        dark = tuple(int(min(255, v * 0.50)) for v in avg)          # 压暗，保留色相
        c = tuple(int(dark[i] * 0.58 + OUTLINE[i] * 0.42) for i in range(3))
        c = tuple(max(0, min(255, v)) for v in c)
        px[(x, y)] = (c[0], c[1], c[2], 255)


def to_art(px: dict) -> dict:
    grid = [[None] * W for _ in range(H)]
    for (x, y), rgba in px.items():
        grid[y][x] = rgba
    return {"width": W, "height": H, "grid": grid}


# ---------------------------------------------------------------------------
# 配色点缀层：每道菜压 2~3 个高饱和小点（辣椒圈 / 葱花 / 芝麻 / 姜丝），
# 把整桌偏棕的色调拉回来。坐标只要给列，行由剪影顶端自动算，绝不会悬空。
# ---------------------------------------------------------------------------
GARNISH: dict[str, tuple[tuple[int, int, str], ...]] = {
    "笋干烧肉": ((3, 1, "chili"), (9, 1, "scallion"), (12, 0, "chili")),
    "香菇滑鸡": ((2, 1, "scallion"), (10, 1, "chili"), (5, 0, "sesame")),
    "豆豉蒸排骨": ((2, 1, "chili"), (11, 1, "scallion"), (9, 0, "sesame")),
    "香干炒芹菜": ((2, 1, "chili"), (11, 1, "sesame"), (8, 0, "chili")),
    "茭白炒肉丝": ((4, 1, "chili"), (11, 1, "scallion"), (2, 0, "sesame")),
    "腐竹烧肉": ((3, 1, "scallion"), (11, 1, "chili"), (7, 0, "sesame")),
    "梅菜蒸肉饼": ((2, 1, "scallion"), (11, 1, "chili"), (7, 0, "sesame")),
    "韭菜炒河虾": ((2, 1, "chili"), (11, 1, "sesame"), (6, 0, "chili")),
    "笋尖菌菇煲": ((2, 1, "scallion"), (12, 1, "chili")),
    "香煎鱼排配姜葱": ((2, 1, "chili"), (12, 1, "scallion"), (8, 0, "chili")),
    "萝卜干炒腊肉": ((2, 1, "scallion"), (11, 1, "chili"), (7, 0, "sesame")),
    "海带烧排骨": ((2, 1, "chili"), (12, 1, "scallion"), (7, 0, "sesame")),
    "平菇滑肉片": ((2, 1, "chili"), (12, 1, "scallion"), (7, 0, "sesame")),
    "蒜香炒蛏子": ((1, 1, "chili"), (12, 1, "scallion"), (7, 0, "sesame")),
    "冬笋焖鸡": ((2, 1, "chili"), (12, 1, "scallion")),
    "香干炒木耳": ((2, 1, "chili"), (12, 1, "sesame"), (7, 0, "chili")),
    "紫苏焖鱼": ((2, 1, "chili"), (12, 1, "scallion"), (7, 0, "sesame")),
    "马蹄炒肉片": ((2, 1, "chili"), (12, 1, "scallion"), (7, 0, "sesame")),
    "冬瓜丸子煲": ((2, 1, "chili"), (12, 1, "scallion")),
    "丝瓜炒蛋": ((2, 1, "chili"), (11, 1, "scallion"), (7, 0, "sesame")),
    "豉油鸡": ((2, 1, "scallion"), (12, 1, "chili"), (8, 0, "sesame")),
    "酸菜炖白肉": ((2, 1, "chili"), (12, 1, "scallion")),
    "香芋蒸排骨": ((2, 1, "chili"), (12, 1, "scallion"), (7, 0, "sesame")),
    "土豆炖鸡块": ((2, 1, "chili"), (12, 1, "scallion")),
    "黄花菜炖肉": ((2, 1, "chili"), (11, 1, "scallion"), (7, 0, "sesame")),
    "爆炒小河虾": ((2, 1, "scallion"), (12, 1, "chili"), (7, 0, "sesame")),
    "莲藕排骨汤": ((3, 0, "scallion"), (11, 0, "chili"), (7, 0, "sesame")),
    "白果炖鸡": ((3, 0, "scallion"), (11, 0, "chili"), (7, 0, "sesame")),
    "紫菜炒鸡蛋": ((3, 1, "chili"), (12, 1, "scallion"), (7, 0, "sesame")),
    "酱萝卜炖牛肉": ((2, 1, "chili"), (12, 1, "scallion")),
}


def top_at(g: Grid, x: int) -> int | None:
    for y in range(H):
        if (x, y) in g:
            return y
    return None


def apply_garnish(g: Grid, name: str) -> None:
    for x, dy, mat in GARNISH.get(name, ()):
        y = top_at(g, x)
        if y is not None:
            put(g, x, y + dy, mat)


# ---------------------------------------------------------------------------
# 菜品定义（每题独立函数，方便单道返工）
# ---------------------------------------------------------------------------
DISHES: list[tuple[str, callable]] = []


def dish(name: str):
    def deco(fn):
        DISHES.append((name, fn))
        return fn

    return deco


@dish("笋干烧肉")
def _(g):
    plate(g)
    ell(g, 7.5, 9.6, 5.4, 2.9, "soy")
    for x, y, w, h in [(2, 7, 3, 3), (6, 8, 3, 3), (10, 5, 3, 3), (4, 4, 3, 2), (9, 9, 3, 2)]:
        blk(g, x, y, w, h, "pork_red")
    for x, y, w in [(3, 5, 3), (8, 7, 3), (2, 9, 2), (11, 8, 2), (6, 6, 2)]:
        hline(g, x, x + w - 1, y, "bamboo")
    put(g, 4, 5, "soy_chicken")
    put(g, 10, 9, "pork_pale")


@dish("香菇滑鸡")
def _(g):
    plate(g)
    ell(g, 7.5, 9.6, 5.2, 2.8, "soy_light")
    for x, y, w, h in [(2, 7, 3, 3), (7, 9, 3, 2), (5, 4, 3, 3), (10, 6, 2, 3)]:
        blk(g, x, y, w, h, "chicken")
    for cx, cy in [(4, 6), (9, 8), (11, 4)]:
        blk(g, cx, cy, 3, 2, "mushroom")
        put(g, cx + 1, cy + 2, "mushroom_e")
    put(g, 3, 9, "chicken_br")
    put(g, 7, 6, "greens")


@dish("豆豉蒸排骨")
def _(g):
    plate_wide(g)
    ell(g, 7.5, 9.8, 5.6, 2.6, "soy")
    for x, y in [(2, 7), (5, 5), (8, 8), (10, 6), (4, 9), (7, 4), (11, 9)]:
        blk(g, x, y, 3, 2, "pork_red")
        put(g, x + 1, y, "bone")
    for x, y in [(3, 6), (6, 8), (9, 5), (11, 7), (2, 9), (8, 10), (5, 4), (12, 9)]:
        put(g, x, y, "bean")


@dish("香干炒芹菜")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.4, "soy_light")
    for x, y in [(2, 8), (6, 6), (9, 9), (4, 5), (10, 7)]:
        blk(g, x, y, 3, 2, "tofu")
    for x, y, n in [(3, 4, 4), (7, 8, 3), (11, 4, 4), (5, 9, 3), (9, 5, 3)]:
        vline(g, x, y, y + n - 1, "celery")
    put(g, 7, 4, "greens")
    put(g, 3, 8, "greens")


@dish("茭白炒肉丝")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.2, 2.5, "soy")
    for x, y, n in [(2, 7, 4), (5, 4, 4), (9, 8, 3), (11, 5, 4), (4, 9, 3), (7, 7, 3)]:
        vline(g, x, y, y + n - 1, "bamboo")
        vline(g, x + 1, y, y + n - 1, "bamboo")
    for x, y in [(4, 6), (8, 9), (10, 4), (3, 8), (6, 8), (10, 9), (2, 5)]:
        hline(g, x, x + 2, y, "pork_pale")
    for x, y in [(5, 5), (9, 6), (3, 9), (11, 8)]:
        hline(g, x, x + 1, y, "pork")


@dish("腐竹烧肉")
def _(g):
    plate(g)
    ell(g, 7.5, 9.6, 5.4, 2.8, "soy")
    for x, y, w, h in [(2, 6, 3, 3), (8, 8, 3, 3), (6, 4, 3, 2), (11, 5, 2, 3)]:
        blk(g, x, y, w, h, "pork_red")
    for x, y in [(3, 4), (9, 5), (4, 9), (11, 8)]:
        hline(g, x, x + 2, y, "lily")
        hline(g, x, x + 1, y + 1, "lily")
    put(g, 7, 7, "lily")
    put(g, 5, 7, "pork_pale")


@dish("梅菜蒸肉饼")
def _(g):
    plate_wide(g)
    ell(g, 7.5, 9.4, 5.4, 3.2, "pork")
    ell(g, 7.5, 8.8, 5.0, 2.6, "pork")
    for x, y in [(3, 7), (6, 5), (9, 8), (5, 9), (8, 6), (11, 7), (4, 5)]:
        hline(g, x, x + 2, y, "pickle_dark")
    put(g, 7, 4, "pickle")
    put(g, 10, 9, "pickle")
    put(g, 2, 9, "pork_pale")


@dish("韭菜炒河虾")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.5, "chili_oil")
    for x, y in [(2, 8), (4, 5), (8, 9), (10, 6), (6, 7)]:
        vline(g, x, y, y + 3, "chive")
        put(g, x + 1, y + 1, "greens")
    for x, y, d in [(3, 6, 1), (7, 8, -1), (10, 4, 1), (5, 9, -1)]:
        blk(g, x, y, 3, 2, "shrimp")
        put(g, x + (0 if d > 0 else 2), y + 2, "shrimp_d")
        put(g, x + (2 if d > 0 else 0), y + 2, "shrimp_d")
    put(g, 12, 8, "shrimp")


@dish("笋尖菌菇煲")
def _(g):
    pot(g, "pot")
    ell(g, 7.5, 7.5, 5.0, 2.0, "soy_light")
    for x, y in [(2, 5), (5, 7), (9, 6), (11, 8)]:
        blk(g, x, y, 2, 3, "bamboo")
        blk(g, x, y, 2, 1, "tofu_white")
    for x, y in [(4, 7), (8, 5), (12, 6)]:
        blk(g, x, y, 3, 2, "mushroom")
    put(g, 7, 5, "mushroom_e")
    put(g, 6, 8, "greens")


@dish("香煎鱼排配姜葱")
def _(g):
    plate(g)
    # 一整块带焦壳的鱼排：通体金黄，底边压进盘沿（y10），鱼肉纹理用粉色碎点表现
    blk(g, 3, 4, 10, 7, "fish_gold")
    blk(g, 2, 5, 12, 5, "fish_gold")
    hline(g, 3, 12, 4, "soy_chicken")
    hline(g, 2, 13, 10, "soy_chicken")
    for x, y in [(4, 6), (7, 5), (10, 6), (5, 7), (9, 7), (11, 5), (3, 7), (6, 8), (10, 8)]:
        put(g, x, y, "fish_pink")
    # 顶上的姜丝葱段
    for x, y, n in [(3, 2, 2), (7, 2, 2), (11, 2, 2)]:
        vline(g, x, y, y + n - 1, "celery")
    for x, y in [(5, 3), (9, 3), (12, 2)]:
        put(g, x, y, "ginger")
    put(g, 2, 3, "ginger")


@dish("萝卜干炒腊肉")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.2, 2.5, "soy")
    for x, y in [(2, 6), (6, 8), (9, 5), (11, 8)]:
        blk(g, x, y, 4, 2, "cured")
        hline(g, x, x + 3, y, "pork_pale")
    for x, y in [(3, 8), (7, 5), (10, 7), (4, 4), (8, 9)]:
        hline(g, x, x + 2, y, "radish_dry")
    put(g, 6, 4, "greens")


@dish("海带烧排骨")
def _(g):
    bowl(g)
    ell(g, 7.5, 8.0, 5.0, 2.6, "soy_light")
    for x, y in [(2, 6), (5, 8), (9, 6), (11, 8)]:
        blk(g, x, y, 3, 2, "kelp")
        hline(g, x, x + 2, y, "greens")
    for x, y in [(3, 4), (7, 5), (10, 3), (6, 8)]:
        blk(g, x, y, 3, 2, "pork_red")
        put(g, x + 1, y, "bone")
    put(g, 4, 6, "kelp")
    put(g, 8, 3, "greens")


@dish("平菇滑肉片")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.4, "soy")
    for x, y in [(2, 7), (6, 5), (9, 8), (11, 5)]:
        blk(g, x, y, 3, 2, "oyster")
        hline(g, x, x + 2, y, "mushroom_e")
        put(g, x + 1, y + 2, "mushroom")
    for x, y in [(4, 8), (8, 9), (10, 7), (5, 3)]:
        blk(g, x, y, 3, 2, "pork_pale")
        put(g, x + 1, y, "pork")
    put(g, 3, 4, "oyster")
    put(g, 12, 9, "pork")


@dish("蒜香炒蛏子")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.4, 2.5, "soy_light")
    for x, y in [(1, 7), (5, 9), (8, 5), (10, 8)]:
        blk(g, x, y, 4, 2, "clam")
        hline(g, x, x + 3, y, "clam_sh")
        put(g, x + 1, y + 1, "pork_pale")
    for x, y in [(3, 5), (7, 8), (11, 6), (6, 4)]:
        put(g, x, y, "garlic")
        put(g, x + 1, y, "garlic")
    put(g, 9, 4, "celery")
    put(g, 4, 8, "celery")


@dish("冬笋焖鸡")
def _(g):
    pot(g, "pot_dark")
    ell(g, 7.5, 7.0, 5.0, 2.2, "soy")
    for x, y in [(2, 5), (6, 7), (10, 4)]:
        blk(g, x, y, 3, 3, "bamboo")
        blk(g, x, y, 3, 1, "tofu_white")
    for x, y in [(4, 6), (8, 5), (11, 7)]:
        blk(g, x, y, 3, 2, "chicken")
    put(g, 3, 4, "chicken_br")
    put(g, 7, 4, "greens")


@dish("香干炒木耳")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.4, "soy")
    for x, y in [(2, 7), (6, 9), (9, 5), (11, 7)]:
        blk(g, x, y, 3, 2, "tofu")
    for x, y in [(4, 5), (7, 7), (10, 9), (2, 4)]:
        blk(g, x, y, 2, 2, "fungus")
        put(g, x + 2, y + 1, "fungus")
    put(g, 6, 4, "fungus")
    put(g, 12, 5, "celery")


@dish("紫苏焖鱼")
def _(g):
    plate_wide(g)
    # 整鱼：酱烧金黄鱼身 + 鱼尾鱼鳍，紫苏叶铺面
    ell(g, 8.4, 8.8, 4.8, 2.4, "fish_gold")
    hline(g, 4, 12, 7, "soy_chicken")
    hline(g, 4, 12, 10, "fish_pink")
    blk(g, 1, 8, 2, 3, "fish_gold")
    put(g, 1, 7, "fish_gold")
    put(g, 1, 11, "fish_gold")
    put(g, 2, 8, "fish_pink")
    put(g, 13, 8, "soy_chicken")
    put(g, 11, 9, "bean")
    for x, y in [(4, 6), (7, 9), (10, 6)]:
        blk(g, x, y, 2, 2, "perilla")
        put(g, x + 1, y + 2, "perilla")
    put(g, 12, 7, "perilla")
    put(g, 6, 7, "egg")


@dish("马蹄炒肉片")
def _(g):
    plate(g)
    ell(g, 7.5, 9.8, 5.0, 2.4, "soy_light")
    for x, y in [(2, 7), (5, 5), (8, 8), (10, 6), (4, 9)]:
        blk(g, x, y, 2, 2, "chest_w")
        put(g, x + 1, y + 1, "radish")
    for x, y in [(3, 5), (7, 6), (9, 9), (11, 8)]:
        blk(g, x, y, 3, 2, "pork_pale")
    put(g, 6, 8, "pork")


@dish("冬瓜丸子煲")
def _(g):
    pot(g, "pot_celadon")
    ell(g, 7.5, 7.0, 5.0, 2.4, "broth")
    for x, y in [(2, 6), (6, 7), (9, 4)]:
        blk(g, x, y, 3, 2, "melon")
        blk(g, x, y, 3, 1, "radish")
    for x, y in [(4, 5), (8, 6), (11, 7)]:
        blk(g, x, y, 2, 2, "pork_red")
        put(g, x, y, "pork")
    put(g, 6, 4, "melon")
    put(g, 12, 5, "greens")


@dish("丝瓜炒蛋")
def _(g):
    plate(g)
    ell(g, 7.5, 9.6, 5.0, 2.6, "soy_light")
    for x, y in [(2, 6), (5, 8), (8, 5), (10, 7)]:
        blk(g, x, y, 3, 2, "loofah")
        put(g, x, y + 2, "celery")
    for x, y in [(4, 4), (7, 7), (10, 4), (3, 9)]:
        blk(g, x, y, 3, 2, "egg")
    put(g, 6, 5, "egg_d")
    put(g, 11, 9, "egg")


@dish("豉油鸡")
def _(g):
    plate_wide(g)
    # 酱汁垫底，鸡腿稳稳坐在盘上：大腿 + 棒腿 + 露出的腿骨
    ell(g, 7.5, 9.6, 5.4, 2.6, "soy")
    ell(g, 5.8, 7.8, 3.8, 2.9, "soy_chicken")
    blk(g, 9, 7, 4, 3, "soy_chicken")
    blk(g, 11, 9, 2, 2, "soy_chicken")
    put(g, 13, 9, "bone")
    put(g, 13, 10, "bone")
    hline(g, 3, 8, 5, "chicken_br")
    hline(g, 6, 11, 9, "chicken_br")
    put(g, 4, 6, "egg")
    put(g, 7, 8, "egg")
    put(g, 10, 8, "egg")
    # 后面再卧一块鸡件
    ell(g, 11.0, 5.2, 2.8, 1.8, "soy_chicken")
    hline(g, 9, 13, 4, "chicken_br")
    put(g, 11, 4, "egg")


@dish("酸菜炖白肉")
def _(g):
    pot(g, "pot")
    ell(g, 7.5, 7.0, 5.0, 2.4, "broth")
    for x, y in [(2, 5), (6, 7), (9, 4)]:
        blk(g, x, y, 3, 2, "pickle")
        hline(g, x, x + 2, y, "pickle_dark")
    for x, y in [(4, 6), (8, 5), (11, 7), (3, 8)]:
        blk(g, x, y, 3, 2, "pork_pale")
    put(g, 12, 4, "pickle")
    put(g, 6, 4, "pork")


@dish("香芋蒸排骨")
def _(g):
    bowl(g)
    ell(g, 7.5, 8.2, 5.0, 2.4, "soy")
    for x, y in [(2, 7), (5, 5), (8, 7), (10, 4)]:
        blk(g, x, y, 3, 2, "taro")
        put(g, x, y, "radish")
    for x, y in [(3, 5), (7, 6), (11, 7), (6, 3)]:
        blk(g, x, y, 3, 2, "pork_red")
        put(g, x + 1, y, "bone")
    put(g, 4, 9, "taro")


@dish("土豆炖鸡块")
def _(g):
    pot(g, "pot_dark")
    ell(g, 7.5, 7.0, 5.0, 2.4, "soy")
    for x, y in [(2, 6), (6, 7), (9, 4)]:
        blk(g, x, y, 3, 2, "potato")
    for x, y in [(4, 5), (8, 6), (11, 7)]:
        blk(g, x, y, 3, 2, "chicken")
    put(g, 5, 4, "potato")
    put(g, 7, 4, "chicken_br")
    put(g, 12, 4, "greens")


@dish("黄花菜炖肉")
def _(g):
    bowl(g)
    ell(g, 7.5, 8.2, 5.0, 2.4, "soy_light")
    for x, y, n in [(2, 6, 4), (5, 5, 4), (8, 7, 3), (10, 5, 4), (4, 8, 3)]:
        vline(g, x, y, y + n - 1, "lily")
    for x, y in [(3, 7), (7, 4), (9, 8)]:
        blk(g, x, y, 3, 2, "pork_red")
    put(g, 6, 6, "pork_pale")
    put(g, 11, 9, "lily")


@dish("爆炒小河虾")
def _(g):
    plate(g)
    ell(g, 7.5, 9.6, 5.2, 2.8, "chili_oil")
    for x, y in [(2, 6), (5, 8), (8, 4), (10, 6), (4, 4), (7, 9)]:
        blk(g, x, y, 3, 2, "shrimp")
        put(g, x, y + 2, "shrimp_d")
        put(g, x + 2, y, "shrimp_d")
    put(g, 3, 9, "shrimp")
    put(g, 11, 9, "shrimp")
    put(g, 6, 6, "shrimp_d")
    put(g, 9, 7, "greens")


@dish("莲藕排骨汤")
def _(g):
    soup_bowl(g)
    for x, y in [(3, 8), (7, 8), (10, 8)]:
        blk(g, x, y, 2, 2, "lotus")
        put(g, x + 1, y, "broth")
    for x, y in [(5, 7), (9, 7), (2, 9)]:
        blk(g, x, y, 2, 2, "pork_red")
    put(g, 12, 9, "lotus")
    put(g, 6, 6, "bone")


@dish("白果炖鸡")
def _(g):
    soup_bowl(g)
    for x, y in [(3, 8), (6, 8), (10, 8)]:
        blk(g, x, y, 2, 2, "ginkgo")
    for x, y in [(5, 7), (9, 7), (2, 9)]:
        blk(g, x, y, 2, 2, "chicken")
    put(g, 12, 9, "ginkgo")
    put(g, 7, 6, "chicken_br")


@dish("紫菜炒鸡蛋")
def _(g):
    plate(g)
    ell(g, 7.5, 9.4, 5.2, 2.8, "egg")
    ell(g, 6.6, 8.4, 4.0, 2.0, "egg")
    for x, y in [(3, 6), (6, 5), (9, 8), (5, 9), (8, 6), (11, 7)]:
        blk(g, x, y, 2, 2, "laver")
    put(g, 4, 4, "laver")
    put(g, 10, 4, "laver")
    put(g, 12, 9, "egg_d")


@dish("酱萝卜炖牛肉")
def _(g):
    pot(g, "pot")
    ell(g, 7.5, 7.0, 5.0, 2.4, "soy")
    for x, y in [(2, 6), (6, 7), (9, 4)]:
        blk(g, x, y, 3, 2, "radish")
    for x, y in [(4, 5), (8, 6), (11, 7)]:
        blk(g, x, y, 3, 2, "beef")
    put(g, 5, 4, "radish")
    put(g, 7, 4, "beef")
    put(g, 12, 4, "greens")


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def build(name: str, fn) -> dict:
    g: Grid = {}
    fn(g)
    apply_garnish(g, name)
    px = shade(g)
    outline(g, px)
    return to_art(px)


def preview(items: list[tuple[str, dict]], out: Path, scale: int = 6) -> None:
    from PIL import Image, ImageDraw, ImageFont

    cols, cell, gap, pad, label_h = 6, 16 * scale, 10, 12, 22
    rows = math.ceil(len(items) / cols)
    w = pad * 2 + cols * cell + (cols - 1) * gap
    h = pad * 2 + rows * (cell + label_h) + (rows - 1) * gap
    img = Image.new("RGB", (w, h), (58, 58, 64))
    draw = ImageDraw.Draw(img)
    font = None
    for fp in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if Path(fp).exists():
            font = ImageFont.truetype(fp, 14)
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
        img.paste(tile.resize((cell, cell), Image.NEAREST), (x, y), tile.resize((cell, cell), Image.NEAREST))
        if font:
            tw = draw.textlength(name, font=font)
            draw.text((x + (cell - tw) / 2, y + cell + 4), name, fill=(232, 232, 236), font=font)
    img.save(out)
    print(f"预览: {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    out_dir = HERE.parent / "foods"
    out_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for name, fn in DISHES:
        if args.only and args.only not in name:
            continue
        art = build(name, fn)
        save_png(art, out_dir / f"{name}.png", scale=1)
        items.append((name, art))
        print(f"{name}.png  ({16}x{16})")

    if args.preview:
        preview(items, HERE.parent / "_foods_preview.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
