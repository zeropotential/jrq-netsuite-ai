import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(handler)
