#!/usr/bin/env python3

from logging import FileHandler
from pathlib import Path
from collections import defaultdict
import click
import yaml

from ifsbench import logger, DEBUG, info, DarshanReport, execute, gettempdir


class ExperimentFiles:
    """
    Helper class to store information about all files required 
    to run an experiment

    Files are categorized according to their path.

    Parameters
    ----------
    exp_id : str
        The id of the experiment
    """

    file_categories = {
        'namelist': 'namelistfc',  # The input namelist
        '{exp_id}': '/{exp_id}/',  # The experiment-specific files
        'rdxdata': '/rdxdata/',    # The static files from rdxdata (e.g., ifsdata, chem, etc.)
    }
    """
    Pairs of `(category, path-identifier)` to specify categories into which
    experiment files are sorted (and packed separately)
    """

    def __init__(self, exp_id):
        self.exp_id = exp_id
        self.categories = {
            title.format(exp_id=self.exp_id): identifier.format(exp_id=self.exp_id)
            for title, identifier in self.file_categories.items() if identifier is not None
        }
        self._files = defaultdict(dict)

    @classmethod
    def from_summary(cls, summary, verify_checksums=True):
        """
        Create object from a summary

        Parameters
        ----------
        summary : dict
            The summary as procuded by :meth:`ExperimentFiles.summary`.
        verify_checksums : bool, optional
            Verify that files and checksums exist (slower, default: True).
        """
        exp_id, categorized_files = summary.popitem()
        assert not summary
        obj = cls(exp_id)
        if not verify_checksums:
            obj._files.update(categorized_files)
        else:
            for title, files in categorized_files.items():
                for f in files.values():
                    obj.add_file(f['path'])
                    assert f['sha256sum'] == obj.get_file(f['path'])['sha256sum']
        return obj

    def update(self, other):
        """
        Update file list with files from another experiment
        """
        for title in self.categories:
            if title in other.categorized_files and other.categorized_files[title]:
                self._files[title].update(other.categorized_files[title])

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

    def _get_category(self, filepath):
        """Obtain corresponding category for a given file path"""
        for title, identifier in self.categories.items():
            if identifier in str(filepath):
                return title
        return 'other'

    def add_file(self, *filepath):
        """Add a file to the list of input files for the experiment"""
        for path in filepath:
            path = str(path)
            category = self._get_category(path)
            if not any(path == f['path'] for f in self._files[category].values()):
                self._files[category][path] = {
                    'path': path,
                    'sha256sum': self._sha256sum(path),
                    'size': self._size(path),
                }

    def get_file(self, filepath):
        """Find a file in the list of input files for the experiment and
        return meta data"""
        filepath = str(filepath)
        for files in self._files.values():
            if filepath in files:
                # Path matches key
                return files[filepath]
            for f in files.values():
                # Path matches absolute path
                if f['path'] == filepath:
                    return f
        raise KeyError('{} not found in ExperimentFiles for {}'.format(filepath, self.exp_id))

    @property
    def categorized_files(self):
        """
        Get input files categorized according to :attr:`file_categories`
        """
        return dict(self._files)

    @staticmethod
    def common_basedir(paths):
        """
        Find the common base directory for all given paths
        """
        if len(paths) == 1:
            return str(Path(list(paths)[0]).parent)
        all_parts = [Path(p).parts for p in paths]
        all_parts = map(set, zip(*all_parts))  # Transpose list of lists and convert to sets
        common_parts = []
        for part in all_parts:
            if len(part) > 1:
                break
            common_parts += [part.pop()]
        return str(Path(*common_parts))

    def convert_to_relative_paths(self):
        """
        Compute relative paths for all files in a category
        """
        for title in self._files:
            if not self._files[title]:
                continue
            basedir = self.common_basedir([f['path'] for f in self._files[title].values()])
            self._files[title] = {str(Path(f['path']).relative_to(basedir)): f for f in self._files[title].values()}

    def summary(self):
        """Create a summary of the input files of the experiment"""
        self.convert_to_relative_paths()
        return {self.exp_id: self.categorized_files}

    @staticmethod
    def _tar_files(files, basedir, output_basename):
        """Create an archive containining :attr:`files` relative to a base
        directory :attr:`basedir`. Base name of the output file (without
        suffix) is given by :attr:`output_basename`.""" 
        output_file = Path(output_basename).with_suffix('.tar.gz')
        cmd = ['tar', 'cvzhf', str(output_file)]
        if basedir:
            cmd += ['-C', str(basedir)]
        cmd += files
        execute(cmd)

    def pack_files(self, output_path, include=None, exclude=None):
        """
        Create tarfile archives with all input files, categorized according to
        :attr:`file_categories`

        Parameters
        ----------
        output_path : str or :any:`pathlib.Path`
            Tarfiles are created in a directory :attr:`exp_id` under this path.
        include : list, optional
            A list of categories to include (default: all).
        exclude : list, optional
            A list of categories to exclude (default: none).
            This takes precedence over :attr:`include`.
        """
        self.convert_to_relative_paths()
        output_path = Path(output_path)
        for title, files in self._files.items():
            if exclude and title in exclude:
                continue
            if include and title not in include:
                continue
            if not files:
                continue
            filepaths = list(files.keys())
            path = files[filepaths[0]]['path']
            basedir = path[:path.find(filepaths[0])]
            self._tar_files(filepaths, basedir, output_path/title)

    @staticmethod
    def _untar_files(file, output_path):
        """Extract an archive :attr:`file` into a directory :attr:`output_path`"""
        cmd = ['tar', 'xvzf', str(file), '-C', str(output_path)]
        execute(cmd)

    def unpack_files(self, basedir, output_path, include=None, exclude=None, verify_checksums=True):
        basedir = Path(basedir)
        for title, files in self._files.items():
            if exclude and title in exclude:
                continue
            if include and title not in include:
                continue
            archive_file = (basedir/title).with_suffix('.tar.gz')
            self._untar_files(archive_file, output_path)
            if verify_checksums:
                for file, data in files.items():
                    if self._sha256sum(output_path/file) != data['sha256sum']:
                        raise ValueError('Checksum for {} does not match'.format(file))            


