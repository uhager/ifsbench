from __future__ import absolute_import

import logging
import sys


__all__ = ['debug', 'info', 'warning', 'error', 'logger', 'colors',
           'DEBUG', 'INFO', 'WARNING', 'ERROR']


class colors:

    @staticmethod
    def enable():
        colors.HEADER = '\033[95m%s\033[0m'
        colors.OKBLUE = '\033[94m%s\033[0m'
        colors.OKGREEN = '\033[92m%s\033[0m'
        colors.WARNING = '\033[93m%s\033[0m'
        colors.FAIL = '\033[91m%s\033[0m'
        colors.BOLD = '\033[1m%s\033[0m'
        colors.UNDERLINE = '\033[4m%s\033[0m'

    @staticmethod
    def disable():
        colors.HEADER = '%s'
        colors.OKBLUE = '%s'
        colors.OKGREEN = '%s'
        colors.WARNING = '%s'
        colors.FAIL = '%s'
        colors.BOLD = '%s'
        colors.UNDERLINE = '%s'


# Set colours on true terminals
if sys.stdout.isatty:
    colors.enable()
else:
    colors.disable()


logger = logging.getLogger('ecbundle')
_ch = logging.StreamHandler()
logger.addHandler(_ch)
logger.setLevel(logging.INFO)

INFO = logging.INFO
DEBUG = logging.DEBUG
WARNING = logging.WARNING
ERROR = logging.ERROR

def debug(msg, *args, **kwargs):
    msg = colors.OKBLUE % msg
    logger.log(logging.DEBUG, msg, *args, **kwargs)


def header(msg, *args, **kwargs):
    msg = colors.HEADER % msg
    logger.log(logging.INFO, msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    msg = colors.OKBLUE % msg
    logger.log(logging.INFO, msg, *args, **kwargs)


def success(msg, *args, **kwargs):
    msg = colors.OKGREEN % msg
    logger.log(logging.INFO, msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    msg = colors.WARNING % msg
    logger.log(logging.WARNING, msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    msg = colors.FAIL % msg
    logger.log(logging.ERROR, msg, *args, **kwargs)
