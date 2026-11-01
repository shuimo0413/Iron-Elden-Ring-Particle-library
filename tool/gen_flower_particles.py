#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「玫瑰 / 白百合」主题 32×32 粒子 JSON，并调用 render_pixel_art 导出 PNG。

只出四张：花朵两张（``rose_bloom`` / ``lily_bloom``）、花瓣两张（``rose_petal`` / ``lily_petal``）。
花瓣单独一枚就够，游戏里靠粒子的随机旋转铺出飘散群落。

渲染分两遍，这是上一版最关键的修正：
    1. **只描外轮廓**。上一版每片花瓣都画满描边，重叠处的描边全露出来，
       于是花冠变成「彩色玻璃 / 雪花」网格。现在所有花瓣先无描边地填色叠好，
       最后统一沿「有像素 ↔ 无像素」的边界描一圈暗边——只有剪影有边，
       花瓣之间靠明暗落差分界（每瓣左亮右暗，相邻两瓣交界处自然是暗→亮的折缝）。
    2. 填充用「勺形 profile + 二维明暗打分」：根部收窄、中段最宽、尖端圆/尖，
       轴向越靠瓣尖越亮，侧向受光面提亮、背光面压暗，瓣缘内侧再补一道薄边高光。

配色：玫瑰走干玫瑰（低饱和暗红偏褐），避免荧光粉；白百合用冷灰紫压阴影 + 极少量暖黄。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from render_pixel_art import load_pixel_art, save_png

SIZE = 32
CENTER = 16

# ---------------------------------------------------------------------------
# 玫瑰：干玫瑰五阶（暗褐红 → 深红 → 胭脂 → 砖红 → 淡粉）
# ---------------------------------------------------------------------------
R_SHADOW = (48, 10, 22)
R_DEEP = (96, 20, 36)
R_MID = (144, 32, 54)
R_BRIGHT = (196, 62, 82)
R_PALE = (240, 136, 152)
R_HEART = (255, 206, 210)
ROSE_GRAD = (R_SHADOW, R_DEEP, R_MID, R_BRIGHT, R_PALE)
ROSE_DARK_GRAD = (R_SHADOW, R_DEEP, R_MID, R_BRIGHT, R_PALE)

# ---------------------------------------------------------------------------
# 白百合：白花不能靠明度拉层次，阴影走冷灰紫；暖黄只出现在花心
# ---------------------------------------------------------------------------
L_SHADOW = (150, 147, 160)
L_VEIN = (198, 197, 209)
L_WHITE = (234, 240, 249)
L_PURE = (255, 255, 255)
L_CORE = (250, 226, 152)
L_ANTHER = (220, 146, 58)
L_PALE_HALO = (238, 246, 255)
LILY_GRAD = (L_WHITE, L_WHITE, L_PURE, L_PURE, L_PURE)  # 白花几乎不留阴影档，结构交给描边
LILY_DARK_GRAD = (L_SHADOW, L_VEIN, L_WHITE, L_WHITE, L_PURE)

# ---------------------------------------------------------------------------
# 单瓣宽度表（0..1 沿瓣长均匀采样的半宽系数）
# 玫瑰：根部窄 → 中上段最宽 → 瓣尖圆钝（玫瑰花瓣的典型「勺形 + 圆头」）
# 百合：根部窄 → 中段最宽 → 尖端锐利外挑（披针形被片）
# ---------------------------------------------------------------------------
ROSE_PETAL_TABLE = (0.14, 0.26, 0.38, 0.50, 0.62, 0.72, 0.80, 0.86, 0.91, 0.95,
                    0.98, 0.99, 0.99, 0.98, 0.96, 0.93, 0.89, 0.83, 0.75, 0.64,
                    0.50, 0.32)
LILY_PETAL_TABLE = (0.10, 0.22, 0.34, 0.45, 0.55, 0.64, 0.72, 0.79, 0.85, 0.89,
                    0.93, 0.95, 0.96, 0.96, 0.95, 0.93, 0.90, 0.86, 0.80, 0.72,
                    0.62, 0.50, 0.36, 0.20)

# 全局光：从左上方打过来（屏幕坐标 y 向下），整朵花共用一套光照
LIGHT = (CENTER, CENTER, -0.7071, -0.7071, 0.32)
LILY_LIGHT = (CENTER, CENTER, -0.7071, -0.7071, 0.28)

Grid = dict[tuple[int, int], tuple[int, int, int, int]]
Pixels = dict[tuple[int, int], tuple[int, int, int, int]]


