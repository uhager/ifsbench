"""
Classes to set-up a benchmark
"""
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from subprocess import CalledProcessError
import yaml

from .drhook import DrHook
from .logging import warning, error
from .util import copy_data, symlink_data, as_tuple, flatten, gettempdir, execute
from .runrecord import RunRecord


__all__ = ['InputFile', 'ExperimentFiles', 'Benchmark']


class InputFile:
    """
    Representation of a single input file together with some meta data

    Parameters
    ----------
    path : str or :any:`pathlib.Path`
        The path of the input file
    src_dir : str or :any:`pathlib.Path`, optional
        The base directory relative to which :attr:`path` is interpreted.
    compute_metadata : bool, optional
        Compute meta data for that file (such as SHA-256 checksum and size).
    """

    def __init__(self, path, src_dir=None, compute_metadata=True):
        if src_dir is None:
            src_dir = '/'
        self._src_dir = Path(src_dir)
        self._path = Path(path).relative_to(self.src_dir)

        if compute_metadata:
            self.checksum = self._sha256sum(self.fullpath)
            self.size = self._size(self.fullpath)
        else:
            self.checksum = None
            self.size = None

    @classmethod
    def from_dict(cls, data, src_dir=None, verify_checksum=True):
        """
        Create :any:`InputFile` from a dict representation

        Parameters
        ----------
        data : dict
            The dict representation, e.g. created by :meth:`to_dict`
        src_dir : str or :any:`pathlib.Path`, optional
            The base directory relative to which the path should be stored.
        verify_checksum : bool, optional
            Verify that checksum in dict matches the file.
        """
        path, meta = data.popitem()
        assert not data
        obj = cls(meta['fullpath'], src_dir=src_dir, compute_metadata=verify_checksum)
        if verify_checksum:
            if meta['sha256sum'] != obj.checksum:
                raise ValueError('Checksum for {} does not match'.format(path))
        else:
            obj.checksum = meta.get('sha256sum')
            obj.size = meta.get('size')
        return obj

    def to_dict(self):
        """Create a `dict` representation of the meta data for this file"""
        data = {'fullpath': str(self.fullpath)}
        if self.checksum:
            data['sha256sum'] = self.checksum
        if self.size:
            data['size'] = self.size
        return {str(self.path): data}

    @property
    def fullpath(self):
        """The full path of the file"""
        return self.src_dir/self._path

    @property
    def path(self):
        """The path of the file relative to :attr:`src_dir`"""
        return self._path

    @property
    def src_dir(self):
        """The base directory under which the file is located"""
        return self._src_dir

    @staticmethod
    def _sha256sum(filepath):
        """Create SHA-256 checksum for the file at the given path"""
        filepath = Path(filepath)
        logfile = gettempdir()/'checksum.sha256'
        cmd = ['sha256sum', str(filepath)]
        execute(cmd, logfile=logfile)
        with logfile.open() as f:
            checksum, name = f.read().split()
            assert name == str(filepath)
        return checksum

    @staticmethod
    def _size(filepath):
        """Obtain file size in byte for the file at the given path"""
        filepath = Path(filepath)
        return filepath.stat().st_size


