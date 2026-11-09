"""提示词模板：系统提示词、硬性约束段、重试 / 打回模板。

放常量而不是 .md 文件：calc 层不能读文件，放这里 prompt_calc 才能保持纯函数。
"""

AUTO_TEXT = "由模型根据描述决定"

COMPACT_FORMAT_EXAMPLE = """{
  "name": "tiny_spark",
  "width": 8,
  "height": 8,
  "palette": {
    "a": [40, 60, 120, 255],
    "b": [120, 180, 255, 255],
    "c": [230, 245, 255, 255]
  },
  "rows": [
    "........",
    "...a....",
    "..aba...",
    ".abcba..",
    "..aba...",
    "...a....",
    "........",
    "........"
  ]
}"""

SYSTEM_PROMPT = f"""你是一名 Minecraft 粒子像素画师，只输出一个 json 对象，不要输出任何解释文字或代码块标记。

## 输出格式（紧凑像素 json）
- name：snake_case 英文名，只含小写字母、数字、下划线。
- width / height：必须等于要求的尺寸。
- palette：调色板对象。键是单个可见字符（不能是 "." 或空白），值是 [R, G, B, A]，每项 0–255 的整数。
- rows：共 height 行字符串，每行恰好 width 个字符；"." 固定表示透明，其余字符必须是 palette 里的键。
- 输出前逐行数一遍字符数，确保每行长度都等于 width、行数等于 height。

8×8 示例：
{COMPACT_FORMAT_EXAMPLE}

## 美术规则
1. 粒子是 billboard（永远面向镜头），背景不固定，所以剪影本身要清楚，不要画背景。
2. 调色板按暗到亮分档，饱和度克制，不要每个像素都换颜色。
3. 只给剪影外轮廓描暗边（若要求描边），内部不描线。
4. 光源在左上：左上偏亮，右下偏暗。
5. 四周留出要求宽度的透明边，防止图集相邻贴图渗色。
6. 少用孤立的单个像素点，同色像素尽量成块。"""

USER_PROMPT_TEMPLATE = """【硬性约束】
尺寸：{size}×{size}；透明边：{margin_text}；颜色上限：{max_colors}
类别：{category_text}
色调：{palette_text}
描边：{outline_text}
对称：{symmetry_text}

【画法指南】
{guide}

【用户描述】
{description}"""

STYLE_HINT_TEMPLATE = "\n\n【风格倾向】\n{style_hint}"

MARGIN_TEXT_TEMPLATE = "四周 {margin}px 内不得有像素"
MARGIN_NONE_TEXT = "无（8×8 可以画满）"
PALETTE_ANCHOR_TEMPLATE = "{label}，暗到亮锚点 {anchors}"

RETRY_HEADER = "上一次输出的问题："
RETRY_FOOTER = "请输出修正后的完整 json。"
HUMAN_FEEDBACK_LABEL = "设计者意见（优先）："

SIZE_CONFLICT_NOTE = "已忽略描述中的尺寸 {found}，按按钮选择的 {size}×{size} 生成"
