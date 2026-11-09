"""POST /extract：各种颜色格式统一成 RGBA 8 位，结果与命令行脚本一致；尺寸 / 文件校验。"""

import importlib.util
import io
from pathlib import Path

import httpx
import pytest
from PIL import Image

from server.client.particle_library_client import no_bytecode
from server.main import app
from tests.support_paths import REAL_LIBRARY_DIR

_spec = importlib.util.spec_from_file_location("cli_extract", REAL_LIBRARY_DIR / "tool" / "extract_image_rgba.py")
cli_extract = importlib.util.module_from_spec(_spec)
with no_bytecode():
    _spec.loader.exec_module(cli_extract)


def _png_bytes(image: Image.Image, fmt: str = "PNG", **save_kwargs) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


async def _extract(data: bytes, filename: str = "sample.png", **form) -> dict:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/extract", files={"file": (filename, data, "application/octet-stream")}, data=form
        )
    assert response.status_code == 200
    return response.json()


def _pixel(body: dict, x: int, y: int) -> list[int] | None:
    for pixel in body["data"]["art"]["pixels"]:
        if pixel["x"] == x and pixel["y"] == y:
            return pixel["rgba"]
    return None


@pytest.mark.parametrize("png", sorted((REAL_LIBRARY_DIR / "images").glob("*.png"))[:5], ids=lambda p: p.name)
async def test_library_png_matches_cli(png: Path):
    body = await _extract(png.read_bytes(), png.name)
    assert body["code"] == 0
    width, height, grid = cli_extract.load_rgba_grid(png)
    expected = cli_extract.grid_to_pixel_art(png.stem, width, height, grid, min_alpha=1)
    assert body["data"]["art"] == expected
    stats = body["data"]["stats"]
    assert stats["unique_colors"] == len(cli_extract.collect_unique_rgba(grid, min_alpha=1))
    assert sum(entry["count"] for entry in body["data"]["palette"]) == stats["written_pixels"]


async def test_rgb_jpg_gets_full_alpha():
    image = Image.new("RGB", (4, 4), (200, 100, 50))
    body = await _extract(_png_bytes(image, "JPEG", quality=100), "photo.jpg")
    assert body["code"] == 0
    assert body["data"]["stats"]["source_mode"] == "RGB"
    assert body["data"]["stats"]["written_pixels"] == 16
    assert all(pixel["rgba"][3] == 255 for pixel in body["data"]["art"]["pixels"])


async def test_palette_png_transparency_index():
    image = Image.new("P", (2, 1))
    image.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
    image.putpixel((0, 0), 0)
    image.putpixel((1, 0), 1)
    body = await _extract(_png_bytes(image, transparency=0), min_alpha="0")
    assert body["data"]["stats"]["source_mode"] == "P"
    assert _pixel(body, 0, 0) == [255, 0, 0, 0]
    assert _pixel(body, 1, 0) == [0, 255, 0, 255]


async def test_16bit_gray_is_scaled_not_clipped():
    image = Image.new("I;16", (2, 1))
    image.putpixel((0, 0), 40000)
    image.putpixel((1, 0), 100)
    body = await _extract(_png_bytes(image), min_alpha="0")
    assert _pixel(body, 0, 0) == [156, 156, 156, 255]
    assert _pixel(body, 1, 0) == [0, 0, 0, 255]


async def test_gray_alpha_keeps_alpha():
    image = Image.new("LA", (1, 1), (90, 120))
    body = await _extract(_png_bytes(image))
    assert _pixel(body, 0, 0) == [90, 90, 90, 120]
    assert body["data"]["stats"]["semi_transparent_pixels"] == 1


async def test_animated_gif_uses_first_frame():
    frames = [Image.new("RGB", (2, 2), color) for color in ((255, 0, 0), (0, 0, 255))]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:])
    body = await _extract(buffer.getvalue(), "anim.gif")
    assert body["code"] == 0 and body["data"]["stats"]["animated"] is True


async def test_custom_name_and_min_alpha():
    image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    image.putpixel((1, 0), (1, 2, 3, 40))
    body = await _extract(_png_bytes(image), name="custom", min_alpha="50")
    assert body["data"]["art"]["name"] == "custom"
    assert body["data"]["art"]["pixels"] == []


async def test_too_large_and_invalid_images_fail():
    big = await _extract(_png_bytes(Image.new("RGBA", (513, 2))))
    assert big["code"] == 1 and "尺寸超出上限" in big["message"]
    invalid = await _extract(b"not an image")
    assert invalid["code"] == 1 and invalid["message"] == "无法识别的图片文件"
