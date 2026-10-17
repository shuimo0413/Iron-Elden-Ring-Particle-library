# 铁魔法：艾尔登法环粒子库

**中文** | [English](README.en.md)

- 这是 mcmod「Iron的法术与魔法书：艾尔登法环」的粒子库，存放原创粒子 PNG，可单独当作通用粒子素材库使用。
- 粒子分辨率大多为 **32×32**；法阵系列 `sigil_*` 为 **64×64**（32×32 放不下「外环 + 刻度带 + 内环」三层结构，符文只剩 4×4 像素，读不出阵形）。
- 仓库：https://github.com/shuimo0413/Iron-Elden-Ring-Particle-library

## 与主工程的关系

本目录位于双版本工作区父文件夹（与 `工具链/`、`模型/` 并列）。Forge / NeoForge 两个工程通过 **junction** 挂载同名 `粒子库/`，因此：

1. 新粒子 PNG 直接放进本目录；
2. 需要进游戏时，再拷到对应工程的 `assets/iss_elden_ring/textures/particle/`；
3. 宣传总览图：见下方 `tool/gen_particle_showcase.py`（按文件名升序铺开，无需改脚本）。

![粒子库预览](粒子库预览.png)

## 法阵系列（64×64，`sigil_*`）

不绑法术属性、可通用染色的六张法阵。共同构图规则：外轮廓必须是大圆（允许缺口），不对称只体现在刻度间距、辐条长短、缺口角度、环心偏移；四周留 2px 透明边防图集渗色。

| 文件 | 结构 | 主要不对称点 |
|---|---|---|
| `sigil_arcane` | 外双环 + 24 刻度 + 虚线内环 + 中心空心三角 | 刻度整体偏 7°，第三枚菱形符文偏 11° |
| `sigil_frost` | 六芒星（双三角）+ 内六边形 + 中心雪花 | 外环 6 处缺口错开尖角 13°，宽度 4.5°~9° |
| `sigil_ember` | 多段断环 + 13 齿梯形锯齿轮 + 中心菱形焰 | 6 处缺口宽度 6°~21°，齿高不等 |
| `sigil_verdant` | 正弦扰动藤蔓环 + 7 片叶芽 + 五瓣花心 | 藤蔓双频起伏，叶片长度 2~4px 随机 |
| `sigil_void` | 三层圆环各自偏心 + 九根不等长辐条 | 二三环环心各偏 1.5px，中心留空 |
| `sigil_gold` | 268° 主弧 + 独立残弧 + 黄金角芒线 | 芒线按 137.508° 排布，长度随机 |

生成方式（像素数据写在脚本里，重跑结果完全一致）：

```powershell
cd tool
python gen_sigil_particles.py
```

> 粒子是 billboard（永远面向摄像机），只能做「立着」的法阵。贴地法阵请走实体四边形渲染（参考主工程 `TerraMagicaZoneRenderer`），粒子只负责外沿点缀。

## tool/ — 像素 JSON ↔ PNG / 总览图

JSON 字段：`name`、`width`、`height`、`pixels`（每项含 `x` / `y` / `rgba:[R,G,B,A]`）。

### `render_pixel_art.py` — JSON → PNG

先让大语言模型（或人工）按约定输出像素化 JSON，再用脚本组装 PNG。

```powershell
# 粒子入库：逻辑像素 1:1，不要放大
python tool/render_pixel_art.py my_particle.json --png-scale 1 -o my_particle.png

# 控制台预览放大（默认 --png-scale 16，适合看清结构）
python tool/render_pixel_art.py my_particle.json -s 2
```

### `extract_image_rgba.py` — 图片 → JSON

从现有 PNG（或其它 Pillow 可读格式）抽出全部 RGBA，写成同上格式的 JSON。默认跳过 `A==0` 的透明像素。

```powershell
python tool/extract_image_rgba.py glintstone_spark.png
python tool/extract_image_rgba.py glintstone_spark.png -o spark.json --unique
# 保留全透明像素：--min-alpha 0
```

主工程里旧的 `工具链/render_pixel_art.py` 仍是兼容入口（转发到本文件），现有 `gen_*` 脚本不用改。

### `gen_particle_showcase.py` — 全部 PNG → 总览大图

扫描本库根目录全部 `*.png`（自动排除 `粒子库预览.png`），按**文件名字符升序**排成一张宣传图，输出 `粒子库预览.png`。不加系列分组，新粒子入库后直接重跑即可。

```powershell
# 在粒子库根目录
python tool/gen_particle_showcase.py

# 或在任一工程根（兼容转发）
python 工具链/gen_particle_showcase.py
```

## 许可证

本库（粒子 PNG 与 `tool/` 脚本）以 [MIT License](LICENSE) 发布。