@click.group()
@click.option('--debug/--no-debug', default=False, show_default=True,
              help='Enable / disable debug mode with verbose logging.')
@click.option('--log', type=click.Path(writable=True),
              help='Write more detailed information to a log file.')
@click.pass_context
def cli(ctx, debug, log):  # pylint:disable=redefined-outer-name
    """
    Define and store the generic options available to all commands.
    """
    ctx.obj['DEBUG'] = debug
    if debug:
        logger.setLevel(DEBUG)
    if log:
        file_handler = FileHandler(log, mode='w')
        file_handler.setLevel(DEBUG)
        logger.addHandler(file_handler)


@cli.command()
@click.option('--include', required=True, multiple=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
              help='The <exp_id>.yml file for which to pack files. This can be given multiple times.')
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.pass_context
def pack_rdxdata(ctx, include, output_dir):  # pylint: disable=unused-argument
    """Read yaml-files from pack-experiment and pack all listed rdxdata into a single archive"""
    rdxdata_files = ExperimentFiles('rdxdata')
    for summary_file in include:
        with Path(summary_file).open() as f:
            exp_files = ExperimentFiles.from_summary(yaml.safe_load(f))
        rdxdata_files.update(exp_files)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rdxdata_files.pack_files(output_dir, include=['rdxdata'])


@cli.command()
@click.option('--input-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Input directory for packed files (default: current working directy)')
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for unpacked files (default: current working directy)')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
              help='Verify checksum of unpacked files (default: enabled)')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
@click.pass_context
def unpack_rdxdata(ctx, input_dir, output_dir, verify_checksum, inputs):  # pylint: disable=unused-argument
    """
    Read yaml-files produced by pack-experiment and unpack and verify
    corresponding rdxdata files    

    INPUTS can be one or multiple <exp_id>.yml.
    """
    rdxdata_files = ExperimentFiles('rdxdata')
    for summary_file in inputs:
        with Path(summary_file).open() as f:
            exp_files = ExperimentFiles.from_summary(yaml.safe_load(f), verify_checksums=False)
        rdxdata_files.update(exp_files)
    output_dir = Path(output_dir)/'rdxdata'
    output_dir.mkdir(parents=True, exist_ok=True)
    rdxdata_files.unpack_files(input_dir, output_dir, include=['rdxdata'], verify_checksums=verify_checksum)


