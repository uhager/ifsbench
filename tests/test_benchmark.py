# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for all classes that define a benchmark and its input files
"""

from contextlib import contextmanager
from pathlib import Path
import shutil

import pytest
from conftest import Watcher
from ifsbench import (
    logger, Benchmark, IFS,
    ExperimentFiles, ExperimentFilesBenchmark, SpecialRelativePath,
)

@pytest.fixture(name='watcher')
def fixture_watcher():
    """Return a :any:`Watcher` to check test output"""
    return Watcher(logger=logger, silent=True)


@pytest.fixture(name='here')
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve()


@contextmanager
def temporary_tarballdir(basedir):
    """
    Create a temporary tarball directory
    """
    tarballdir = basedir/'tarballdir'
    if tarballdir.exists():
        shutil.rmtree(tarballdir)
    tarballdir.mkdir(parents=True, exist_ok=True)
    yield tarballdir

    # Clean up after us
    if tarballdir.exists():
        shutil.rmtree(tarballdir)


@contextmanager
def temporary_rundir(basedir):
    """
    Create a temporary `rundir` and clean it up afterwards
    """
    rundir = basedir/'rundir'
    if rundir.exists():
        shutil.rmtree(rundir)
    rundir.mkdir(parents=True, exist_ok=True)
    yield rundir

    # Clean up after us
    if rundir.exists():
        shutil.rmtree(rundir)


experiment_files_dict = {
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
                'sha256sum': 'aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f'
            },
        },
    },
}


class SimpleBenchmark(Benchmark):
    """
    Example configuration of simple :any:`Benchmark`
    """

    input_files = [
        'inputA',
        './someplace/inputB',
        Path('./inputC'),
    ]


class SimpleExperimentFilesBenchmark(ExperimentFilesBenchmark):
    """
    Example configuration of simple :any:`ExperimentFilesBenchmark`
    """

    special_paths = [
        SpecialRelativePath.from_filename('inputB', './someplace/inputB'),
    ]


@pytest.mark.parametrize('copy', [True, False])
def test_benchmark_from_files(here, copy):
    """
    Test input file verification for a simple benchmark setup.
    """
    with temporary_rundir(here) as rundir:
        benchmark = SimpleBenchmark.from_files(rundir=rundir, srcdir=here/'inidata', copy=copy)

        # Let benchmark test itself
        benchmark.check_input()

        # And then we just make sure
        assert (rundir/'inputA').exists()
        assert (rundir/'someplace/inputB').exists()
        assert (rundir/'inputC').exists()


def test_benchmark_execute(here, watcher):
    """
    Test the basic benchmark execution mechanism.
    """
    # Example of how to create and run one of the above...
    ifs = IFS.create_cycle('default', builddir=here)
    with temporary_rundir(here) as rundir:
        benchmark = SimpleBenchmark.from_files(ifs=ifs, srcdir=here/'inidata', rundir=rundir)

        benchmark.check_input()
        with watcher:
            benchmark.run(dryrun=True, namelist=here/'t21_fc.nml')

        ifscmd = str(rundir.parent/'bin/ifsMASTER.DP')
        assert ifscmd in watcher.output

        # Ensure fort.4 config file was generated
        config = rundir/'fort.4'
        assert config.exists()

        # Clean up config file
        config.unlink()


@pytest.mark.parametrize('copy', [True, False])
def test_benchmark_from_experiment_files(here, copy):
    """
    Test input file verification for a simple benchmark setup
    """
    exp_files = ExperimentFiles.from_dict(experiment_files_dict.copy(), verify_checksum=False)
    exp_files.update_srcdir(here, with_ifsdata=True)

    with temporary_rundir(here) as rundir:
        benchmark = SimpleExperimentFilesBenchmark.from_experiment_files(
            rundir=rundir, exp_files=exp_files, copy=copy)

        # Let benchmark test itself
        benchmark.check_input()

        # And then we just make sure
        assert (rundir/'inputA').exists()
        assert (rundir/'someplace/inputB').exists()
        assert (rundir/'inputC').exists()
        assert (rundir/'inputD').exists()


def test_benchmark_from_experiment_files_execute(here, watcher):
    """
    Test the basic benchmark execution mechanism.
    """
    exp_files = ExperimentFiles.from_dict(experiment_files_dict.copy(), verify_checksum=False)
    exp_files.update_srcdir(here, with_ifsdata=True)
    ifs = IFS.create_cycle('default', builddir=here)

    with temporary_rundir(here) as rundir:
        benchmark = SimpleExperimentFilesBenchmark.from_experiment_files(
            rundir=rundir, exp_files=exp_files, ifs=ifs)

        benchmark.check_input()
        with watcher:
            benchmark.run(dryrun=True, namelist=here/'t21_fc.nml')

        ifscmd = str(rundir.parent/'bin/ifsMASTER.DP')
        assert ifscmd in watcher.output

        # Ensure fort.4 config file was generated
        config = rundir/'fort.4'
        assert config.exists()

        # Clean up config file
        config.unlink()


def test_benchmark_from_tarball(here, watcher):
    """
    Test running a benchmark from a tarball
    """
    with temporary_tarballdir(here) as tarballdir:
        # Pack experiment files to tarballs
        exp_files = ExperimentFiles.from_dict(experiment_files_dict.copy(), verify_checksum=False)
        exp_files.update_srcdir(here, with_ifsdata=True)
        exp_files.to_tarball(tarballdir, with_ifsdata=True)
        yaml_file = tarballdir/(exp_files.exp_id+'.yml')
        exp_files.to_yaml(yaml_file)

        # Unpack experiments
        reloaded_exp_files = ExperimentFiles.from_tarball(
            yaml_file, input_dir=tarballdir, output_dir=tarballdir, with_ifsdata=True)

        with temporary_rundir(here) as rundir:
            ifs = IFS.create_cycle('default', builddir=here)
            benchmark = SimpleExperimentFilesBenchmark.from_experiment_files(
                rundir=rundir, exp_files=reloaded_exp_files, ifs=ifs)

            benchmark.check_input()
            with watcher:
                benchmark.run(dryrun=True, namelist=here/'t21_fc.nml')

            ifscmd = str(rundir.parent/'bin/ifsMASTER.DP')
            assert ifscmd in watcher.output

            # Ensure fort.4 config file was generated
            config = rundir/'fort.4'
            assert config.exists()

            # Clean up config file
            config.unlink()
