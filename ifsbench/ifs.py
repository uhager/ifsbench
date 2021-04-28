from abc import ABC, abstractmethod
from pathlib import Path
from os import getenv

from .arch import arch_registry
from .drhook import DrHook
from .namelist import IFSNamelist

# Note: all IFS subclasses registered in cycle_registry are also exported
# at the end of this file
__all__ = ['IFS', 'cycle_registry']


class IFS(ABC):
    """
    Manage environment setup, configuration sanity checks and execution of IFS

    This class is specialized for every supported release of the IFS (called
    cycle). It is instantiated via the factory method :meth:`IFS.create_cycle`,
    using the subclass corresponding to the provided cycle.
    See :any:`cycles_registry` for all available cycles.

    Parameters
    ----------
    builddir : str or :any:`pathlib.Path`
        The build directory of the IFS.
    sourcedir : str or :any:`pathlib.Path`, optional
        The source code directory of the IFS.
    installdir : str or :any:`pathlib.Path`, optional
        The install directory of the IFS.
    nml_template : str or :any:`pathlib.Path`, optional
        The path to a namelist template.
    """

    def __init__(self, builddir, sourcedir=None, installdir=None, nml_template=None):
        assert getattr(self, 'cycle').startswith('cy')
        self.builddir = Path(builddir)
        self.sourcedir = None if sourcedir is None else Path(sourcedir)
        self.installdir = None if installdir is None else Path(installdir)
        self.nml_template = nml_template

    @staticmethod
    def create_cycle(cycle, *args, **kwargs):
        """
        Parameters
        ----------
        cycle : str
            The name of the IFS cycle to instantiate.
        *args :
            Positional arguments to provide to the cycle constructor
        **kwargs :
            Keyword arguments to provide to the cycle constructor
        """
        if cycle is None:
            cycle = 'default'
        return cycle_registry[cycle.lower()](*args, **kwargs)

    @property
    @abstractmethod
    def exec_name(self):
        """
        The name of the binary to run
        """

    @property
    def executable(self):
        """
        Primary executable to run

        This prefers the binary from the install directory, if given, otherwise
        uses the binary from the build directory.

        Returns
        -------
        pathlib.Path
            The path to the executable
        """
        if self.installdir is not None:
            return (self.installdir/'bin')/self.exec_name
        return (self.builddir/'bin')/self.exec_name

    def verify_namelist(self, namelist):
        """
        Check correctness of namelist entries against compiled
        namelist headers.
        """
        raise NotImplementedError('Not yet done...')

    def setup_env(self, **kwargs):
        """
        Define run environment

        This should be overriden by cycle-specific classes when necessary to
        add/modify the default environment defined here.

        :meth:`IFS.run` will call this method with all parameters provided to
        itself. The parameter list given below gives further details about
        parameters used in particular by this method.

        Parameters
        ----------
        rundir : str or :any:`pathlib.Path`
            The run directory for IFS execution
        nproc : int
            The total number of MPI ranks
        nproc_io : int
            The number of MPI ranks for the IO server
        drhook : :any:`DrHook`, optional
            DrHook-specific environment presets
        env : dict, optional
            An existing environment definition to use as a starting point.
        **kwargs :
            Other named parameters provided to :meth:`IFS.run`.
        """
        # Initialize environment
        env = kwargs.pop('env', None)
        env = {} if env is None else env

        # Define the run directory as data directory to the IFS
        env['DATA'] = kwargs.pop('rundir')

        # Set up DrHook according to preset
        drhook = kwargs.pop('drhook', None)
        if drhook is not None:
            assert isinstance(drhook, DrHook)
            env.update(drhook.env)

        # Add GRIB-specific paths
        env['GRIB_DEFINITION_PATH'] = str(self.builddir/'share/eccodes/definitions')
        env['GRIB_SAMPLES_PATH'] = str(self.builddir/'share/eccodes/ifs_samples/grib1_mlgrib2')

        # Set number of MPI processes and OpenMP threads
        nproc = kwargs['nproc']
        nproc_io = kwargs['nproc_io']
        assert isinstance(nproc, int) and isinstance(nproc_io, int)
        env['NPROC'] = nproc - nproc_io
        env['NPROC_IO'] = nproc_io

        return env

    def setup_nml(self, **kwargs):
        """
        Setup the IFS namelist

        This should be overridden by cycle-specific classes where necessary to
        add/modify the namelist created here.

        Parameters
        ----------
        namelist : :any:`f90nml.Namelist`
            A namelist to use as a basis for the IFS run that will be further
            modified by :meth:`IFS.setup_nml`
        nproc : int
            The total number of MPI ranks
        nproc_io : int
            The number of MPI ranks for the IO server
        fclen : str, optional
            Override the length of the forecast run (e.g., ``'h240'`` or
            ``'d10'``).
        **kwargs :
            Other named parameters provided to :meth:`IFS.run`.
        """
        nml = IFSNamelist(namelist=kwargs['namelist'], template=self.nml_template)

        # Insert the number of MPI ranks into the config file
        nml['NAMPAR0']['NPROC'] = kwargs['nproc'] - kwargs['nproc_io']
        nml['NAMIO_SERV']['NPROC_IO'] = kwargs['nproc_io']

        # Modify forecast length
        fclen = kwargs.pop('fclen', None)
        if fclen is not None:
            nml['NAMRIP']['CSTOP'] = fclen

        return nml

    def run(self, namelist, rundir, nproc=1, nproc_io=0, nthread=1, hyperthread=1, arch=None, **kwargs):
        """
        Set-up environment and configuration file and launch an IFS execution

        This calls :meth:`IFS.setup_env` and :meth:`IFS.setup_nml` before
        invoking the architecture's :any:`Arch.run` method.

        Parameters
        ----------
        namelist : :any:`f90nml.Namelist` or NoneType
            A namelist to use as a basis for the IFS run that will be further
            modified by :meth:`IFS.setup_nml`
        rundir : str or :any:`pathlib.Path`
            The run directory for IFS execution
        nproc : int, optional
            The total number of MPI ranks
        nproc_io : int, optional
            The number of MPI ranks for the IO server
        nthread : int, optional
            The number of OpenMP threads to use per MPI rank
        hyperthread : int, optional
            The number of hyperthreads to use per physical core
        arch : :any:`Arch`, optional
            The architecture definition to use
        **kwargs :
            Further named parameters. See also :meth:`IFS.setup_env` and
            :meth:`IFS.setup_nml` for specific parameters used there.
        """

        # Setup the run environment
        env = self.setup_env(namelist=namelist, rundir=rundir, nproc=nproc, nproc_io=nproc_io,
                             nthread=nthread, hyperthread=hyperthread, **kwargs)

        # Setup the IFS namelist
        nml = self.setup_nml(namelist=namelist, rundir=rundir, nproc=nproc, nproc_io=nproc_io,
                             nthread=nthread, hyperthread=hyperthread, **kwargs)

        # Select architecture preset from registry
        arch = arch_registry[arch]

        # Write the input namelist
        nml.write('fort.4', force=True)

        cmd = ['%s' % self.executable]
        arch.run(cmd=cmd, nproc=nproc, nthread=nthread, hyperthread=hyperthread, env=env, **kwargs)