class ExperimentFiles:
    """
    Helper class to store the list of files required to run an experiment

    It provides capabilities to pack and unpack tarballs of these files
    to prepare an experiment for external runs.

    Parameters
    ----------
    exp_id : str
        The id of the experiment
    src_dir : (list of) str or :any:`pathlib.Path`, optional
        One or more source directories from which input data to take.
        If given, files are searched for in these paths.
    """

    def __init__(self, exp_id, src_dir=None):
        self.exp_id = exp_id
        self.src_dir = tuple(Path(s) for s in as_tuple(src_dir))
        self._files = set()

    @classmethod
    def from_yaml(cls, input_path, verify_checksum=True):
        """
        Load :any:`ExperimentFiles` from a YAML file

        Parameters
        ----------
        input_path : str or :any:`pathlib.Path`
            The file name of the YAML file.
        verify_checksum : bool, optional
            Verify checksum of all files.
        """
        with Path(input_path).open() as f:
            return cls.from_dict(yaml.safe_load(f), verify_checksum=verify_checksum)

    @classmethod
    def from_dict(cls, data, verify_checksum=True):
        """
        Create :any:`ExperimentFiles` from `dict` representation

        Parameters
        ----------
        data : dict
            The dictionary representation, e.g. as created by :meth:`to_dict`.
        verify_checksum : bool, optional
            Verify checksum of all files.
        """
        exp_id, src_dir_files = data.popitem()
        assert not data
        src_dir = list(src_dir_files.keys())
        obj = cls(exp_id, src_dir=src_dir)
        obj._files = {  # pylint: disable=protected-access
            InputFile.from_dict({p: f}, src_dir=src_dir, verify_checksum=verify_checksum)
            for src_dir, files in src_dir_files.items() for p, f in files.items()
        }
        return obj

    def to_yaml(self, output_path):
        """
        Save list of experiment files and their meta data as a YAML file.

        Parameters
        ----------
        output_path : str or :any:`pathlib.Path`
            File name for the YAML file.
        """
        with Path(output_path).open('w') as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False)

    def to_dict(self):
        """
        Create a dictionary containing the list of experiment files and the
        meta data stored for them.
        """
        data = defaultdict(dict)
        for f in self.files:
            data[str(f.src_dir)].update(f.to_dict())
        return {self.exp_id: dict(data)}

    def _input_file_in_src_dir(self, input_file):
        """
        Find :attr:`input_file` in :attr:`ExperimentFiles.src_dir`

        The file is identified by comparing file name and checksum.
        """
        if not self.src_dir:
            return input_file
        candidates = [
            (path, src_dir)
            for src_dir in self.src_dir
            for path in src_dir.glob('**/{}'.format(input_file.path.name))
        ]
        for path, src_dir in candidates:
            candidate_file = InputFile(path, src_dir)
            if candidate_file.checksum == input_file.checksum:
                return candidate_file
        warning('Input file %s not found in source directories', input_file.path.name)
        return input_file

    def add_file(self, *filepath, compute_metadata=True):
        """
        Add one or more files to the list of input files for the experiment

        Parameters
        ----------
        filepath : (list of) str or :any:`pathlib.Path`
            One or multiple file paths to add.
        """
        for path in filepath:
            input_file = InputFile(path, compute_metadata=compute_metadata)
            input_file = self._input_file_in_src_dir(input_file)
            self._files.add(input_file)

    def add_input_file(self, *input_file):
        """
        Add one or more :any:`InputFile` to the list of input files

        Parameters
        ----------
        Input_file : (list of) :any:`InputFile`
            One or multiple input file instances to add.
        """
        self._files += [*input_file]

    @property
    def files(self):
        """
        The set of :any:`InputFile` for the experiment
        """
        return self._files

    @property
    def exp_files(self):
        """
        The set of experiment-specific :any:`InputFile`
        """
        return {f for f in self.files if '/ifsdata/' not in str(f.fullpath)}

    @property
    def ifsdata_files(self):
        """
        The set of static ifsdata files used by the experiment
        """
        return {f for f in self.files if '/ifsdata/' in str(f.fullpath)}

    @staticmethod
    def _create_tarball(files, output_basename, basedir=None):
        """
        Create a tarball containing :attr:`files`

        Parameters
        ----------
        files : list of str
            The files to be included in the tarball.
        output_basename : str
            The base name without suffix of the tarball.
        basedir : str, optional
            If given, :attr:`files` are interpreted as relative to this.
        """
        output_file = Path(output_basename).with_suffix('.tar.gz')
        cmd = ['tar', 'cvzhf', str(output_file)]
        if basedir:
            cmd += ['-C', str(basedir)]
        cmd += files
        execute(cmd)

    def to_tarball(self, output_dir, with_ifsdata=False):
        """
        Create tarballs containing all input files.

        Parameters
        ----------
        output_dir : str or :any:`pathlib.Path`
            Output directory for tarballs.
        with_ifsdata : bool, optional
            Create also a tarball containing the ifsdata files used by
            this experiment (default: disabled).
        """
        output_dir = Path(output_dir)

        exp_files = defaultdict(list)
        for f in self.exp_files:
            exp_files[f.src_dir] += [f.path]
        for src_dir, files in exp_files.items():
            output_basename = output_dir/(src_dir.name or 'other')
            self._create_tarball(files, output_basename, basedir=src_dir)

        if with_ifsdata:
            ifsdata_files = list(self.ifsdata_files)
            if ifsdata_files:
                basedir = ifsdata_files[0].src_dir
                files = [f.path for f in ifsdata_files]
                output_basename = output_dir/'ifsdata'
                self._create_tarball(files, output_basename, basedir=basedir)


class Benchmark(ABC):
    """
    Definition of a general benchmark setup.
    """

    def __init__(self, **kwargs):
        self.expid = kwargs.get('expid')
        self.rundir = kwargs.get('rundir', None)

        self.ifs = kwargs.get('ifs')

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

        :param rundir: Run directory to copy/symlink input data into
        :param srcdir: One or more source directories to search for input data
        :param copy: Copy files intp `rundir` instead of symlinking them
        :param force: Force delete existing input files and re-link/copy
        """
        srcdir = as_tuple(kwargs.get('srcdir'))
        rundir = Path(kwargs.get('rundir'))
        copy = kwargs.pop('copy', False)
        force = kwargs.pop('force', False)
        ifsdata = kwargs.get('ifsdata', None)

        if ifsdata is not None:
            symlink_data(Path(ifsdata), rundir/'ifsdata', force=force)

        # Copy / symlink input files into rundir
        for path in cls.input_files:
            path = Path(path)
            dest = Path(rundir) / path
            candidates = flatten([list(Path(s).glob('**/%s' % path.name)) for s in srcdir])
            if len(candidates) == 0:
                warning('Input file %s not found in %s' % (path.name, srcdir))
                continue
            elif len(candidates) == 1:
                source = candidates[0]
            else:
                warning('More than one input file %s found in %s' % (path.name, srcdir))
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

    def run(self, **kwargs):
        """
        Run the specified benchmark and validate against stored results.
        """
        if 'rundir' in kwargs:
            if kwargs['rundir'] != self.rundir:
                error('Stored run directory: %s' % self.rundir)
                error('Given run directory:  %s' % kwargs['rundir'])
                raise RuntimeError('Conflicting run directories provided!')
        else:
            kwargs['rundir'] = self.rundir

        try:
            self.ifs.run(**kwargs)

        except CalledProcessError:
            error('Benchmark run failed: %s' % kwargs)
            exit(-1)

        # Provide DrHook output path only if DrHook is active
        drhook = kwargs.get('drhook', DrHook.OFF)
        drhook_path = None if drhook == DrHook.OFF else self.rundir/'drhook.*'

        dryrun = kwargs.get('dryrun', False)
        if not dryrun:
            return RunRecord.from_run(nodefile=self.rundir/'NODE.001_01', drhook=drhook_path)
