"""粒子库文件读写，以及对 粒子库/tool/ 共享脚本的调用。

- 出图：render_pixel_art.load_pixel_art / save_png
- 取色：extract_image_rgba.load_rgba_grid / grid_to_pixel_art
- 总览图：gen_particle_showcase.main

共享脚本按文件路径加载（不改 sys.path），保证命令行与 Web 结果一致。
粒子 PNG 在 images/，标准像素 JSON 在 tool/origin_json/。
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image


@contextmanager
def no_bytecode() -> Iterator[None]:
    """加载 / 运行共享脚本期间不写 __pycache__，避免往粒子库仓库里留 .pyc。"""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        yield
    finally:
        sys.dont_write_bytecode = previous


@dataclass
class ImageProbe:
    mode: str
    width: int
    height: int
    animated: bool


@dataclass
class ParticleFile:
    name: str
    width: int
    height: int
    has_json: bool
    modified_at: float


class ParticleLibraryClient:
    def __init__(self, library_dir: Path) -> None:
        self.library_dir = library_dir
        self.images_dir = library_dir / "images"
        self.origin_json_dir = library_dir / "tool" / "origin_json"
        self.tool_dir = library_dir / "tool"
        self.showcase_path = library_dir / "粒子库预览.png"
        self._modules: dict[str, ModuleType] = {}
        # 入库与重建总览图串行，避免两个任务同时写同名文件
        self._write_lock = threading.Lock()

    # —— 共享脚本 ——

    def _tool(self, module_name: str) -> ModuleType:
        module = self._modules.get(module_name)
        if module is None:
            path = self.tool_dir / f"{module_name}.py"
            spec = importlib.util.spec_from_file_location(f"particle_tool_{module_name}", path)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法加载共享脚本 {path}")
            module = importlib.util.module_from_spec(spec)
            with no_bytecode():
                spec.loader.exec_module(module)
            self._modules[module_name] = module
        return module

    # —— 出图 ——

    def render_png(self, art_json_path: Path, output_path: Path, scale: int) -> Path:
        """标准像素 JSON 文件 → PNG（最近邻放大 scale 倍）。"""
        renderer = self._tool("render_pixel_art")
        art = renderer.load_pixel_art(art_json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return renderer.save_png(art, output_path, scale=scale)

    # —— 取色 ——

    def probe_image(self, data: bytes) -> ImageProbe:
        """只读文件头：模式、尺寸、是否动图；不解码全部像素。"""
        with Image.open(io.BytesIO(data)) as image:
            return ImageProbe(
                mode=image.mode,
                width=image.width,
                height=image.height,
                animated=bool(getattr(image, "is_animated", False)),
            )

    def load_rgba_grid(self, data: bytes) -> tuple[int, int, list[list[tuple[int, int, int, int]]]]:
        return self._tool("extract_image_rgba").load_rgba_grid(io.BytesIO(data))

    def grid_to_pixel_art(self, name: str, width: int, height: int, grid, *, min_alpha: int) -> dict[str, Any]:
        return self._tool("extract_image_rgba").grid_to_pixel_art(name, width, height, grid, min_alpha=min_alpha)

    # —— 库浏览 ——

    def list_names(self) -> set[str]:
        """库内已占用的名字：images/*.png 与 origin_json/*.json 的文件名。"""
        names = {path.stem for path in self.images_dir.glob("*.png")}
        names.update(path.stem for path in self.origin_json_dir.glob("*.json"))
        return names

    def list_particles(self) -> list[ParticleFile]:
        json_names = {path.stem for path in self.origin_json_dir.glob("*.json")}
        files: list[ParticleFile] = []
        for path in sorted(self.images_dir.glob("*.png")):
            with Image.open(path) as image:
                width, height = image.size
            files.append(ParticleFile(path.stem, width, height, path.stem in json_names, path.stat().st_mtime))
        return files

    def particle_png_path(self, name: str) -> Path:
        return self.images_dir / f"{name}.png"

    def read_particle_art(self, name: str) -> tuple[dict[str, Any], bool]:
        """优先读 origin_json；没有则从 PNG 现取。返回 (标准像素 JSON, 是否来自 json)。"""
        json_path = self.origin_json_dir / f"{name}.json"
        if json_path.is_file():
            return json.loads(json_path.read_text(encoding="utf-8")), True
        width, height, grid = self._tool("extract_image_rgba").load_rgba_grid(self.particle_png_path(name))
        return self.grid_to_pixel_art(name, width, height, grid, min_alpha=1), False

    # —— 入库 ——

    def publish(self, name: str, art: dict[str, Any]) -> str:
        """写 tool/origin_json/<name>.json 与 images/<name>.png（1:1）；同名已存在时抛 FileExistsError。"""
        with self._write_lock:
            if name in self.list_names():
                raise FileExistsError(name)
            stored = {**art, "name": name}
            json_path = self.origin_json_dir / f"{name}.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.render_png(json_path, self.particle_png_path(name), scale=1)
            return name

    def rebuild_showcase(self) -> int:
        """重跑 gen_particle_showcase，返回参与总览的粒子数。耗时数秒，调用方放线程里跑。"""
        with self._write_lock:
            showcase = self._tool("gen_particle_showcase")
            with no_bytecode():
                showcase.main()
            return len(showcase.list_particle_pngs())
