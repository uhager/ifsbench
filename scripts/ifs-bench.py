#!/usr/bin/env python3

from logging import FileHandler
from pathlib import Path
import click

from ifsbench import (
    logger, DEBUG, ExperimentFiles,
    DarshanReport, read_files_from_darshan, write_files_from_darshan
)

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
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
def pack_ifsdata(output_dir, inputs):
    """
    Create a tarball with ifsdata files for (multiple) YAML files from
    pack-experiment

    INPUTS is one or multiple <exp_id>.yml files.
    """
    ifsdata_files = ExperimentFiles('ifsdata')
    for summary_file in inputs:
        exp_files = ExperimentFiles.from_yaml(summary_file)
        ifsdata_files.add_input_file(*exp_files.ifsdata_files)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ifsdata_files.to_tarball(output_dir, with_ifsdata=True)


# @cli.command()
# @click.option('--input-dir', default=Path.cwd(),
#               type=click.Path(file_okay=False, dir_okay=True, writable=True),
#               help='Input directory for packed files (default: current working directory)')
# @click.option('--output-dir', default=Path.cwd(),
#               type=click.Path(file_okay=False, dir_okay=True, writable=True),
#               help='Output directory for unpacked files (default: current working directory)')
# @click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
#               help='Verify checksum of unpacked files (default: enabled)')
# @click.argument('inputs', required=True, nargs=-1,
#                 type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
# @click.pass_context
# def unpack_rdxdata(ctx, input_dir, output_dir, verify_checksum, inputs):  # pylint: disable=unused-argument
#     """
#     Read yaml-files produced by pack-experiment and unpack and verify
#     corresponding rdxdata files
#
#     INPUTS can be one or multiple <exp_id>.yml.
#     """
#     rdxdata_files = ExperimentFiles('rdxdata')
#     for summary_file in inputs:
#         with Path(summary_file).open() as f:
#             exp_files = ExperimentFiles.from_summary(yaml.safe_load(f), verify_checksums=False)
#         rdxdata_files.update(exp_files)
#     output_dir = Path(output_dir)/'rdxdata'
#     output_dir.mkdir(parents=True, exist_ok=True)
#     rdxdata_files.unpack_files(input_dir, output_dir, include=['rdxdata'],
#                                verify_checksums=verify_checksum)


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


# @cli.command()
# @click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True, writable=True),
#               help='Output directory for unpacked files (default: current working directy).')
# @click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
#               help='Verify checksum of unpacked files (default: enabled)')
# @click.option('--with-rdxdata/--without-rdxdata', type=bool, default=False,
#               help='Unpack also rdxdata archives (default: disabled)')
# @click.argument('inputs', required=True, nargs=-1,
#                 type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
# @click.pass_context
# def unpack_experiment(ctx, output_dir, verify_checksum, with_rdxdata, inputs):  # pylint: disable=unused-argument
#     """
#     Read yaml-files produced by pack-experiment and unpack all
#     corresponding archives
#
#     INPUTS can be one or multiple <exp_id>.yml, each optionally followed by a
#     directory in which the archives corresponding to that experiment are
#     stored. For yml-files with no directory specified, the current working
#     directory is assumed.
#     """
#     # Match input files and input directories
#     summary_files = {}
#     inputs = list(reversed(inputs)) # reverse and use list as stack
#     while inputs:
#         summary_file = Path(inputs.pop())
#         if inputs and not inputs[-1].endswith('.yml'):
#             summary_files[summary_file] = Path(inputs.pop())
#         else:
#             summary_files[summary_file] = Path.cwd()
#     # Set-up output directory
#     output_dir = Path(output_dir)
#     output_dir.mkdir(parents=True, exist_ok=True)
#     # Unpack all files
#     for summary_file, input_dir in summary_files.items():
#         with Path(summary_file).open() as f:
#             exp_files = ExperimentFiles.from_summary(yaml.safe_load(f), verify_checksums=False)
#         exclude = []
#         if not with_rdxdata:
#             exclude += ['rdxdata']
#         output_path = output_dir/exp_files.exp_id
#         output_path.mkdir(exist_ok=True)
#         exp_files.unpack_files(input_dir, output_path, verify_checksums=verify_checksum, exclude=exclude)


if __name__ == "__main__":
    cli(obj={})  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
