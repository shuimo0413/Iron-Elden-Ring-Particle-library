"""具体业务异常：仅用于在代码中区分语义，响应统一为 HTTP 200 + code=1。

不存在 / 状态冲突 / 参数不合法 / 外部依赖未配置或失败。
"""

from common.exception.base_exception import BizException


class NotFoundException(BizException):
    pass


class ConflictException(BizException):
    pass


class InvalidParamException(BizException):
    pass


class NotConfiguredException(BizException):
    pass


class BadGatewayException(BizException):
    pass
