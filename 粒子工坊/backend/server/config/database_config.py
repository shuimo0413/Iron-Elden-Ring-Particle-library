"""业务库（SQLite + aiosqlite）的 engine 与 session 工厂；连接时开启 WAL，减少轮询读与后台写的互相阻塞。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from common.properties.db_properties import DbProperties, get_db_properties

_SQLITE_FILE_PREFIX = "sqlite+aiosqlite:///"


def _enable_sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


class DatabaseManager:
    def __init__(self, props: DbProperties):
        url = props.resolved_database_url()
        if url.startswith(_SQLITE_FILE_PREFIX) and ":memory:" not in url:
            Path(url[len(_SQLITE_FILE_PREFIX):]).parent.mkdir(parents=True, exist_ok=True)
        self.engine: AsyncEngine = create_async_engine(url, echo=False)
        if url.startswith("sqlite"):
            event.listen(self.engine.sync_engine, "connect", _enable_sqlite_pragmas)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )

    async def create_all(self) -> None:
        import pojo.entity  # noqa: F401  注册全部实体
        from pojo.entity.base_entity import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()


_manager: DatabaseManager | None = None


def get_database() -> DatabaseManager:
    """进程内唯一的连接管理器；首次使用时按配置创建。"""
    global _manager
    if _manager is None:
        _manager = DatabaseManager(get_db_properties())
    return _manager


async def close_database() -> None:
    global _manager
    if _manager is not None:
        await _manager.dispose()
        _manager = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_database().session_factory() as session:
        yield session
