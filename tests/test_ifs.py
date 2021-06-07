"""
Test :any:`IFS` and adjacent classes
"""
from pathlib import Path
import pytest
import ifsbench.ifs as ifs


@pytest.fixture(name='here')
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve()


@pytest.mark.parametrize('cycle,expected_type', [
    ('CY46R1', ifs.IFS_CY46R1),
    ('cy46r1', ifs.IFS_CY46R1),
    ('CY47R1', ifs.IFS_CY47R1),
    ('cy47r1', ifs.IFS_CY47R1),
    ('CY47R2', ifs.IFS_CY47R2),
    ('cy47r2', ifs.IFS_CY47R2),
    (None, ifs.IFS_CY47R2),
    ('default', ifs.IFS_CY47R2),
])
def test_ifs_construction(cycle, expected_type):
    """
    Test correct setup of IFS cycles
    """
    obj = ifs.IFS.create_cycle(cycle, builddir='.')
    assert isinstance(obj, expected_type)


@pytest.mark.parametrize('cycle', list(ifs.cycle_registry.keys()))
def test_ifs(cycle):
    """
    Verify that some of the default properties return sensible values
    """
    obj_default = ifs.IFS.create_cycle(cycle, builddir='build')
    assert obj_default.exec_name == 'ifsMASTER.DP'
    assert str(obj_default.executable) == 'build/bin/ifsMASTER.DP'

    obj_install = ifs.IFS.create_cycle(cycle, builddir='build', installdir='../prefix')
    assert obj_default.exec_name == 'ifsMASTER.DP'
    assert str(obj_install.executable) == '../prefix/bin/ifsMASTER.DP'


@pytest.mark.parametrize('cycle', list(ifs.cycle_registry.keys()))
def test_ifs_setup_env(cycle):
    """
    Verify that a given number of default parameters is present in the env
    """
    default_keys = {'DATA', 'GRIB_DEFINITION_PATH', 'GRIB_SAMPLES_PATH', 'NPROC', 'NPROC_IO'}

    obj = ifs.IFS.create_cycle(cycle, builddir='build')
    env, kwargs = obj.setup_env(rundir='.', nproc=1337, nproc_io=42, namelist=None, nthread=1,
                                hyperthread=1, arch=None)
    assert kwargs == {}
    assert default_keys <= set(env.keys())

    env, kwargs = obj.setup_env(rundir='../..', env={'abc': 123, 'foo': 666}, nproc=1, nproc_io=0,
                                namelist=None, nthread=1, hyperthread=1, arch=None, foobar='baz')
    assert kwargs == {'foobar': 'baz'}
    assert (default_keys | {'abc', 'foo'}) <= set(env.keys())


@pytest.mark.parametrize('cycle', list(ifs.cycle_registry.keys()))
def test_ifs_setup_nml(here, cycle):
    """
    Verify that a given number of default parameters is set correctly
    in the namelist
    """
    default_params = (
        (('nampar0', 'nproc'), 7),
        (('namio_serv', 'nproc_io'), 5),
    )

    obj = ifs.IFS.create_cycle(cycle, builddir='build')
    nml, kwargs = obj.setup_nml(namelist=(here/'t21_fc.nml'), rundir='.', nproc=12, nproc_io=5,
                                nthread=1, hyperthread=1, arch=None, foobar='baz')
    assert kwargs == {'foobar': 'baz'}
    groups = tuple(nml.nml.groups())
    assert all(param in groups for param in default_params)

    nml, kwargs = obj.setup_nml(namelist=(here/'t21_fc.nml'), rundir='.', nproc=12, nproc_io=5,
                                fclen='d10', nthread=1, hyperthread=1, arch=None)
    assert kwargs == {}
    groups = tuple(nml.nml.groups())
    default_params += ((('namrip', 'cstop'), 'd10'),)
    assert all(param in groups for param in default_params)