class IFS_CY47R1(IFS):

    def __init__(self, *args, **kwargs):
        self.cycle = 'cy47r1'
        super().__init__(*args, **kwargs)

    @property
    def exec_name(self):
        return 'ifsMASTER.DP'

    def setup_env(self, **kwargs):
        """
        CY47R1-specific environment setup.

        This calls :meth:`IFS.setup_env` and additionally:

        * Insert ``builddir/ifs-source`` into ``LD_LIBRARY_PATH`` so
          ``libblack.so`` is picked up.
        """
        env = super().setup_env(**kwargs)

        # TODO: Suspended for Cray runs... :( Needs proper fix!
        arch = kwargs.get('arch')
        if arch is not None and not arch.startswith('xc40'):
            if 'LD_LIBRARY_PATH' not in env:
                env['LD_LIBRARY_PATH'] = getenv('LD_LIBRARY_PATH', '')
            env['LD_LIBRARY_PATH'] = str(self.builddir/'ifs-source') + ':' + env['LD_LIBRARY_PATH']

        return env


class IFS_CY47R2(IFS):

    def __init__(self, *args, prec='dp', **kwargs):
        self.cycle = 'cy47r2'
        super().__init__(*args, **kwargs)

        prec = prec.lower()
        if prec in ('double', 'dp'):
            self.prec = 'dp'
        elif prec in ('single', 'sp'):
            self.prec = 'sp'
        else:
            raise ValueError('Invalid precision: {}'.format(prec))

    @property
    def exec_name(self):
        return 'ifsMASTER.{}'.format(self.prec.upper())

    def setup_env(self, **kwargs):
        """
        CY47R2-specific environment setup.

        This calls :meth:`IFS.setup_env` and additionally:

        * Insert ``builddir/ifs_sp`` or ``builddir/ifs_dp`` into
          ``LD_LIBRARY_PATH`` so ``libblack.so`` is picked up.
        """
        env = super().setup_env(**kwargs)

        # TODO: Suspended for Cray runs... :( Needs proper fix!
        arch = kwargs.get('arch')
        if arch is not None and not arch.startswith('xc40'):
            if 'LD_LIBRARY_PATH' not in env:
                env['LD_LIBRARY_PATH'] = getenv('LD_LIBRARY_PATH', '')
            env['LD_LIBRARY_PATH'] = str(self.builddir/('ifs-' + self.prec)) + ':' + env['LD_LIBRARY_PATH']

        return env


cycle_registry = {
    'default': IFS_CY47R2,

    'cy47r1': IFS_CY47R1,
    'cy47r2': IFS_CY47R2,
}
"""Registry of available IFS cycles and the corresponding classes"""


# Export all cycle_registry classes
__all__ += [cls.__name__ for cls in set(cycle_registry.values())]
