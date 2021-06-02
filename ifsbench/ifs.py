from pathlib import Path
from os import getenv

from .arch import arch_registry, Workstation, XC40Cray, XC40Intel
from .drhook import DrHook
from .namelist import IFSNamelist

__all__ = ['IFS']


class IFS(object):
    """
    A single instance of the IFS system that enables execution of
    individual binaries, as well as managing environment setup and
    sanity-checking input configurations.
    """

    def __init__(self, builddir, sourcedir=None, installdir=None, nml_template=None):
        self.builddir = Path(builddir)
        self.sourcedir = None if sourcedir is None else Path(sourcedir)
        self.installdir = None if installdir is None else Path(installdir)

        # TODO: Parameterize for single-prec and surface models, etc.
        self.exec_name = 'ifsMASTER.DP'
        self.nml_template = nml_template

    @property
    def executable(self):
        """
        Primary executable to run.
        """
        if self.installdir is not None:
            return (self.installdir/'bin')/self.exec_name
        if self.builddir is not None:
            return (self.builddir/'bin')/self.exec_name

    def verify_namelist(self, namelist):
        """
        Check correctness of namelist entries against compiled
        namelist headers.
        """
        raise NotImplementedError('Not yet done...')

    def run(self, namelist, rundir, nproc=1, nproc_io=0, nthread=1, hyperthread=1, **kwargs):
        env = kwargs.pop('env', None)
        env = {} if env is None else env

        # Select architecture preset from registry
        arch = kwargs.pop('arch', None)
        arch = arch_registry[arch]

        # Set up DrHook according to preset
        drhook = kwargs.pop('drhook', None)
        if drhook is not None:
            env.update(drhook.env)

        # Define the run directory to the IFS
        env['DATA'] = rundir

        # Add GRIB-specific paths
        env['GRIB_DEFINITION_PATH'] = self.builddir/'share/eccodes/definitions'
        env['GRIB_SAMPLES_PATH'] = self.builddir/'share/eccodes/ifs_samples/grib1_mlgrib2'

        # Add additional lib location so that we can pick up libblack.so
        # TODO: Suspended for Cray runs... :( Needs proper fix!
        if arch is not XC40Cray and arch is not XC40Intel:
            new_path = str(self.builddir/'ifs-source') + ':' + getenv('LD_LIBRARY_PATH', '')
            env['LD_LIBRARY_PATH'] = new_path

        # Set number of MPI processes and OpenMP threads
        env['NPROC'] = nproc - nproc_io
        env['NPROC_IO'] = nproc_io

        # Of course, we need to insert the number of MPI ranks into the config file
        nml = IFSNamelist(namelist=namelist, template=self.nml_template)
        nml['NAMPAR0']['NPROC'] = nproc - nproc_io
        nml['NAMIO_SERV']['NPROC_IO'] = nproc_io
        nml.write('fort.4', force=True)

        cmd = ['%s' % self.executable]
        arch.run(cmd=cmd, nproc=nproc, nthread=nthread, hyperthread=hyperthread, env=env, **kwargs)