@cli.command()
@click.option('--exp-id', required=True, type=str, help='the ID of the experiment')
@click.option('--darshan-log', required=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
              help='the Darshan logfile')
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.option('--with-rdxdata/--without-rdxdata', default=False, type=bool,
               help=('pack rdxdata files, such as ifsdata '
                     '(default: capture only in <exp_id>.yml for later packaging with pack-rdxdata)'))
@click.pass_context
def pack_experiment(ctx, exp_id, darshan_log, output_dir, with_rdxdata):  # pylint: disable=unused-argument
    """Pack input data of an experiment for standalone use"""

    # Parse the darshan report
    report = DarshanReport(darshan_log)

    # Find all reads and writes from modules POSIX and STDIO
    posix_rec = report.records['POSIX']
    posix_reads = posix_rec[(posix_rec['<counter>'] == 'POSIX_READS') & (posix_rec['<value>'] > 0)]
    posix_writes = posix_rec[(posix_rec['<counter>'] == 'POSIX_WRITES') & (posix_rec['<value>'] > 0)]

    stdio_rec = report.records['STDIO']
    stdio_reads = stdio_rec[(stdio_rec['<counter>'] == 'STDIO_READS') & (stdio_rec['<value>'] > 0)]
    stdio_writes = stdio_rec[(stdio_rec['<counter>'] == 'STDIO_WRITES') & (stdio_rec['<value>'] > 0)]

    # Select input files (files that are read but never written)
    read_files = set(posix_reads['<file name>']) | set(stdio_reads['<file name>'])
    write_files = set(posix_writes['<file name>']) | set(stdio_writes['<file name>'])
    input_files = read_files - write_files

    # Setup output directory
    output_dir = Path(output_dir)/exp_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create input files overview
    exp_files = ExperimentFiles(exp_id)
    exp_files.add_file(*input_files)

    # Write input files summary
    summary_yml = output_dir/'{}.yml'.format(exp_id)
    with summary_yml.open('w') as f:
        yaml.safe_dump(exp_files.summary(), f, sort_keys=False) 

    # Pack experiment files
    exclude = []
    if not with_rdxdata:
        exclude += ['rdxdata']
    exp_files.pack_files(output_dir, exclude)


@cli.command()
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for unpacked files (default: current working directy).')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
              help='Verify checksum of unpacked files (default: enabled)')
@click.option('--with-rdxdata/--without-rdxdata', type=bool, default=False,
              help='Unpack also rdxdata archives (default: disabled)')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
@click.pass_context
def unpack_experiment(ctx, output_dir, verify_checksum, with_rdxdata, inputs):  # pylint: disable=unused-argument
    """
    Read yaml-files produced by pack-experiment and unpack all
    corresponding archives

    INPUTS can be one or multiple <exp_id>.yml, each optionally followed by a
    directory in which the archives corresponding to that experiment are
    stored. For yml-files with no directory specified, the current working
    directory is assumed.
    """
    # Match input files and input directories
    summary_files = {}
    inputs = list(reversed(inputs)) # reverse and use list as stack
    while inputs:
        summary_file = Path(inputs.pop())
        if inputs and not inputs[-1].endswith('.yml'):
            summary_files[summary_file] = Path(inputs.pop())
        else:
            summary_files[summary_file] = Path.cwd()
    # Set-up output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Unpack all files
    for summary_file, input_dir in summary_files.items():
        with Path(summary_file).open() as f:
            exp_files = ExperimentFiles.from_summary(yaml.safe_load(f), verify_checksums=False)
        exclude = []
        if not with_rdxdata:
            exclude += ['rdxdata']
        output_path = output_dir/exp_files.exp_id
        output_path.mkdir(exist_ok=True)
        exp_files.unpack_files(input_dir, output_path, verify_checksums=verify_checksum, exclude=exclude)


if __name__ == "__main__":
    cli(obj={})  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
