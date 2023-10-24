import logging


def set_logging(level="info"):
    levels = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "warn": logging.WARNING,
        "error": logging.ERROR,
    }

    logging.basicConfig(
        level=levels.get(level, logging.INFO),
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
    )
