"""全局异常处理：所有异常一律 HTTP 200 + {code: 1, message, data}，前端只认 code（0 成功 / 1 失败）。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.exception.base_exception import BizException
from common.result.result import Result

log = logging.getLogger(__name__)


def _fail(message: str, data: Any = None) -> JSONResponse:
    body = Result.error(message, data=data).model_dump()
    return JSONResponse(status_code=200, content=jsonable_encoder(body))


async def _biz_handler(request: Request, exc: BizException) -> JSONResponse:
    log.warning("业务失败 %s %s: %s", request.method, request.url.path, exc.message)
    return _fail(exc.message)


_HTTP_MESSAGES = {404: "接口不存在", 405: "请求方法不支持"}


async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    message = _HTTP_MESSAGES.get(exc.status_code) or (detail if isinstance(detail, str) else str(detail))
    log.warning("HTTP异常 %s %s: %s", request.method, request.url.path, message)
    return _fail(message)


def _validation_message(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "请求参数校验失败"
    first = errors[0]
    loc = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path"))
    msg = first.get("msg", "")
    return f"请求参数校验失败：{loc} {msg}".strip() if loc else f"请求参数校验失败：{msg}"


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # 不回显 input：手改像素数组可能很大
    errors = jsonable_encoder([{k: v for k, v in error.items() if k not in ("input", "ctx")} for error in exc.errors()])
    message = _validation_message(errors)
    log.warning("参数校验失败 %s %s: %s", request.method, request.url.path, message)
    return _fail(message, data=errors)


async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error: %s", exc)
    return _fail("服务器内部错误")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BizException, _biz_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
