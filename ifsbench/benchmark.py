"""
Classes to set-up a benchmark
"""
from abc import ABC, abstractmethod
from pathlib import Path
from subprocess import CalledProcessError
import sys

from .drhook import DrHook
from .logging import warning, error
from .util import copy_data, symlink_data, as_tuple, flatten
from .runrecord import RunRecord


__all__ = ['Benchmark', 'ExperimentFilesBenchmark']


class Benchmark(ABC):
    """
    Definition of a general benchmark setup

    Parameters
    ----------
    expid : str
        The experiment id corresponding to the input data set.
    ifs : :any:`IFS`
        The IFS configuration object.
    rundir : str or :any:`pathlib.Path`, optional
        The default working directory to be used for :meth:`run`.
    """

    def __init__(self, **kwargs):
        self.expid = kwargs.get('expid')
        self.rundir = kwargs.get('rundir', None)

        self.ifs = kwargs.get('ifs')

    @property
    @classmethod
    @abstractmethod
    def input_files(cls):
        """
        List of relative paths that define all necessary input data files to
        run this benchmark

        Returns
        -------
        list of str or :any:`pathlib.Path`
            Relative paths for all input files required to run this benchmark.
            The relative paths will be reproduced in :attr:`Benchmark.rundir`.
        """

    @classmethod
    def from_files(cls, **kwargs):
        """
        Create instance of :class:`Benchmark` by globbing a set of input paths
        for the necessary input data and copying or linking it into rundir

        Parameters
        ----------
        rundir : str or :any:`pathlib.Path`
            Run directory to copy/symlink input data into
        srcdir : (list of) str or :any:`pathlib.Path`
            One or more source directories to search for input data
        ifsdata : str or :any:`pathlib.Path`, optional
            `ifsdata` directory to link as a whole
            (default: :attr:`Benchmark.input_data`)
        input_files : list of str, optional
            Relative paths of necessary input files
        copy : bool, optional
            Copy files into :data:`rundir` instead of symlinking them (default: False)
        force : bool, optional
            Overwrite existing input files and re-link/copy (default: False)
        """
        srcdir = as_tuple(kwargs.get('srcdir'))
        rundir = Path(kwargs.get('rundir'))
        copy = kwargs.pop('copy', False)
        force = kwargs.pop('force', False)
        ifsdata = kwargs.get('ifsdata', None)
        input_files = kwargs.get('input_files', cls.input_files)

        if ifsdata is not None:
            symlink_data(Path(ifsdata), rundir/'ifsdata', force=force)

        # Copy / symlink input files into rundir
        for path in input_files:
            path = Path(path)
            dest = Path(rundir) / path
            candidates = flatten([list(Path(s).glob(f'**/{path.name}')) for s in srcdir])
            if len(candidates) == 0:
                warning(f'Input file {path.name} not found in {srcdir}')
                continue
            if len(candidates) == 1:
                source = candidates[0]
            else:
                warning(f'More than one input file {path.name} found in {srcdir}')
                source = candidates[0]

            if copy:
                copy_data(source, dest, force=force)
            else:
                symlink_data(source, dest, force=force)

        return cls(**kwargs)

    @classmethod
    def from_tarball(cls):
        """
        Create instance of ``Benchmark`` object from given tarball
        """
        raise NotImplementedError

    def to_tarball(self, filepath):
        """
        Dump input files and configuration to a tarball for off-line
        benchmarking.
        """
        raise NotImplementedError

    def check_input(self):
        """
        Check input file list matches benchmark configuration.
        """
        for path in self.input_files:
            filepath = self.rundir / path
            if not filepath.exists():
                raise RuntimeError(f'Required input file "{filepath}" not found!')

    def run(self, **kwargs):
        """
        Run the specified benchmark and validate against stored results.
        """
        if 'rundir' in kwargs:
            if kwargs['rundir'] != self.rundir:
                error(f'Stored run directory: {self.rundir}')
                error(f'Given run directory:  {kwargs["rundir"]}')
                raise RuntimeError('Conflicting run directories provided!')
        else:
            kwargs['rundir'] = self.rundir

        try:
            self.ifs.run(**kwargs)

        except CalledProcessError:
            error(f'Benchmark run failed: {" ".join(kwargs)}')
            sys.exit(-1)

        # Provide DrHook output path only if DrHook is active
        drhook = kwargs.get('drhook', DrHook.OFF)
        drhook_path = None if drhook == DrHook.OFF else self.rundir/'drhook.*'

        dryrun = kwargs.get('dryrun', False)
        if not dryrun:
            return RunRecord.from_run(nodefile=self.rundir/'NODE.001_01', drhook=drhook_path)
        return None


class ExperimentFilesBenchmark(Benchmark):
    """
    General :class:`Benchmark` setup created from input file description
    provided by :any:`ExperimentFiles`

    """

    def __init__(self, **kwargs):
        self._input_files = kwargs.pop('input_files')
        super().__init__(**kwargs)

    @property
    @classmethod
    def special_paths(cls):
        """
        List of :any:`SpecialRelativePath` patterns that define transformations
        for converting a file path to a particular relative path object.

        Returns
        -------
        list of :any:`SpecialRelativePath`
        """

    @property
    def input_files(self):
        return self._input_files

    @classmethod
    def from_experiment_files(cls, **kwargs):
        """
        Instantiate :class:`Benchmark` using input file lists captured in an
        :any:`ExperimentFiles` object
        """
        rundir = Path(kwargs.get('rundir'))
        exp_files = kwargs.pop('exp_files')
        copy = kwargs.pop('copy', False)
        force = kwargs.pop('force', False)
        ifsdata = kwargs.get('ifsdata', None)

        if ifsdata is not None:
            symlink_data(Path(ifsdata), rundir/'ifsdata', force=force)

        special_paths = cls.special_paths if isinstance(cls.special_paths, (list, tuple)) else ()
        input_files = []
        for f in exp_files.files:
            dest, source = str(f.fullpath), str(f.fullpath)
            for pattern in special_paths:
                dest = pattern(dest)
                if dest != source:
                    break
            else:
                dest = str(Path(dest).name)

            input_files += [dest]
            source, dest = Path(source), rundir/dest
            if copy:
                copy_data(source, dest, force=force)
            else:
                symlink_data(source, dest, force=force)

        obj = cls(input_files=input_files, **kwargs)
        return obj
