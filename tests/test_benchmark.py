import pytest
import shutil
from conftest import Watcher
from pathlib import Path

from ifsbench import logger, FCBenchmark, IFS, IFSNamelist, Workstation


@pytest.fixture
def watcher():
    return Watcher(logger=logger, silent=True)


@pytest.fixture
def here():
    return Path(__file__).parent.resolve()


@pytest.fixture
def rundir(here):
    """
    Remove any created ``source`` directories
    """
    rundir = here/'rundir'
    rundir.mkdir(parents=True, exist_ok=True)
    yield rundir

    # Clean up after us
    if rundir.exists():
        shutil.rmtree(rundir)


class T21FC(FCBenchmark):
    """
    Example configuration of a T21 forceast benchmark.
    """

    input_files = [
        'inputA',
        './someplace/inputB',
        Path('./inputC'),
    ]


@pytest.mark.parametrize('copy', [True, False])
def test_benchmark_from_files(here, rundir, copy):
    """
    Test input file verification for a simple benchmark setup.
    """
    benchmark = T21FC.from_files(rundir=rundir, srcdir=here/'inidata', copy=copy)

    # Let benchmark test itself
    benchmark.check_input()

    # And then we just make sure
    assert (rundir/'inputA').exists()
    assert (rundir/'someplace/inputB').exists()
    assert (rundir/'inputC').exists()


@pytest.mark.skip(reason='Tarball packing not yet implemented')
def test_benchmark_from_tarball():
    """
    Test input file verification for a simple benchmark setup.
    """
    raise NotImplementedError('Tarball packaging not yet tested')


def test_benchmark_execute(here, rundir, watcher):
    """
    Test the basic benchmark execution mechanism.
    """
    # Example of how to create and run one of the above...
    ifs = IFS(builddir=here)
    namelist = IFSNamelist(here/'default.nml')
    benchmark = T21FC.from_files(ifs=ifs, namelist=namelist,
                                 srcdir=here/'inidata', rundir=rundir)

    benchmark.check_input()
    with watcher:
        benchmark.run(dryrun=True, arch=Workstation)

    assert 'Executing: ifsMASTER.DP' in watcher.output
