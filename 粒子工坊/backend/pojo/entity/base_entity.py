"""ORM 基类：所有实体共享的 DeclarativeBase，以及 id / 创建 / 更新时间字段。

时间统一存本机本地时间（单用户本机工具），前端直接按本地时间显示。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def local_now() -> datetime:
    return datetime.now().replace(microsecond=0)


class Base(DeclarativeBase):
    pass


class BaseEntity(Base):
    __abstract__ = True

    # SQLite 只有 INTEGER PRIMARY KEY 才自增，不能用 BigInteger
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=local_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=local_now, onupdate=local_now)
