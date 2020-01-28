from pathlib import Path

from .arch import Workstation


__all__ = ['IFS']


class IFS(object):
    """
    A single instance of the IFS system that enables execution of
    individual binaries, as well as managing environment setup and
    sanity-checking input configurations.
    """

    def __init__(self, builddir, installdir=None):
        self.builddir = Path(builddir)
        self.installdir = installdir if installdir is None else Path(installdir)
        self.executable = 'ifsMASTER.DP'

    @property
    def binary(self):
        """
        Primary executable to run.
        """
        if self.installdir is not None:
            return (self.installdir/'bin')/self.executable
        if self.builddir is not None:
            return (self.builddir/'bin')/self.executable

    def verify_namelist(self, namelist):
        """
        Check correctness of namelist entries against compiled
        namelist headers.
        """
        raise NotImplementedError('Not yet done...')

    def run(self, rundir, nproc=1, nproc_io=0, nthread=1, hyperthread=1, **kwargs):
        env = kwargs.pop('env', None)
        env = {} if env is None else env

        arch = kwargs.pop('env', None)
        arch = Workstation if arch is None else arch

        # Define the run directory to the IFS
        env['DATA'] = rundir

        # Add GRIB-specific paths
        env['GRIB_DEFINITION_PATH'] = self.builddir/'share/eccodes/definitions'
        env['GRIB_SAMPLES_PATH'] = self.builddir/'share/eccodes/ifs_samples/grib1_mlgrib2'

        # Set number of MPI processes and OpenMP threads
        env['NPROC'] = nproc - nproc_io
        env['NPROC_IO'] = nproc_io

        # TODO: Generate run-specific namelist

        cmd = ['%s' % self.executable]
        arch.run(cmd=cmd, nproc=nproc, nthread=nthread, hyperthread=hyperthread, env=env, **kwargs)
