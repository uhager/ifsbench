from abc import ABC, abstractmethod
from pathlib import Path

from .environment import Workstation
from .ifs import IFSExecutable
from .namelist import IFSNamelist
from .util import copy_data, symlink_data


__all__ = ['Benchmark', 'FCBenchmark']


class Benchmark(ABC):
    """
    Definition of a general benchmark setup.
    """

    def __init__(self, **kwargs):
        self.expid = kwargs.get('expid')
        self.rundir = kwargs.get('rundir', None)

    @property
    @classmethod
    @abstractmethod
    def input_files(self):
        """
        List of relative paths (strings or ``Path`` objects) that
        define all necessary input data files to run this benchmark.
        """
        pass

    @classmethod
    def from_files(cls, **kwargs):
        """
        Create instance of ``Benchmark`` object by globbing a set of
        input paths for the ncessary input data and copying it into rundir.

        :param paths: One or more paths in which the necessary input data can be found
        :param rundir: Run directory to copy/symlink input data into
        :param copy: Copy files intp `rundir` instead of symlinking them
        :param force: Force delete existing input files and re-link/copy
        """
        srcdir = kwargs.get('srcdir')
        rundir = kwargs.get('rundir')
        copy = kwargs.pop('copy', False)
        force = kwargs.pop('force', False)

        # Copy / symlink input files into rundir
        for path in cls.input_files:
            path = Path(path)
            dest = Path(rundir) / path
            srcdir = Path(srcdir)
            candidates = list(srcdir.glob(path.name))
            if len(candidates) == 0:
                warning('Input file %s not found in %s' % (path.name, srcdir))
                continue
            elif len(candidates) == 1:
                source = candidates[0]
            else:
                warning('More than one input file %s found in %s' % (path.name, srcdir))
                source = candidates[0]

            if copy:
                copy_data(source, dest)
            else:
                symlink_data(source, dest)

        return cls(**kwargs)

    @classmethod
    def from_experiment(cls):
        """
        Create instance of ``Benchmark`` object from an experiment.

        Note, this requires the experiment to be suspended just before
        the template run is about to be executed, so that we can
        inspect the experiment run directory.
        """
        pass

    @classmethod
    def from_tarball(cls):
        """
        Create instance of ``Benchmark`` object from given tarball
        """
        pass

    def to_tarball(self, filepath):
        """
        Dump input files and configuration to a tarball for off-line
        benchmarking.
        """
        pass

    def check_input(self):
        """
        Check input file list matches benchmarjmk configuration.
        """
        for path in self.input_files:
            filepath = self.rundir / path
            if not filepath.exists():
                raise RuntimeError('Required input file %s not found!' % filepath)


class FCBenchmark(Benchmark):
    """
    Definition of a high-res forcecast benchmark.
    """

    pass


class T21FC(FCBenchmark):
    """
    Example configuration of a T21 forceast benchmark.
    """


if __name__ == "__main__":

    # Example of how to create and run one of the above...
    ifs = IFSExecutable(build_dir='...', install_dir='...')

    # benchmark = T21FC.from_tarball('path_to_tarball', run_dir='./')

    namelist = IFSNamelist('path_to_default_namelist')
    benchmark = T21FC.from_files('path_to_glob_for_input', namelist=namelist)

    benchmark.check_input()  # <= check that all required input data is found
    benchmark.run(ifs=ifs, env=Workstation())
