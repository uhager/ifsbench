#!/usr/bin/env python3

from logging import FileHandler
from pathlib import Path
from shutil import copy
import click
import yaml

from ifsbench import logger, DEBUG, info, DarshanReport, execute, gettempdir


class ExperimentFiles:
    """
    Helper class to store information about all files required 
    to run an experiment
    """

    file_categories = {
        'namelist': 'namelistfc',
        '{exp_id}': '/{exp_id}/',
        'ifsdata': '/ifsdata/',
    }

    def __init__(self, exp_id):
        self.exp_id = exp_id
        self.files = {}

    @classmethod
    def from_summary(cls, summary):
        assert isinstance(summary, dict) and len(summary) == 1
        exp_id, categorized_files = summary.popitem()
        assert not summary
        obj = cls(exp_id)
        return obj

    @staticmethod
    def _sha256sum(filepath):
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
        filepath = Path(filepath)
        return filepath.stat().st_size

    def add_file(self, *filepath):
        """Add a file to the list of input files for the experiment"""
        for path in filepath:
            path = str(path)
            if path not in self.files:
                self.files[path] = {
                    'path': path,
                    'sha256sum': self._sha256sum(path),
                    'size': self._size(path),
                }

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

    def get_categorized_files(self, relative_paths=True):
        """
        Get input files categorized according to :attr:`file_categories`
        """
        # The categories with identifier
        categories = {
            title.format(exp_id=self.exp_id): identifier.format(exp_id=self.exp_id)
            for title, identifier in self.file_categories.items() if identifier is not None
        }

        # The "other files" category
        other_files_title = [t for t, i in self.file_categories.items() if i is None]
        assert len(other_files_title) <= 1
        other_files_title = other_files_title[0] if other_files_title else None

        # Put all files into their categories
        available_files = set(self.files.keys())
        categorized_files = {}
        for title, identifier in categories.items():
            categorized_files[title] = {f: self.files[f] for f in available_files if identifier in f}
            available_files -= set(categorized_files[title].keys())

        # Strip common base directory
        if relative_paths:
            for title in categorized_files:
                if not categorized_files[title]:
                    continue
                basedir = self.common_basedir(categorized_files[title])
                categorized_files[title] = {
                    str(Path(f).relative_to(basedir)): d for f, d in categorized_files[title].items()
                }

        # Treat all remaining files
        categorized_files['other'] = {f: self.files[f] for f in available_files}
        available_files.clear()
        if relative_paths and categorized_files['other']:
            basedir = self.common_basedir(categorized_files['other'])
            categorized_files['other'] = {
                str(Path(f).relative_to(basedir)): d for f, d in categorized_files['other'].items()
            }

        return categorized_files

    def summary(self):
        """Create a summary of the input files of the experiment"""
        return {self.exp_id: self.get_categorized_files()}

    @staticmethod
    def _tar_files(files, basedir, output_basename):
        """Create an archive containining :attr:`files` relative to a base
        directory :attr:`basedir`. Base name of the output file (without
        suffix) is given by :attr:`output_basename`.""" 
        output_file = Path(output_basename).with_suffix('.tar.gz')
        cmd = ['tar', 'cvzhf', str(output_file), '-C', str(basedir), *files]
        execute(cmd)

    def pack_files(self, output_path, exclude=None):
        """
        Create tarfile archives with all input files, categorized according to
        :attr:`file_categories`

        Parameters
        ----------
        output_path : str or :any:`pathlib.Path`
            Tarfiles are created in a directory :attr:`exp_id` under this path.
        exclude : list, optional
            Give a list of categories to exclude.
        """
        output_path = Path(output_path)
        for title, files in self.get_categorized_files().items():
            if exclude and title in exclude:
                continue
            if not files:
                continue
            filepaths = list(files.keys())
            path = files[filepaths[0]]['path']
            basedir = path[:path.find(filepaths[0])]
            self._tar_files(filepaths, basedir, output_path/title)


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
              help='The <exp_id>.yml file for which to pack files.')
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.option('--with-ifsdata/--without-ifsdata', default=True, type=bool,
              help='Pack ifsdata input files.')
@click.option('--with-other/--without-other', default=True, type=bool,
              help='Pack other input files (not located in ifsdata).')
@click.pass_context
def pack_data(ctx, include, output_dir, with_ifsdata, with_other):  # pylint: disable=unused-argument
    exp_files = ExperimentFiles('static_data')
    for summary_file in include:
        with Path(summary_file).open() as f:
            summary = yaml.safe_load(f)
        exp_id, categorized_files = summary.popitem()
        if with_ifsdata:
            for file in categorized_files.get('ifsdata', {}).values():
                exp_files.add_file(file['path'])
        if with_other:
            for file in categorized_files.get('other', {}).values():
                exp_files.add_file(file['path'])
    exp_files.pack_files(output_dir)


