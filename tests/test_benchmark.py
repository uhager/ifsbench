import pytest
import shutil

from ifsbench import FCBenchmark
from pathlib import Path


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
