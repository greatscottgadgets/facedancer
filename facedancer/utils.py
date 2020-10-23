import logging
import sys


# Set up our logger
LOGLEVEL_TRACE = logging.DEBUG + 2
logging.addLevelName(LOGLEVEL_TRACE, 'TRACE')
logger = logging.getLogger(__name__)

# Log formatting strings.
LOG_FORMAT_COLOR = "\u001b[37;1m%(levelname)-8s| \u001b[0m\u001b[1m%(module)-15s|\u001b[0m %(message)s"
LOG_FORMAT_PLAIN = "%(levelname)-8s| %(module)-15s| %(message)s"

if sys.stdout.isatty():
    log_format = LOG_FORMAT_COLOR
else:
    log_format = LOG_FORMAT_PLAIN

__hdl = logging.StreamHandler()
__fmt = logging.Formatter(log_format)
__hdl.formatter = __fmt
logger.addHandler(__hdl)