def rgba(rgb: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return (rgb[0], rgb[1], rgb[2], max(0, min(255, alpha)))


def put(grid: Grid, x: int, y: int, rgb: tuple[int, int, int], alpha: int = 255) -> None:
    if 0 <= x < SIZE and 0 <= y < SIZE:
        grid[(x, y)] = rgba(rgb, alpha)


def stamp(grid: Grid, pixels: Pixels) -> None:
    """把一层像素盖到画布上（后盖前，等价于「近处的花瓣在前」）。"""
    grid.update(pixels)


def silhouette_outline(grid: Grid, outline: tuple[int, int, int]) -> None:
    """沿剪影**向外**描一圈边：只把「空白但紧贴实体」的格子填上暗色。

    向内描会把花瓣边缘啃掉一像素，白花尤其明显（描边顺着花瓣缺口到处乱窜，
    变成一圈灰色毛边）。向外扩一圈，花瓣内部保持不变，轮廓也干净。
    """
    filled = set(grid)
    ring: set[tuple[int, int]] = set()
    for (x, y) in filled:
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + ox, y + oy
            if (nx, ny) not in filled and 0 <= nx < SIZE and 0 <= ny < SIZE:
                ring.add((nx, ny))
    for (x, y) in ring:
        grid[(x, y)] = rgba(outline)


def soft_glow(grid: Grid, cx: float, cy: float, radius: float,
              rgb: tuple[int, int, int], alpha_core: int, falloff: float = 1.9) -> None:
    """背景光晕：只铺在还没有实体的格子上，不参与造型。"""
    radius_ceil = int(math.ceil(radius)) + 1
    for dy in range(-radius_ceil, radius_ceil + 1):
        for dx in range(-radius_ceil, radius_ceil + 1):
            x, y = int(cx) + dx, int(cy) + dy
            if (x, y) in grid:
                continue
            distance = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if distance > radius:
                continue
            alpha = int(alpha_core * (1 - distance / radius) ** falloff)
            if alpha > 4:
                grid[(x, y)] = rgba(rgb, alpha)


def profile(along: float, a: float, b: float) -> float:
    """勺形宽度系数：u^a·(1-u)^b 归一化到峰值 1。

    与 sin(πu) 的区别是不对称——根部（u→0）还留得住宽度、尖端（u→1）才收，
    所以看起来是「花瓣」而不是「叶片」。
    """
    if not 0 < along < 1:
        return 0.0
    peak = (a / (a + b)) ** a * (b / (a + b)) ** b
    return (along ** a) * ((1 - along) ** b) / peak


def pick(grad: tuple, score: float) -> tuple[int, int, int]:
    return grad[max(0, min(len(grad) - 1, int(score * len(grad))))]


def petal(cx: float, cy: float, length: float, width: float, angle_deg: float,
          grad: tuple, *, a: float = 0.45, b: float = 0.75,
          vein: tuple[int, int, int] | None = None, curves: tuple[float, float] = (0.0, 0.0),
          base_shade: float = 0.0, table: tuple[float, ...] | None = None,
          side_weight: float = 0.50,
          light: tuple[float, float, float, float, float] | None = None,
          cel: bool = False) -> Pixels:
    """一枚花瓣的像素层（不含描边）。

    cel=False：连续明暗（5 级渐变），适合单片飘落花瓣。
    cel=True ：赛璐璐上色——整片只取 1 个主色，再叠暗边（背光侧）、亮边（受光侧）
               和瓣尖高光。花冠用这个模式，否则十几片花瓣的渐变会互相咬成色块噪点。

    侧向 v<0 视为受光面；curves=(根部位移, 尖端位移) 让花瓣整根弯出弧度、做卷边；
    base_shade 把靠近花心的根部再压暗一档（被外层花瓣遮挡的背光面）。
    light = (花心x, 花心y, 光来向x, 光来向y, 权重)：整朵花共用的单向光。
    """
    angle = math.radians(angle_deg)
    axis_x, axis_y = math.cos(angle), math.sin(angle)
    normal_x, normal_y = -axis_y, axis_x
    start_x, start_y = cx - axis_x * length / 2, cy - axis_y * length / 2
    root_curve, tip_curve = curves

    def half_at(along: float) -> float:
        if table is None:
            return (width / 2) * profile(along, a, b)
        if not 0 < along < 1:
            return 0.0
        position = along * (len(table) - 1)
        low = int(position)
        high = min(low + 1, len(table) - 1)
        factor = table[low] + (table[high] - table[low]) * (position - low)
        return (width / 2) * factor

    def local(px: float, py: float) -> tuple[float, float, float]:
        rel_x, rel_y = px - start_x, py - start_y
        along = (rel_x * axis_x + rel_y * axis_y) / length
        shift = root_curve + (tip_curve - root_curve) * along * along
        across = rel_x * normal_x + rel_y * normal_y - shift
        return along, across, half_at(along)

    inside: set[tuple[int, int]] = set()
    reach = int(length / 2 + width + max(abs(root_curve), abs(tip_curve))) + 2
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            x, y = int(cx) + dx, int(cy) + dy
            along, across, half_width = local(x + 0.5, y + 0.5)
            if half_width > 0.4 and abs(across) <= half_width:
                inside.add((x, y))

    pixels: Pixels = {}
    for x, y in inside:
        along, across, half_width = local(x + 0.5, y + 0.5)
        ratio = across / max(half_width, 0.01)
        score = (0.10 * along
                 + side_weight * (0.5 - 0.5 * ratio)
                 + 0.14 * (ratio * ratio)
                 + 0.10 * (1 - abs(ratio)))
        if light is not None:
            origin_x, origin_y, light_x, light_y, weight = light
            rel_x, rel_y = x + 0.5 - origin_x, y + 0.5 - origin_y
            distance = max(math.hypot(rel_x, rel_y), 1.0)
            facing = (rel_x * light_x + rel_y * light_y) / distance
            # facing>0 表示该点位于光源那一侧，应当更亮
            score += weight * (0.5 + 0.5 * facing)
        score -= base_shade * max(0.0, (0.32 - along) / 0.32)
        if cel:
            # 赛璐璐：先按整片受光定主档，再单独压暗背光侧、提亮受光侧与瓣尖
            index = 1
            if score > 0.58:
                index = 2
            elif score < 0.30:
                index = 0
            if ratio > 0.45:
                index -= 1
            elif ratio < -0.50:
                index += 1
            if along > 0.84:
                index += 1
            rgb = grad[max(0, min(3, index))]
        else:
            rgb = pick(grad, score)
        if vein is not None and abs(ratio) < 0.14 and 0.14 < along < 0.95:
            rgb = vein
        pixels[(x, y)] = rgba(rgb)
    return pixels


def rim_light(grid: Grid, grad: tuple, outline: tuple[int, int, int],
              light_dir: tuple[float, float]) -> None:
    """沿受光侧的内边补一道亮边：紧贴描边、且朝光方向的像素提亮一档。

    light_dir 指向「光从哪来」（屏幕坐标，y 向下），例如 (-1,-1) = 左上。
    暗描边旁边接一条亮线，花瓣边缘的「厚度」就出来了，不会像一块平涂色块。
    """
    edges = {(x, y) for (x, y), value in grid.items() if value[:3] == outline[:3]}
    lit_dx, lit_dy = light_dir
    for (x, y), value in list(grid.items()):
        if value[3] < 255 or (x, y) in edges:
            continue
        if not any(neighbour in edges for neighbour in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
            continue
        if (x - CENTER) * lit_dx + (y - CENTER) * lit_dy <= 0:
            continue
        for index, rgb in enumerate(grad):
            if value[:3] == rgb[:3]:
                if index + 1 < len(grad):
                    put(grid, x, y, grad[index + 1])
                break


def crease(grid: Grid, r_from: float, r_to: float, angles: tuple[float, ...],
           rgb: tuple[int, int, int]) -> None:
    """在相邻两片花瓣之间压一道 1px 折缝（从 r_from 放射到 r_to）。

    花冠里相邻花瓣如果只靠明暗过渡，中段会糊成一坨；这道缝就是花瓣的分界线。
    缝只画在花冠内部，不会碰到剪影，所以不会出现「彩色玻璃」那种网格感。
    """
    for angle_deg in angles:
        rad = math.radians(angle_deg)
        radius = r_from
        while radius <= r_to:
            x = int(CENTER + math.cos(rad) * radius)
            y = int(CENTER + math.sin(rad) * radius)
            if (x, y) in grid:
                grid[(x, y)] = rgba(rgb)
            radius += 0.4


def to_json(name: str, grid: Grid) -> dict:
    pixels = [{"x": x, "y": y, "rgba": list(value)}
              for (x, y), value in sorted(grid.items()) if value[3] > 0]
    return {"name": name, "width": SIZE, "height": SIZE, "pixels": pixels}


# ---------------------------------------------------------------------------
# 玫瑰
# ---------------------------------------------------------------------------


def build_rose_bloom() -> dict:
    """俯视玫瑰：外 5 瓣大开 → 中 5 瓣错位 → 中心卷心收口。"""
    grid: Grid = {}
    soft_glow(grid, CENTER, CENTER, 15, R_BRIGHT, 26)

    # 外环：五片大瓣，瓣尖略向外翻（b 调小 → 瓣尖圆钝，不会扎成五角星）
    for index in range(5):
        angle = -90 + index * 72
        rad = math.radians(angle)
        stamp(grid, petal(CENTER + math.cos(rad) * 6.4, CENTER + math.sin(rad) * 6.4,
                          15.5, 16.8, angle, ROSE_GRAD, a=0.45, b=0.58,
                          curves=(0.0, 0.9), light=LIGHT))
    # 中环：五片错开 36°，压暗一档，只露出外缘弧
    for index in range(5):
        angle = -54 + index * 72
        rad = math.radians(angle)
        stamp(grid, petal(CENTER + math.cos(rad) * 3.9, CENTER + math.sin(rad) * 3.9,
                          11.5, 13.4, angle, ROSE_DARK_GRAD, a=0.45, b=0.62,
                          curves=(0.0, 0.7), base_shade=0.5, light=LIGHT))
    # 内环：三片小瓣，最暗，靠近中心
    for index in range(3):
        angle = -30 + index * 120
        rad = math.radians(angle)
        stamp(grid, petal(CENTER + math.cos(rad) * 2.2, CENTER + math.sin(rad) * 2.2,
                          8.0, 10.0, angle, ROSE_DARK_GRAD, a=0.5, b=0.7,
                          base_shade=0.9, light=LIGHT))

    silhouette_outline(grid, R_SHADOW)
    rim_light(grid, ROSE_GRAD, R_SHADOW, (-1.0, -1.0))

    # 卷心（半径 0.6→2.4、转一圈半），把三环花瓣的汇聚点收住，
    # 比直接挖一个黑洞更像「还没展开的花心」
    for step in range(9):
        radius = 0.6 + step * 0.22
        theta = math.radians(-90 + step * 42)
        put(grid, int(CENTER + math.cos(theta) * radius),
            int(CENTER + math.sin(theta) * radius), R_DEEP if step < 6 else R_MID)
    put(grid, CENTER - 1, CENTER - 2, R_HEART)
    put(grid, CENTER + 1, CENTER + 1, R_HEART)
    put(grid, CENTER - 2, CENTER, R_MID)

    # 外瓣瓣尖的高光（露珠感）
    put(grid, 13, 4, R_HEART)
    put(grid, 14, 3, R_PALE)
    put(grid, 20, 6, R_PALE)
    put(grid, 21, 7, R_MID)
    return to_json("rose_bloom", grid)


def build_rose_petal() -> dict:
    """单片玫瑰花瓣：手调宽度表的圆头勺形，正向摆放保住硬边，一道纵向折痕。"""
    grid: Grid = {}
    soft_glow(grid, CENTER, CENTER, 14, R_BRIGHT, 22)
    stamp(grid, petal(CENTER, CENTER, 23, 16, -90, ROSE_GRAD,
                      table=ROSE_PETAL_TABLE, curves=(-1.6, 1.2), side_weight=0.44))

    silhouette_outline(grid, R_SHADOW)
    rim_light(grid, ROSE_GRAD, R_SHADOW, (-1.0, -1.0))

    # 折痕：沿主轴一道浅缝，把受光面与背光面分开，避免读成一块石头
    for step in range(-6, 7):
        x = CENTER + int(round(step * 0.30))
        y = CENTER + step
        key = (x, y)
        if key in grid and grid[key][:3] != R_SHADOW[:3]:
            put(grid, x, y, R_DEEP if step < 0 else R_MID)

    put(grid, 11, 9, R_HEART)
    put(grid, 10, 11, R_PALE)
    return to_json("rose_petal", grid)


# ---------------------------------------------------------------------------
# 白百合
# ---------------------------------------------------------------------------


def build_lily_bloom() -> dict:
    """正视白百合：六枚宽被片咬合成一整朵，尖端到 r≈14，中心暖黄花蕊。"""
    grid: Grid = {}
    soft_glow(grid, CENTER, CENTER, 15, L_PALE_HALO, 26)

    # 六枚等长被片：整朵旋转 8°（不跟像素网格对齐）、每枚带一点同向弯曲，
    # 让它是「一朵斜着开的花」，而不是正面朝上的雪花。
    for angle in range(-82, 278, 60):
        rad = math.radians(angle)
        stamp(grid, petal(CENTER + math.cos(rad) * 6.8, CENTER + math.sin(rad) * 6.8,
                          15.6, 16.6, angle, LILY_GRAD, a=0.34, b=0.86,
                          curves=(0.0, 2.0), base_shade=0.22, light=LILY_LIGHT))

    # 相邻被片之间的分界交给明暗（每枚被片中脉一条浅灰），不再额外画放射折缝：
    # 放射线在花冠里会读成「裂纹」，反而更脏

    silhouette_outline(grid, L_VEIN)

    # 每枚被片一道浅中脉（从花心射向瓣尖），把六瓣读出来
    for angle in range(-90, 270, 60):
        rad = math.radians(angle)
        for step in range(3, 13):
            key = (int(CENTER + math.cos(rad) * step), int(CENTER + math.sin(rad) * step))
            if key in grid and grid[key][:3] != L_SHADOW[:3]:
                put(grid, key[0], key[1], L_VEIN if step > 7 else L_WHITE)

    # 花心：暖黄底盘 + 五根伸出来的花丝，每根顶着橙褐花药——这是百合的身份证，
    # 有了它即使白色花瓣挤在一起也能一眼看出是百合
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx * dx + dy * dy <= 4:
                put(grid, CENTER + dx, CENTER + dy, L_CORE)
    put(grid, CENTER, CENTER - 1, L_PURE)
    for angle in (-120, -48, 12, 84, 156):
        rad = math.radians(angle)
        for step in range(2, 6):
            put(grid, int(CENTER + math.cos(rad) * step), int(CENTER + math.sin(rad) * step),
                L_CORE)
        tip = (int(CENTER + math.cos(rad) * 6.2), int(CENTER + math.sin(rad) * 6.2))
        put(grid, tip[0], tip[1], L_ANTHER)
        put(grid, tip[0] + 1, tip[1], L_ANTHER)
        put(grid, tip[0], tip[1] + 1, L_ANTHER)
    return to_json("lily_bloom", grid)


def build_lily_petal() -> dict:
    """单片百合被片：手调宽度表的披针形，正向摆放，两道平行浅脉收向瓣根。"""
    grid: Grid = {}
    soft_glow(grid, CENTER, CENTER, 14, L_PALE_HALO, 20)
    stamp(grid, petal(CENTER, CENTER, 25, 19, -90, (L_SHADOW, L_VEIN, L_WHITE, L_PURE, L_PURE),
                      table=LILY_PETAL_TABLE, curves=(-0.6, 2.0), side_weight=0.58))

    silhouette_outline(grid, L_VEIN)

    # 两道浅脉：从瓣尖向下收拢到瓣根，越往根部越靠中间
    for offset in (-2.4, 2.4):
        for step in range(-9, 10):
            along = (step + 12.5) / 25
            px = CENTER + offset * (1 - along) * 0.8
            py = CENTER + step
            key = (int(round(px)), int(round(py)))
            if key in grid and grid[key][:3] != L_SHADOW[:3]:
                put(grid, key[0], key[1], L_VEIN)

    put(grid, 14, 8, L_PURE)
    put(grid, 15, 7, L_PURE)
    return to_json("lily_petal", grid)


BUILDERS = [
    build_rose_bloom,
    build_rose_petal,
    build_lily_bloom,
    build_lily_petal,
]

# 上一版出过、这一版精简掉的文件（只保留花朵与花瓣）
OBSOLETE = (
    "rose_bud", "rose_petals", "rose_bramble", "rose_glow", "rose_sparkle",
    "rose_mote_0", "rose_mote_1", "rose_mote_2",
    "lily_bud", "lily_petals", "lily_stamen", "lily_glow", "lily_sparkle",
    "lily_mote_0", "lily_mote_1", "lily_mote_2",
)


def main() -> int:
    tool_dir = Path(__file__).absolute().parent
    origin = tool_dir / "origin_json"
    texture_dir = tool_dir.parent / "images"
    origin.mkdir(parents=True, exist_ok=True)
    texture_dir.mkdir(parents=True, exist_ok=True)

    for name in OBSOLETE:
        for path in (origin / f"{name}.json", texture_dir / f"{name}.png"):
            if path.exists():
                path.unlink()

    written: list[str] = []
    for builder in BUILDERS:
        data = builder()
        name = data["name"]
        json_path = origin / f"{name}.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        art = load_pixel_art(json_path)
        png_path = texture_dir / f"{name}.png"
        save_png(art, png_path, scale=1)
        written.append(f"{name}: {len(data['pixels'])} px → images/{png_path.name}")

    print(f"已生成 {len(written)} 个粒子（花朵 + 花瓣）：")
    for line in written:
        print(f"  {line}")
    print(f"\nJSON: {origin}")
    print(f"PNG:  {texture_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
