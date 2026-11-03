import logging

from backend.app.core.request_context import RequestIdLogFilter


def configure_logging(log_level: str) -> None:
    """Configure application logging with a consistent console format."""

    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format=("%(asctime)s | %(levelname)s | %(name)s | request_id=%(request_id)s | %(message)s"),
        force=True,
    )
    request_filter = RequestIdLogFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(request_filter)
