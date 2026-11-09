"""图片逐像素取色：读图（共享脚本，统一转 RGBA 8 位）→ 尺寸上限检查 → 颜色统计 → 组装结果。不落盘。"""

from __future__ import annotations

import asyncio

from PIL import UnidentifiedImageError

from common.constant.message_constant import MessageConstant
from common.exception.biz_exceptions import InvalidParamException
from common.properties.extract_properties import ExtractProperties
from pojo.vo.extract_vo import ExtractStatsVO, ExtractVO, PaletteEntryVO
from server.calc import color_stat_calc
from server.client.particle_library_client import ParticleLibraryClient


class ExtractService:
    def __init__(self, props: ExtractProperties, library: ParticleLibraryClient) -> None:
        self.props = props
        self.library = library

    # 取色：data 为上传文件的全部字节；name 写入 JSON；min_alpha 以下的像素不写入 pixels
    async def extract(self, data: bytes, *, name: str, min_alpha: int) -> ExtractVO:
        if not data:
            raise InvalidParamException(MessageConstant.EXTRACT_FILE_EMPTY)
        if len(data) > self.props.max_upload_bytes:
            limit_mb = self.props.extract_max_upload_mb
            raise InvalidParamException(f"{MessageConstant.EXTRACT_FILE_TOO_LARGE}（上限 {limit_mb} MB）")
        try:
            probe = self.library.probe_image(data)
        except (UnidentifiedImageError, OSError) as exc:
            raise InvalidParamException(MessageConstant.EXTRACT_IMAGE_INVALID) from exc
        limit = self.props.extract_max_side_px
        if probe.width > limit or probe.height > limit:
            raise InvalidParamException(
                f"{MessageConstant.EXTRACT_IMAGE_TOO_LARGE}：{probe.width}×{probe.height}，上限 {limit}×{limit}"
            )
        return await asyncio.to_thread(self._extract_sync, data, name, min_alpha, probe.mode, probe.animated)

    def _extract_sync(self, data: bytes, name: str, min_alpha: int, mode: str, animated: bool) -> ExtractVO:
        width, height, grid = self.library.load_rgba_grid(data)
        art = self.library.grid_to_pixel_art(name, width, height, grid, min_alpha=min_alpha)
        palette = color_stat_calc.build_palette(grid, min_alpha=min_alpha)
        return ExtractVO(
            art=art,
            palette=[
                PaletteEntryVO(rgba=list(entry.rgba), hex=entry.hex, count=entry.count, first_index=entry.first_index)
                for entry in palette
            ],
            stats=ExtractStatsVO(
                source_mode=mode,
                animated=animated,
                width=width,
                height=height,
                written_pixels=len(art["pixels"]),
                total_pixels=width * height,
                unique_colors=len(palette),
                semi_transparent_pixels=color_stat_calc.count_semi_transparent(grid, min_alpha=min_alpha),
            ),
        )
