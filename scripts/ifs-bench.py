#!/usr/bin/env python3

from logging import FileHandler
from pathlib import Path
import tarfile
import click

from ifsbench import logger, DEBUG, DarshanReport

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


#@cli.command(help='Pack input data of an experiment for standalone use')
@cli.command()
@click.option('--darshan-log', required=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
              help='The log file containing Darshan output')
@click.option('--exp-id', required=True, type=str, help='The ID of the experiment')
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.pass_context
def pack_experiment(ctx, darshan_log, exp_id, output_dir):  # pylint: disable=unused-argument
    """Pack input data of an experiment for standalone use"""
    report = DarshanReport(darshan_log)

    posix_rec = report.records['POSIX']
    posix_reads = posix_rec[(posix_rec['<counter>'] == 'POSIX_READS') & (posix_rec['<value>'] > 0)]
    posix_writes = posix_rec[(posix_rec['<counter>'] == 'POSIX_WRITES') & (posix_rec['<value>'] > 0)]

    stdio_rec = report.records['STDIO']
    stdio_reads = stdio_rec[(stdio_rec['<counter>'] == 'STDIO_READS') & (stdio_rec['<value>'] > 0)]
    stdio_writes = stdio_rec[(stdio_rec['<counter>'] == 'STDIO_WRITES') & (stdio_rec['<value>'] > 0)]

    read_files = set(posix_reads['<file name>']) | set(stdio_reads['<file name>'])
    write_files = set(posix_writes['<file name>']) | set(stdio_writes['<file name>'])
    input_files = read_files - write_files

    exp_files = set(f for f in input_files if '/{}/'.format(exp_id) in f)
    ifsdata_files = set(f for f in input_files if '/ifsdata/' in f)
    other_files = input_files - exp_files - ifsdata_files

    output_files = set(f for f in write_files - read_files if '/log/' in f)

    print('exp_files:')
    print('  ' + '\n  '.join(exp_files) + '\n')
    print('ifsdata_files:')
    print('  ' + '\n  '.join(ifsdata_files) + '\n')
    print('other_files:')
    print('  ' + '\n  '.join(other_files) + '\n')
    print('output_files:')
    print('  ' + '\n  '.join(output_files) + '\n')

    class RelativePath:
        def __init__(self, relative_to):
            self.relative_to = relative_to

        def __call__(self, tarinfo):
            start = tarinfo.name.find(self.relative_to)
            tarinfo.name = tarinfo.name[start+1:]
            return tarinfo

    def strip_path(tarinfo):
        tarinfo.name = Path(tarinfo.name).name
        return tarinfo

    output_dir = Path(output_dir)
    with tarfile.open(output_dir/'ifsdata.tar.gz', 'w:gz', dereference=True) as tar:
        for f in ifsdata_files:
            tar.add(f, filter=RelativePath('/ifsdata/'))
    with tarfile.open(output_dir/'{}.tar.gz'.format(exp_id), 'w:gz', dereference=True) as tar:
        for f in exp_files:
            tar.add(f, filter=RelativePath('/{}/'.format(exp_id)))
    with tarfile.open(output_dir/'other.tar.gz', 'w:gz', dereference=True) as tar:
        for f in other_files:
            tar.add(f, filter=RelativePath('/rdxdata/'))
    with tarfile.open(output_dir/'output.tar.gz', 'w:gz', dereference=True) as tar:
        for f in output_files:
            tar.add(f, filter=strip_path)


if __name__ == "__main__":
    cli(obj={})  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
