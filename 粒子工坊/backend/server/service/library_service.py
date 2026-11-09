"""粒子库浏览：列表（关键字 / 系列前缀过滤）、单个粒子详情、手动重建总览图。

入库由工作流 publish 节点完成（同一个 ParticleLibraryClient）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from common.constant.library_constant import LIBRARY_URL_SEGMENT, PARTICLE_NAME_PATTERN, SHOWCASE_URL_PATH
from common.constant.message_constant import MessageConstant
from common.exception.biz_exceptions import InvalidParamException, NotFoundException
from common.properties.app_properties import AppProperties
from pojo.vo.library_vo import ParticleDetailVO, ParticleItemVO, ShowcaseVO
from server.client.particle_library_client import ParticleFile, ParticleLibraryClient


def series_of(name: str) -> str:
    """文件名第一个下划线前的前缀；没有下划线时就是文件名本身。"""
    return name.split("_", 1)[0]


class LibraryService:
    def __init__(self, props: AppProperties, library: ParticleLibraryClient) -> None:
        self.props = props
        self.library = library

    # 粒子列表：q 按名称包含过滤（不分大小写），series 按前缀精确过滤
    async def list(self, q: str | None, series: str | None) -> list[ParticleItemVO]:
        files = await asyncio.to_thread(self.library.list_particles)
        keyword = (q or "").strip().lower()
        items = []
        for file in files:
            if keyword and keyword not in file.name.lower():
                continue
            if series and series_of(file.name) != series:
                continue
            items.append(self._item_vo(file))
        return items

    # 单个粒子：尺寸、PNG 地址、标准像素 JSON
    async def detail(self, name: str) -> ParticleDetailVO:
        if not PARTICLE_NAME_PATTERN.match(name):
            raise InvalidParamException(MessageConstant.PARTICLE_NAME_INVALID)
        png_path = self.library.particle_png_path(name)
        if not png_path.is_file():
            raise NotFoundException(MessageConstant.PARTICLE_NOT_FOUND)
        art, has_json = await asyncio.to_thread(self.library.read_particle_art, name)
        file = ParticleFile(name, int(art["width"]), int(art["height"]), has_json, png_path.stat().st_mtime)
        return ParticleDetailVO(**self._item_vo(file).model_dump(), art=art)

    # 手动重建总览图
    async def rebuild_showcase(self) -> ShowcaseVO:
        count = await asyncio.to_thread(self.library.rebuild_showcase)
        return ShowcaseVO(url=self.showcase_url(), particle_count=count)

    def showcase_url(self) -> str:
        return f"{self.props.api_prefix}{SHOWCASE_URL_PATH}"

    # 总览图文件路径（粒子库根目录下的 粒子库预览.png）
    def showcase_path(self) -> Path:
        return self.library.showcase_path

    def _item_vo(self, file: ParticleFile) -> ParticleItemVO:
        return ParticleItemVO(
            name=file.name,
            series=series_of(file.name),
            width=file.width,
            height=file.height,
            png_url=f"{self.props.api_prefix}{LIBRARY_URL_SEGMENT}/{file.name}.png",
            has_json=file.has_json,
            modified_at=file.modified_at,
        )
