import logging
import sys
from typing import List, Callable
from typing_extensions import Protocol

class LogState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.listeners: List[Callable[[str], None]] = []
            cls._instance.temp_logs: List[str] = []
        return cls._instance

class LogListener(Protocol):
    def __call__(self, log_message: str) -> None: ...

class CustomHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record):
        log_message = self.format(record)
        state = LogState()
        state.temp_logs.append(log_message)
        for listener in state.listeners:
            listener(log_message)

def _reset_logger(log):
    # 清除现有处理器避免重复
    for handler in log.handlers[:]:
        log.removeHandler(handler)

    formatter = logging.Formatter(
        "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run.log", encoding="utf-8"),
        CustomHandler()
    ]

    for handler in handlers:
        handler.setFormatter(formatter)
        log.addHandler(handler)

def _get_logger():
    log = logging.getLogger("my_app_logger")
    if not log.handlers:  # 避免重复初始化
        _reset_logger(log)
        log.setLevel(logging.INFO)
    return log

def add_log_listener(listener: LogListener):
    state = LogState()
    state.listeners.append(listener)
    # 回放历史日志
    for log in state.temp_logs:
        listener(log)

# 全局日志实例
logger = _get_logger()