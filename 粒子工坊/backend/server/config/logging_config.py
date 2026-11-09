"""日志配置：统一日志格式，级别由环境变量 LOG_LEVEL 控制（默认 INFO）。"""

import logging
import os

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format=_FORMAT)
    # 业务日志写在 controller；前端每秒轮询，压低 uvicorn access 避免刷屏
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
