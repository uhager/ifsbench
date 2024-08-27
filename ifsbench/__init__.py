"""
ifsbench: IFS benchmark and testing utilities in Python

This package contains Python utilities to run and benchmark the IFS.
"""

from pkg_resources import get_distribution, DistributionNotFound

from .arch import * # noqa
from .benchmark import * # noqa
from .cli import * # noqa
from .darshanreport import * # noqa
from .drhook import * # noqa
from .files import * # noqa
from .gribfile import * # noqa
from .ifs import * # noqa
from .job import * # noqa
from .launcher import * # noqa
from .logging import * # noqa
from .namelist import * # noqa
from .nodefile import * # noqa
from .paths import * # noqa
from .runrecord import * # noqa
from .util import * # noqa

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass
