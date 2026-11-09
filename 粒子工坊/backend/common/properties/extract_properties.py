"""功能二取色配置：图片边长上限与上传大小上限。"""

from functools import lru_cache

from common.properties.base_properties import BaseProperties


class ExtractProperties(BaseProperties):
    # 单边像素上限；调大会让返回 JSON 急剧变大（512×512 已是 26 万像素）
    extract_max_side_px: int = 512
    extract_max_upload_mb: int = 10

    @property
    def max_upload_bytes(self) -> int:
        return self.extract_max_upload_mb * 1024 * 1024


@lru_cache
def get_extract_properties() -> ExtractProperties:
    return ExtractProperties()
