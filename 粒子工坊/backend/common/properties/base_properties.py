"""配置基类：统一从 backend/.env（及 .env.{APP_ENV}）与环境变量读取，忽略未声明的键。

.env 按 backend 根目录定位，不依赖启动时的工作目录。
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from common.utils.path_util import BACKEND_ROOT


def _env_files() -> tuple[str, ...]:
    """.env 为公共配置；APP_ENV=dev 时再叠加 .env.dev（后者覆盖前者）。"""
    files = [str(BACKEND_ROOT / ".env")]
    env = os.getenv("APP_ENV", "").strip()
    if env:
        files.append(str(BACKEND_ROOT / f".env.{env}"))
    return tuple(files)


class BaseProperties(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )
