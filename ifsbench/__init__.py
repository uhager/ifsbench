"""
ifsbench: IFS benchmark and testing utilities in Python

This package contains Python utilities to run and benchmark the IFS.
"""

from __future__ import (absolute_import, division, print_function)  # noqa

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


from .arch import * # noqa
from .benchmark import * # noqa
from .darshanreport import * # noqa
from .drhook import * # noqa
from .files import * # noqa
from .ifs import * # noqa
from .job import * # noqa
from .logging import * # noqa
from .namelist import * # noqa
from .nodefile import * # noqa
from .paths import * # noqa
from .runrecord import * # noqa
from .util import * # noqa
