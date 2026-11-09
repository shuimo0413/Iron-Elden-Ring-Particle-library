"""通用 Mapper 基类：按主键查询、新增、删除、刷新；具体 Mapper 继承后补充自定义查询。"""

from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from pojo.entity.base_entity import Base

E = TypeVar("E", bound=Base)


class BaseMapper(Generic[E]):
    """单表通用增删改查。只 flush 不 commit，事务由 service 决定。"""

    entity: type[E]

    def __init__(self, session: AsyncSession):
        self.session = session

    # 按主键查询实体
    async def select_by_id(self, id_: Any) -> E | None:
        return await self.session.get(self.entity, id_)

    # 新增实体（flush + refresh，不 commit）
    async def insert(self, obj: E) -> E:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    # 删除实体（只 flush）
    async def delete(self, obj: E) -> None:
        await self.session.delete(obj)
        await self.session.flush()
