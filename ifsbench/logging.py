import logging
try:
    import coloredlogs
except ImportError:
    coloredlogs = None


__all__ = ['logger', 'debug', 'info', 'success', 'warning', 'error', 'log',
           'set_log_level', 'DEBUG', 'INFO', 'WARNING', 'ERROR']

# Initialize central logging
logging.basicConfig()

# set success level
logging.SUCCESS = 35
logging.addLevelName(logging.SUCCESS, 'SUCCESS')

# Wrap the usual log level flags
DEBUG = logging.DEBUG
INFO = logging.INFO
SUCCESS = logging.SUCCESS
WARNING = logging.WARNING
ERROR = logging.ERROR

# Create the default logger with color and timings
default_level = INFO
logger = logging.getLogger('ifsbench')

if coloredlogs:
    coloredlogs.install(level=default_level, logger=logger)
else:
    logger.setLevel(default_level)


# Wrap the common invocation methods
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
log = logger.log
setattr(logger, 'success', lambda message, *args: logger._log(logging.SUCCESS, message, args))
success = logger.success


def set_log_level(level):
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
