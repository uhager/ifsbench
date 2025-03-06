# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pytest

from ifsbench.launch.launcher_utils import LauncherLookup, Launchers
from ifsbench.launch.mpirunlauncher import MpirunLauncher
from ifsbench.launch.srunlauncher import SrunLauncher


@pytest.mark.parametrize(
    'launchername, launchertype',
    [
        ('MpirunLauncher', MpirunLauncher),
        ('SrunLauncher', SrunLauncher),
    ],
)
def test_launcher_utils_from_name(launchername, launchertype):

    lookup_type = LauncherLookup[launchername]

    assert lookup_type == launchertype


@pytest.mark.parametrize(
    'launchername, launchertype',
    [
        (Launchers.MPIRUN, MpirunLauncher),
        (Launchers.SRUN, SrunLauncher),
    ],
)
def test_launcher_utils_from_enum(launchername, launchertype):

    lookup_type = LauncherLookup[launchername]

    assert lookup_type == launchertype
