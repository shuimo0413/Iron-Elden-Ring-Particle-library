"""存储配置：业务库（SQLite 异步）地址、LangGraph checkpoint 库路径、是否自动建表。"""

from functools import lru_cache

from common.properties.base_properties import BaseProperties
from common.utils.path_util import resolve_backend_path

_SQLITE_PREFIX = "sqlite+aiosqlite:///"


class DbProperties(BaseProperties):
    # 相对路径（./data/app.sqlite）按 backend 根目录解析，不依赖启动目录
    database_url: str = "sqlite+aiosqlite:///./data/app.sqlite"
    checkpoint_db_path: str = "./data/checkpoints.sqlite"
    db_auto_create: bool = True

    def resolved_database_url(self) -> str:
        url = self.database_url
        if not url.startswith(_SQLITE_PREFIX):
            return url
        raw_path = url[len(_SQLITE_PREFIX):]
        if raw_path == ":memory:":
            return url
        return f"{_SQLITE_PREFIX}{resolve_backend_path(raw_path).as_posix()}"

    def resolved_checkpoint_path(self) -> str:
        return str(resolve_backend_path(self.checkpoint_db_path))


@lru_cache
def get_db_properties() -> DbProperties:
    return DbProperties()
