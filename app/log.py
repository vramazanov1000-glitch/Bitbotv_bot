import logging
from .config import LOG_LEVEL


def setup_logging() -> None:
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )