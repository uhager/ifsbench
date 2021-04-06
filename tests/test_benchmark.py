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


@pytest.fixture(name='tarballdir')
def fixture_tarballdir(here):
    """
    Create a temporary tarball directory
    """
    tarballdir = here/'tarballdir'
    tarballdir.mkdir(parents=True, exist_ok=True)
    yield tarballdir

    # Clean up after us
    if tarballdir.exists():
        shutil.rmtree(tarballdir)


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

    # Test equality of input files even with different paths
    the_file = InputFile(path, src_dir=here)
    also_the_file = InputFile(here/'..'/path.parent.name/path.name, src_dir=here.parent)
    assert the_file.fullpath != also_the_file.fullpath
    assert the_file.fullpath.resolve() == also_the_file.fullpath.resolve()
    assert the_file.checksum == also_the_file.checksum
    assert the_file == also_the_file


def test_benchmark_experiment_files(here, tarballdir):
    """
    Test discovery of files in src_dir
    """
    exp_setup = {
        'my-exp-id': {
            '/some/path/to/some/source/dir': {
                'sub/directory/inputA': {
                    'fullpath': '/some/path/to/some/source/dir/sub/directory/inputA',
                    'sha256sum': 'b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c'
                },
                'sub/directory/inputC': {
                    'fullpath': '/some/path/to/some/source/dir/sub/directory/inputC',
                    'sha256sum': 'bf07a7fbb825fc0aae7bf4a1177b2b31fcf8a3feeaf7092761e18c859ee52a9c'
                },
            },
            '/some/other/path/to/some/input/dir': {
                'subsub/dir/inputB': {
                    'fullpath': '/some/other/path/to/some/input/dir/subsub/dir/inputB',
                    'sha256sum': '7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730'
                },
            },
            '/the/path/to/ifsdata': {
                'some/inputD': {
                    'fullpath': '/the/path/to/ifsdata/some/inputD',
                    'sha256sum': 'aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019'
                    # Note: missing last letter 'f' in checksum (see test below)!
                },
            },
        },
    }

    # Create ExperimentFiles object from the dict
    exp_files = ExperimentFiles.from_dict(exp_setup.copy(), verify_checksum=False)
    assert exp_files.exp_id == 'my-exp-id'
    assert len(exp_files.files) == 4
    assert len(exp_files.exp_files) == 3
    assert len(exp_files.ifsdata_files) == 1

    # Update the srcdir which automatically verifies the checksum
    with pytest.raises(ValueError):
        exp_files.update_srcdir(here, with_ifsdata=True)

    # Do the same with correct checksum
    exp_setup['my-exp-id']['/the/path/to/ifsdata']['some/inputD']['sha256sum'] += 'f'
    exp_files = ExperimentFiles.from_dict(exp_setup, verify_checksum=False)

    # Update the srcdir for exp_files but not ifsdata
    exp_files.update_srcdir(here)
    assert all(str(f.fullpath.parent) == str(here/'inidata') for f in exp_files.exp_files)
    assert all(str(f.fullpath.parent).startswith('/the/path/to') for f in exp_files.ifsdata_files)

    # Update srcdir for all
    exp_files.update_srcdir(here, with_ifsdata=True)
    assert all(str(f.fullpath.parent) == str(here/'inidata') for f in exp_files.exp_files)
    assert all(str(f.fullpath.parent) == str(here/'ifsdata') for f in exp_files.ifsdata_files)

    # Reload experiment from dict with checksum verification
    reloaded_exp_files = ExperimentFiles.from_dict(exp_files.to_dict(), verify_checksum=True)
    assert len(reloaded_exp_files.files) == 4
    assert len(reloaded_exp_files.exp_files) == 3
    assert len(reloaded_exp_files.ifsdata_files) == 1

    # Pack experiment files to tarballs
    exp_files.to_tarball(tarballdir, with_ifsdata=True)
    assert Path(tarballdir/here.name).with_suffix('.tar.gz').exists()
    assert Path(tarballdir/'ifsdata.tar.gz').exists()
    yaml_file = tarballdir/(exp_files.exp_id+'.yml')
    exp_files.to_yaml(yaml_file)

    # Unpack experiments
    reloaded_exp_files = ExperimentFiles.from_tarball(
        yaml_file, input_dir=tarballdir, output_dir=tarballdir, with_ifsdata=True)
    assert len(reloaded_exp_files.files) == 4
    assert len(reloaded_exp_files.exp_files) == 3
    assert len(reloaded_exp_files.ifsdata_files) == 1
    assert all(str(f.fullpath.parent).startswith(str(tarballdir)) for f in reloaded_exp_files.files)


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
