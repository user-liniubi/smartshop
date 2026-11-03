import logging
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str):
    return request_id_context.set(request_id)


def reset_request_id(token) -> None:
    request_id_context.reset(token)


def get_request_id() -> str:
    return request_id_context.get()


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
