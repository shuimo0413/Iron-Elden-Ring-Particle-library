#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 foods/ 下全部 16×16 贴图整合成一张带分组标题的总览大图。

输出：foods/全部贴图总览.png
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen_foods as gf  # noqa: E402
import gen_foods_more as gm  # noqa: E402
import gen_foods_third as gt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FOODS = HERE.parent / "foods"
OUT = FOODS / "全部贴图总览.png"

SCALE = 6
CELL = 16 * SCALE
COLS = 10
GAP = 8
PAD = 26
LABEL_H = 15
HEAD_H = 30
TITLE_H = 46

BG = (44, 45, 50)
CARD = (58, 60, 66)
INK = (238, 238, 242)
SUB = (168, 172, 182)
ACCENT = (226, 176, 92)


def font(size: int, bold: bool = False):
    for path in (
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def sections() -> list[tuple[str, list[str]]]:
    """(分组标题, 菜名列表)，与生成脚本顺序一致。"""
    out: list[tuple[str, list[str]]] = [
        ("一、中式热菜", [n for n, _ in gf.DISHES]),
    ]
    buf: dict[str, list[str]] = {}
    for group, name, _arch, _kw in gm.SPEC:
        buf.setdefault(group, []).append(name)
    titles = [
        ("面点", "二、面食 · 点心 · 小吃"),
        ("卤味", "三、卤味 · 腌腊 · 风干"),
        ("河鲜", "四、河鲜海味进阶"),
        ("西式", "五、西式 · 地中海 · 游牧"),
        ("东南亚", "六、东南亚 · 热带丛林"),
        ("荒漠", "七、荒漠 · 干草原"),
        ("汤羹", "八、汤 · 羹 · 粥"),
        ("甜品", "九、甜品 · 蜜饯 · 果食"),
        ("下界", "十、下界特色料理"),
        ("末地", "十一、末地奇幻料理"),
        ("创意", "十二、小众创意混搭"),
    ]
    for key, title in titles:
        if key in buf:
            out.append((title, buf[key]))

    buf3: dict[str, list[str]] = {}
    for group, name, _arch, _kw in gt.SPEC:
        buf3.setdefault(group, []).append(name)
    titles3 = [
        ("西式·意德北欧", "十三、西式风味（意 / 德 / 北欧 / 俄 / 匈 / 法）"),
        ("日式", "十四、日式风味"),
        ("韩式", "十五、韩式风味"),
        ("东南亚·泰越马来", "十六、东南亚扩充（泰 / 越 / 马来）"),
        ("荒漠·中东", "十七、荒漠 · 中东 · 中亚"),
        ("汤羹·续", "十八、各国汤 · 羹 · 粥"),
        ("甜品·中外", "十九、甜品 · 蜜饯（中外）"),
        ("下界·续", "二十、下界特色料理（续）"),
        ("末地·续", "二十一、末地奇幻料理（续）"),
        ("创意·续", "二十二、小众创意混搭（续）"),
    ]
    for key, title in titles3:
        if key in buf3:
            out.append((title, buf3[key]))
    return out


def main() -> int:
    secs = sections()
    total = sum(len(names) for _, names in secs)

    rows_icons = sum(math.ceil(len(names) / COLS) for _, names in secs)
    width = PAD * 2 + COLS * CELL + (COLS - 1) * GAP
    height = TITLE_H + PAD + len(secs) * HEAD_H + rows_icons * (CELL + LABEL_H + GAP) + PAD

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    f_title = font(26, True)
    f_head = font(15, True)
    f_label = font(11)

    # 标题
    d.text((PAD, 14), "农夫乐事 · 美食拓展 贴图总览", font=f_title, fill=INK)
    tw = d.textlength(f"共 {total} 张 · 16×16", font=f_head)
    d.text((width - PAD - tw, 24), f"共 {total} 张 · 16×16", font=f_head, fill=ACCENT)

    y = TITLE_H + PAD
    for title, names in secs:
        # 分组标题条
        d.text((PAD, y + 4), title, font=f_head, fill=ACCENT)
        cnt = f"{len(names)} 道"
        cw = d.textlength(cnt, font=f_label)
        d.text((width - PAD - cw, y + 7), cnt, font=f_label, fill=SUB)
        line_y = y + HEAD_H - 8
        d.line([(PAD, line_y), (width - PAD, line_y)], fill=(72, 74, 82), width=1)
        y += HEAD_H

        for i, name in enumerate(names):
            r, c = divmod(i, COLS)
            x = PAD + c * (CELL + GAP)
            cy = y + r * (CELL + LABEL_H + GAP)
            src = FOODS / f"{name}.png"
            if not src.exists():
                print(f"缺少: {src.name}")
                continue
            # 卡片底
            d.rounded_rectangle([x - 2, cy - 2, x + CELL + 2, cy + CELL + 2], 6, fill=CARD)
            tile = Image.open(src).convert("RGBA").resize((CELL, CELL), Image.NEAREST)
            img.paste(tile, (x, cy), tile)
            lw = d.textlength(name, font=f_label)
            d.text((x + (CELL - lw) / 2, cy + CELL + 1), name, font=f_label, fill=INK)

        y += math.ceil(len(names) / COLS) * (CELL + LABEL_H + GAP)

    img.save(OUT)
    print(f"已输出 {OUT}  ({img.width}x{img.height}, {total} 张)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
