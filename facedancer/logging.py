import functools
import logging
import sys


LOGLEVEL_TRACE = 5

LOG_FORMAT_COLOR = "\u001b[37;1m%(levelname)-8s| \u001b[0m\u001b[1m%(module)-15s|\u001b[0m %(message)s"
LOG_FORMAT_PLAIN = "%(levelname)-8s| %(module)-15s| %(message)s"


def configure_default_logging(level=logging.INFO, logger=logging):
    if sys.stdout.isatty():
        log_format = LOG_FORMAT_COLOR
    else:
        log_format = LOG_FORMAT_PLAIN

    logger.basicConfig(level=level, format=log_format)
    logging.getLogger("facedancer").level = level


def _initialize_logging():
    # add a TRACE level to logging
    logging.TRACE = LOGLEVEL_TRACE
    logging.addLevelName(logging.TRACE, "TRACE")
    logging.Logger.trace = functools.partialmethod(logging.Logger.log, logging.TRACE)
    logging.trace = functools.partial(logging.log, logging.TRACE)

    # Configure facedancer logger
    logger = logging.getLogger("facedancer")
    logger.level = logging.WARN

    return logger


log = _initialize_logging()
