#!/usr/bin/env python3

from logging import FileHandler
from pathlib import Path
import click

from ifsbench import (
    logger, DEBUG, gettempdir, ExperimentFiles,
    DarshanReport, read_files_from_darshan, write_files_from_darshan
)

@click.group()
@click.option('--debug/--no-debug', default=False, show_default=True,
              help='Enable / disable debug mode with verbose logging.')
@click.option('--log', type=click.Path(writable=True),
              help='Write more detailed information to a log file.')
@click.pass_context
def cli(ctx, debug, log):
    """
    Command-line interface for IFSbench

    This provides a number of commands to pack and unpack input
    files for IFS experiments.
    """
    ctx.obj['DEBUG'] = debug
    if debug:
        logger.setLevel(DEBUG)
    if log:
        file_handler = FileHandler(log, mode='w')
        file_handler.setLevel(DEBUG)
        logger.addHandler(file_handler)


@cli.command()
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=False,
              help='Verify checksum of files listed in YAML files (default: disabled)')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
def pack_ifsdata(output_dir, verify_checksum, inputs):
    """
    Create a tarball with ifsdata files for (multiple) YAML files from
    pack-experiment

    INPUTS is one or multiple <exp_id>.yml files.

    Note that checksum verification is disabled by default for this command
    because experiment-specific files mentioned in YAML files are possibly
    already cleaned up.
    """
    ifsdata_files = ExperimentFiles('ifsdata')
    for summary_file in inputs:
        exp_files = ExperimentFiles.from_yaml(summary_file, verify_checksum=verify_checksum)
        ifsdata_files.add_input_file(*exp_files.ifsdata_files)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ifsdata_files.to_tarball(output_dir, with_ifsdata=True)


@cli.command()
@click.option('--input-dir', default=Path.cwd(),
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
              help='Input directory for ifsdata tarball (default: current working directory)')
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True),
              help='Output directory for unpacked files (default: current working directory)')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
              help='Verify checksum of unpacked files (default: enabled)')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
def unpack_ifsdata(input_dir, output_dir, verify_checksum, inputs):
    """
    Read YAML files produced by pack-experiment and unpack and verify
    corresponding ifsdata files

    INPUTS can be one or multiple <exp_id>.yml.
    """
    # Build ifsdata YAML file
    ifsdata_files = ExperimentFiles('ifsdata')
    for summary_file in inputs:
        exp_files = ExperimentFiles.from_yaml(summary_file, verify_checksum=False)
        ifsdata_files.add_input_file(*exp_files.ifsdata_files)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ifsdata_yaml = gettempdir()/'ifsdata.yml'
    ifsdata_files.to_yaml(ifsdata_yaml)

    # Extract all ifsdata files
    ExperimentFiles.from_tarball(ifsdata_yaml, input_dir, output_dir, ifsdata_dir=output_dir,
                                 with_ifsdata=True, verify_checksum=verify_checksum)


@cli.command()
@click.option('--exp-id', required=True, type=str, help='ID of the experiment')
@click.option('--darshan-log', required=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
              help='Darshan logfile (produced by Darshan during execution)')
@click.option('--input-dir', required=True, multiple=True,
              type=click.Path(file_okay=False, dir_okay=True, readable=True),
              help='Data directory relative to which input files are searched. Can be given multiple times.')
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for tarballs (default: current working directory)')
@click.option('--with-ifsdata/--without-ifsdata', default=False, type=bool,
               help=('Pack files in ifsdata (default: capture only in <exp_id>.yml '
                     'for later packaging with pack-ifsdata)'))
def pack_experiment(exp_id, darshan_log, input_dir, output_dir, with_ifsdata):
    """Pack input files of an experiment for standalone use"""

    # Parse the darshan report
    report = DarshanReport(darshan_log)
    read_files = read_files_from_darshan(report)
    write_files = write_files_from_darshan(report)
    input_files = read_files - write_files

    # Create input files overview
    exp_files = ExperimentFiles(exp_id, src_dir=input_dir)
    exp_files.add_file(*input_files)

    # Setup output directory
    output_dir = Path(output_dir)/exp_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write input files summary
    summary_yml = output_dir/'{}.yml'.format(exp_id)
    exp_files.to_yaml(summary_yml)

    # Pack experiment files
    exp_files.to_tarball(output_dir, with_ifsdata=with_ifsdata)


@cli.command()
@click.option('--input-dir', default=Path.cwd(), multiple=True,
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help=('Input directory for tarballs (default: current working directory). '
                    'Can be given multiple times.'))
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for unpacked files (default: current working directory).')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
              help='Verify checksum of unpacked files (default: enabled)')
@click.option('--with-ifsdata/--without-ifsdata', type=bool, default=False,
              help='Unpack ifsdata archives (default: disabled)')
@click.option('--ifsdata-input-dir', default=None, type=click.Path(file_okay=False, dir_okay=True),
              help='Use a different input directory for joint ifsdata tarball.')
@click.option('--ifsdata-output-dir', default=None, type=click.Path(file_okay=False, dir_okay=True),
              help='Use a different joint output directory for ifsdata files.')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.pass_context
def unpack_experiment(ctx, input_dir, output_dir, verify_checksum, with_ifsdata,
                      ifsdata_input_dir, ifsdata_output_dir, inputs):
    """
    Read yaml-files produced by pack-experiment and unpack all
    corresponding archives

    INPUTS can be one or multiple <exp_id>.yml files.
    """
    # Set-up output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if ifsdata_output_dir is None:
        ifsdata_output_dir = output_dir
    else:
        ifsdata_output_dir = Path(ifsdata_output_dir)
        ifsdata_output_dir.mkdir(parents=True, exist_ok=True)

    # Unpack ifsdata files if asked for different directory
    if with_ifsdata and ifsdata_input_dir is not None:
        ctx.invoke(unpack_ifsdata, input_dir=ifsdata_input_dir, output_dir=ifsdata_output_dir,
                   verify_checksum=verify_checksum, inputs=inputs)

    # Unpack all files
    inplace_ifsdata = with_ifsdata and ifsdata_input_dir is None
    for summary_file in inputs:
        ExperimentFiles.from_tarball(summary_file, input_dir, output_dir, ifsdata_dir=ifsdata_output_dir,
                                     with_ifsdata=inplace_ifsdata, verify_checksum=verify_checksum)


if __name__ == "__main__":
    cli(obj={})  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
