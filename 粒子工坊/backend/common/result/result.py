"""统一返回体 Result：code=0 表示成功，code=1 表示业务失败；data 为泛型业务数据。"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None

    @classmethod
    def success(cls, data: T | None = None, message: str = "ok") -> "Result[T]":
        return cls(data=data, message=message)

    @classmethod
    def error(cls, message: str, code: int = 1, data: T | None = None) -> "Result[T]":
        return cls(code=code, message=message, data=data)
