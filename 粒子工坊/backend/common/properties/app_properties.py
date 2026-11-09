"""应用基础配置：应用名、环境、接口前缀、CORS 白名单、产物目录、粒子库目录。"""

from functools import lru_cache
from pathlib import Path

from common.properties.base_properties import BaseProperties
from common.utils.path_util import resolve_backend_path


class AppProperties(BaseProperties):
    app_name: str = "粒子工坊"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5175,http://127.0.0.1:5175"

    # 产物目录（数据库、checkpoint、runs/ 产物）；相对路径按 backend 根目录解析
    data_dir: str = "./data"
    # 粒子库根目录（含 images/、tool/）；粒子工坊放在 粒子库/ 内时为 ../..
    particle_library_dir: str = "../.."

    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return ["*"]
        return [x.strip() for x in raw.split(",") if x.strip()]

    def data_path(self) -> Path:
        return resolve_backend_path(self.data_dir)

    def runs_path(self) -> Path:
        return self.data_path() / "runs"

    def particle_library_path(self) -> Path:
        return resolve_backend_path(self.particle_library_dir)


@lru_cache
def get_app_properties() -> AppProperties:
    return AppProperties()