@cli.command()
@click.option('--exp-id', required=True, type=str, help='The ID of the experiment')
@click.option('--darshan-log', required=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
              help='The log file containing Darshan output')
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.option('--with-ifsdata', default=False, type=bool,
               help='Pack ifsdata files (default: only captured for later packaging with pack_data)')
@click.option('--with-other', default=False, type=bool,
               help='Pack other data files (default: only captured for later packaging with pack_data)')
@click.pass_context
def pack_experiment(ctx, exp_id, darshan_log, output_dir, with_ifsdata, with_other):  # pylint: disable=unused-argument
    """Pack input data of an experiment for standalone use"""

    # Output helpers
    def relative_paths(files, basedir_identifier):
        """Convert filenames to relative paths, relative to a base directory
        identified by :attr:`basedir_identifier`."""
        files = list(files)
        basedir_pos = files[0].find(basedir_identifier)
        basedir = files[0][:basedir_pos]
        files = [f[basedir_pos+1:] for f in files]
        return basedir, files

    def tar_filename(basedir, stem):
        """Generate filename for output archive."""
        return (basedir/stem).with_suffix('.tar.gz')

    def tar_files(files, basedir, output_file):
        """Create an archive containining :attr:`files` relative to a base
        directory :attr:`basedir`. Base name of the output file (without
        suffix) is given by :attr:`output_basename`.""" 
        cmd = ['tar', 'cvzhf', str(output_file), '-C', str(basedir), *files]
        execute(cmd)

    def metadata_files(files, basedir):
        """Create meta data (such as checksum, original path etc.) for
         a set of files."""
        metadata = {}
        with logfile.open() as f:
            for l in f.readlines():
                checksum, name = l.split()
                filepath = Path(basedir)/name
                stat = filepath.stat()
                metadata[name] = {
                    'sha256sum': checksum,
                    'path': str(filepath),
                    'size': stat.st_size,
                }
        return metadata

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
    if not with_ifsdata:
        exclude += ['ifsdata']
    if not with_other:
        exclude += ['other']
    exp_files.pack_files(output_dir, exclude)
    return

    # Categorize input files
    namelist_files = set(f for f in input_files if Path(f).name == 'namelistfc')
    ifsdata_files = set(f for f in input_files if '/ifsdata/' in f) - namelist_files
    exp_files = set(f for f in input_files if '/{}/'.format(exp_id) in f) - namelist_files
    rdxdata_files = input_files - ifsdata_files - namelist_files - exp_files

    # Select output files (files that are written but never read)
    output_files = set(f for f in write_files - read_files if '/log/' in f)

    # Some meta-data
    summary = {}

    # Collect summary for all files
    if namelist_files:
        summary[exp_id]
        for namelist in namelist_files:
            filepath = Path(namelist)
            metadata = metadata_files([filepath.name], filepath.parent)
            summary[exp_id][filepath.name] = metadata[filepath.name]
            copy(namelist, output_dir/filepath.name)

    if exp_files:
        exp_basedir, exp_files = relative_paths(exp_files, '/{}/'.format(exp_id))
        exp_tarfile = tar_filename(output_dir, exp_id) 
        summary[exp_id][exp_tarfile.name] = metadata_files(exp_files, exp_basedir)
        tar_files(exp_files, exp_basedir, exp_tarfile)

    if output_files:
        output_basedir, output_files = relative_paths(output_files, '/{}/'.format(exp_id))
        output_tarfile = tar_filename(output_dir, 'output_{}'.format(exp_id))
        summary[exp_id][output_tarfile.name] = metadata_files(output_files, output_basedir)
        tar_files(output_files, output_basedir, output_tarfile)

    if rdxdata_files:
        rdxdata_basedir, rdxdata_files = relative_paths(rdxdata_files, '/rdxdata/')
        rdxdata_tarfile = tar_filename(output_dir, 'rdxdata')
        summary[exp_id][rdxdata_tarfile.name] = metadata_files(rdxdata_files, rdxdata_basedir)
        if with_rdxdata:
            tar_files(rdxdata_files, rdxdata_basedir, rdxdata_tarfile)

    if ifsdata_files:
        ifsdata_basedir, ifsdata_files = relative_paths(ifsdata_files, '/ifsdata/')
        ifsdata_tarfile = tar_filename(output_dir, 'ifsdata')
        summary[exp_id][ifsdata_tarfile.name] = metadata_files(ifsdata_files, ifsdata_basedir)
        if with_ifsdata:
            tar_files(ifsdata_files, ifsdata_basedir, ifsdata_tarfile)

    # Setup output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write input files summary
    summary_yml = output_dir/'{}.yml'.format(exp_id)
    with summary_yml.open('w') as f:
        yaml.dump(summary, f, sort_keys=False) 

    # Create input file archives
    pack_files(summary)


if __name__ == "__main__":
    cli(obj={})  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
