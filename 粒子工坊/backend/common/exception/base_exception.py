"""业务异常基类：只携带提示文案，由全局异常处理器统一转换为 HTTP 200 + code=1。"""


class BizException(Exception):
    """业务异常基类（Python 内置已有 BaseException，故命名为 BizException）。"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
