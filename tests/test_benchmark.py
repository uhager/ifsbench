import shutil
from pathlib import Path

import pytest
from conftest import Watcher
from ifsbench import (
    logger, Benchmark, IFS, InputFile, ExperimentFiles,
    DarshanReport, read_files_from_darshan, write_files_from_darshan, gettempdir
)

@pytest.fixture(name='watcher')
def fixture_watcher():
    return Watcher(logger=logger, silent=True)


@pytest.fixture(name='here')
def fixture_here():
    return Path(__file__).parent.resolve()


@pytest.fixture(name='rundir')
def fixture_rundir(here):
    """
    Remove any created ``source`` directories
    """
    rundir = here/'rundir'
    rundir.mkdir(parents=True, exist_ok=True)
    yield rundir

    # Clean up after us
    if rundir.exists():
        shutil.rmtree(rundir)


class SimpleBenchmark(Benchmark):
    """
    Example configuration of simple benchmark.
    """

    input_files = [
        'inputA',
        './someplace/inputB',
        Path('./inputC'),
    ]


def test_benchmark_input_file(here):
    """
    Test representation of a single input file
    """
    # Test basic representation
    path = Path(__file__)
    input_file = InputFile(path, src_dir=here)
    assert str(input_file.path) == path.name
    assert input_file.fullpath == path
    assert input_file.src_dir == here

    # Test dumping and loading
    other_file = InputFile.from_dict(input_file.to_dict(), src_dir=here)
    assert str(other_file.path) == path.name
    assert other_file.fullpath == path
    assert other_file.src_dir == here

    # Test dumping and loading without src_dir
    extra_file = InputFile.from_dict(input_file.to_dict())
    assert extra_file.path == path.relative_to('/')
    assert extra_file.fullpath == path
    assert extra_file.src_dir == Path('/')

    # Test checksum verification
    extra_file.checksum = 'foobar'
    with pytest.raises(ValueError):
        InputFile.from_dict(extra_file.to_dict())

    # Test dumping and loading without checksum verification
    other_file._path = Path('foo.bar')  # pylint: disable=protected-access
    extra_file = InputFile.from_dict(other_file.to_dict(), verify_checksum=False)
    assert extra_file.path == (here/'foo.bar').relative_to('/')
    assert extra_file.fullpath == here/'foo.bar'
    assert extra_file.src_dir == Path('/')


def test_benchmark_experiment_files(here):
    """
    Test discovery of files in src_dir
    """
    # TODO
    pass


def test_benchmark_experiment_files_from_darshan(here):
    """
    Test representation of darshan report in `ExperimentFiles`
    """
    report = DarshanReport(here/'darshan.log')
    read_files = read_files_from_darshan(report)
    write_files = write_files_from_darshan(report)
    input_files = read_files - write_files

    # Test basic representation
    exp_files = ExperimentFiles('abcd')
    exp_files.add_file(*input_files, compute_metadata=False)
    assert len(exp_files.files) == 27
    assert len(exp_files.exp_files) == 15
    assert len(exp_files.ifsdata_files) == 12

    # Test dumping and loading
    other_files = ExperimentFiles.from_dict(exp_files.to_dict(), verify_checksum=False)
    assert {str(f.fullpath) for f in exp_files.files} == {str(f.fullpath) for f in other_files.files}

    yaml_file = gettempdir()/'experiment_files.yml'
    exp_files.to_yaml(yaml_file)
    other_files = ExperimentFiles.from_yaml(yaml_file, verify_checksum=False)


@pytest.mark.parametrize('copy', [True, False])
def test_benchmark_from_files(here, rundir, copy):
    """
    Test input file verification for a simple benchmark setup.
    """
    benchmark = SimpleBenchmark.from_files(rundir=rundir, srcdir=here/'inidata', copy=copy)

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
    benchmark = SimpleBenchmark.from_files(ifs=ifs, srcdir=here/'inidata', rundir=rundir)

    benchmark.check_input()
    with watcher:
        benchmark.run(dryrun=True, namelist=here/'t21_fc.nml')

    ifscmd = str(rundir.parent/'bin/ifsMASTER.DP')
    assert ifscmd in watcher.output

    # Ensure fort.4 config file was generated
    config = here.parent/'fort.4'
    assert config.exists()

    # Clean up config file
    config.unlink()
