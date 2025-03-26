# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import Enum
from types import MappingProxyType

from ifsbench.launch.mpirunlauncher import MpirunLauncher
from ifsbench.launch.srunlauncher import SrunLauncher

__all__ = ['Launchers', 'LauncherLookup']


class Launchers(str, Enum):
    MPIRUN = MpirunLauncher.__name__
    SRUN = SrunLauncher.__name__


LauncherLookup = MappingProxyType(
    {Launchers.MPIRUN: MpirunLauncher, Launchers.SRUN: SrunLauncher}
)
