# Iron's Spells: Elden Ring — Particle Library

[中文](README.md) | **English**

- Particle library of the Minecraft mod **"Iron's Spells 'n Spellbooks: Elden Ring"**. It stores original pixel-art particle PNGs and can also be used on its own as a general-purpose particle texture pack.
- Most particles are **32×32**; the sigil family `sigil_*` is **64×64** (32×32 cannot fit the three-layer structure of outer ring + tick band + inner ring — glyphs would be squeezed into 4×4 px and stop reading as a magic circle).
- Repository: https://github.com/shuimo0413/Iron-Elden-Ring-Particle-library

## Relationship with the main project

This folder lives in the parent directory of the dual-version workspace (next to `工具链/` (toolchain) and `模型/` (models)). Both the Forge 1.20.1 and NeoForge 1.21.1 projects mount it as `粒子库/` via a Windows **junction**, so:

1. Put new particle PNGs directly into this folder;
2. When a particle is needed in-game, copy it into the target project's `assets/iss_elden_ring/textures/particle/`;
3. For the showcase image, see `tool/gen_particle_showcase.py` below (files are laid out in ascending filename order; no script changes required).

![Particle library preview](粒子库预览.png)

## Particle families

Files are grouped by filename prefix, for example:

| Prefix | Theme |
|---|---|
| `carian_*`, `glintstone_*`, `comet_azur_*` | Carian / glintstone sorcery (blue) |
| `gravity_*`, `void_*`, `nebula_*`, `star_*` | Gravity, void and astral effects |
| `frost_*` | Frost magic |
| `holy_*` | Holy golden light |
| `ember_*`, `flame_*` | Fire and embers |
| `nature_*` | Nature / life |

Numbered files such as `*_mote_0/1/2.png` or `*_ripple_0/1/2.png` are animation frames or size variants of the same particle.

## Sigil family (64×64, `sigil_*`)

Six spell-agnostic magic circles meant to be tinted at runtime. Shared composition rules: the outer silhouette must stay a large circle (gaps allowed); asymmetry only comes from tick spacing, spoke length, gap angles and off-center rings; a 2 px transparent margin prevents atlas bleeding.

| File | Structure | Main asymmetry |
|---|---|---|
| `sigil_arcane` | Double outer ring + 24 ticks + dashed inner ring + hollow center triangle | Ticks rotated 7°, third diamond glyph shifted 11° |
| `sigil_frost` | Hexagram (two triangles) + inner hexagon + center snowflake | Six ring gaps offset 13° from the tips, widths 4.5°–9° |
| `sigil_ember` | Multi-segment broken ring + 13-tooth trapezoid gear + diamond flame core | Six gap widths from 6° to 21°, unequal tooth heights |
| `sigil_verdant` | Sine-perturbed vine ring + 7 leaf buds + five-petal core | Dual-frequency vine, leaf length 2–4 px randomized |
| `sigil_void` | Three rings with individual off-centers + 9 unequal spokes | Rings 2 and 3 shifted 1.5 px each, hollow center |
| `sigil_gold` | 268° main arc + detached arc fragment + golden-angle rays | Rays spaced by 137.508°, randomized length |

Regenerating (pixel data lives in the script, output is deterministic):

```powershell
cd tool
python gen_sigil_particles.py
```

> Particles are billboards (always facing the camera), so they can only serve as *standing* sigils. For a ground-projected magic circle use a quad-based entity renderer (see `TerraMagicaZoneRenderer` in the main project) and let particles handle only the rim accents.

## tool/ — pixel JSON ↔ PNG / showcase image

Pixel JSON format: `name`, `width`, `height`, `pixels` (each entry has `x` / `y` / `rgba: [R, G, B, A]`).

`tool/origin_json/` holds the source pixel JSON for some particles, and the `tool/gen_*_particles.py` scripts procedurally generate particle families (frost, holy, fire, nature) and export them to PNG.

### `render_pixel_art.py` — JSON → PNG

Have an LLM (or a human) produce pixel JSON following the format above, then assemble the PNG with this script.

```powershell
# Adding a particle to the library: logical pixels 1:1, do not upscale
python tool/render_pixel_art.py my_particle.json --png-scale 1 -o my_particle.png

# Enlarged console preview (default --png-scale 16, good for inspecting structure)
python tool/render_pixel_art.py my_particle.json -s 2
```

### `extract_image_rgba.py` — image → JSON

Extracts every RGBA pixel from an existing PNG (or any format Pillow can read) into JSON in the same format. Fully transparent pixels (`A == 0`) are skipped by default.

```powershell
python tool/extract_image_rgba.py glintstone_spark.png
python tool/extract_image_rgba.py glintstone_spark.png -o spark.json --unique
# Keep fully transparent pixels: --min-alpha 0
```

In the main project, the old `工具链/render_pixel_art.py` remains as a compatibility entry point (it forwards to this file), so existing `gen_*` scripts need no changes.

### `gen_particle_showcase.py` — all PNGs → showcase image

Scans every `*.png` in the library root (automatically excluding `粒子库预览.png`), arranges them in **ascending filename order** into one showcase image, and writes `粒子库预览.png`. There is no family grouping; just rerun it after adding new particles.

```powershell
# From the particle library root
python tool/gen_particle_showcase.py

# Or from either project root (compatibility forwarder)
python 工具链/gen_particle_showcase.py
```

Requires Python 3 and [Pillow](https://pypi.org/project/pillow/).

## License

This library (particle PNGs and `tool/` scripts) is released under the [MIT License](LICENSE).
