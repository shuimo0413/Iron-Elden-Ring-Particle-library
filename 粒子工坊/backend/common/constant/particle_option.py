"""生成按钮选项：类别、色调（含暗到亮锚点颜色）、描边、对称、变体数，以及推荐联动与风格倾向。

前端通过 GET /options 拉取后渲染，加按钮只改这里。
"""

from __future__ import annotations

from dataclasses import dataclass, field

AUTO = "auto"


@dataclass(frozen=True)
class OptionItem:
    value: str
    label: str
    # 写进提示词的说明；「自动」项为空，提示词里显示「由模型根据描述决定」
    prompt_text: str = ""
    # 色调专用：暗到亮的锚点颜色 (R, G, B)
    anchors: tuple[tuple[int, int, int], ...] = field(default_factory=tuple)


CATEGORY_OPTIONS: tuple[OptionItem, ...] = (
    OptionItem(AUTO, "自动"),
    OptionItem("spark", "火花", "火花 / 星点：小而亮的核心 + 短促的放射尖角"),
    OptionItem("glow", "光晕", "光晕：中心亮、向外衰减的柔和光团，边缘可用半透明"),
    OptionItem("sigil", "法阵", "法阵：外圈大圆 + 刻度 / 符文带 + 中心图案的几何阵形"),
    OptionItem("flower", "花朵", "花朵：花瓣围绕花心排布，可带一两片叶子"),
    OptionItem("food", "食物", "食物：可辨认的食物剪影，像游戏物品图标"),
    OptionItem("item", "物品", "物品：道具 / 器物剪影，像游戏物品图标"),
    OptionItem("other", "其他", "其他：按描述自由发挥"),
)

PALETTE_OPTIONS: tuple[OptionItem, ...] = (
    OptionItem(AUTO, "自动"),
    OptionItem("cold_blue", "冷蓝", "冷蓝", ((24, 40, 82), (58, 96, 168), (120, 180, 255), (214, 240, 255))),
    OptionItem("crimson", "炽红", "炽红", ((70, 14, 18), (150, 34, 28), (236, 96, 48), (255, 214, 150))),
    OptionItem("gold", "金色", "金色", ((72, 46, 14), (150, 104, 30), (230, 182, 64), (255, 240, 180))),
    OptionItem("purple", "紫", "紫", ((40, 18, 64), (96, 48, 150), (170, 110, 230), (236, 210, 255))),
    OptionItem("green", "绿", "绿", ((18, 52, 30), (40, 112, 58), (110, 190, 90), (210, 246, 170))),
    OptionItem("grey_white", "灰白", "灰白", ((40, 42, 50), (100, 104, 116), (176, 180, 190), (244, 246, 250))),
)

OUTLINE_OPTIONS: tuple[OptionItem, ...] = (
    OptionItem("dark", "暗色剪影描边", "只给剪影外轮廓描一圈比相邻内部更暗的颜色，内部不描线"),
    OptionItem("none", "无描边", "不描边，靠明暗区分形状"),
)

SYMMETRY_OPTIONS: tuple[OptionItem, ...] = (
    OptionItem("none", "无", "不要求对称"),
    OptionItem("mirror_x", "左右镜像", "左右镜像对称（以竖直中线为轴，形状对称，明暗可按左上受光略有差别）"),
    OptionItem("rotational", "旋转对称", "90° 旋转对称（转 90° 后形状重合，明暗可略有差别）"),
)

VARIANT_COUNT_OPTIONS: tuple[int, ...] = (1, 2, 3, 4)

DEFAULT_OPTIONS: dict[str, object] = {
    "size": 32,
    "category": AUTO,
    "palette": AUTO,
    "outline": "dark",
    "symmetry": "none",
    "variants": 2,
}

# 联动只提示不强制：选中某类别时，在推荐的按钮旁显示「推荐」
RECOMMENDATIONS: dict[str, dict[str, dict[str, object]]] = {
    "category": {
        "sigil": {"size": 64, "symmetry": "rotational"},
    },
}

# 多个变体各自追加不同的风格倾向，避免几份结果雷同；按变体序号取用
STYLE_HINTS: tuple[str, ...] = (
    "偏简洁：形状干净，颜色档位少，留白多",
    "偏华丽：细节更丰富，可以多一层装饰",
    "偏柔和：明暗过渡平缓，边缘可用少量半透明",
    "偏锐利：对比强烈，尖角和硬边更多",
)


def option_values(options: tuple[OptionItem, ...]) -> frozenset[str]:
    return frozenset(item.value for item in options)


def find_option(options: tuple[OptionItem, ...], value: str) -> OptionItem | None:
    for item in options:
        if item.value == value:
            return item
    return None
