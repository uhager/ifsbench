"""
Architecture specifications
"""
from abc import ABC, abstractmethod
import os

from .job import CpuConfiguration, CpuBinding, Job
from .launcher import Launcher, MpirunLauncher, SrunLauncher, AprunLauncher
from .util import as_tuple, execute


__all__ = ['Arch', 'Workstation', 'XC40Cray', 'XC40Intel', 'AtosAaIntel', 'arch_registry']


class Arch(ABC):
    """
    Machine and compiler architecture on which to run the IFS

    This provides compiler and environment assumptions for MPI-parallel runs.

    An implementation of this class must be provided for each target system.
    It must declare the CPU configuration in :attr:`cpu_config` and the
    launcher in :attr:`launcher` that is used for MPI-parallel execution.

    For multiple toolchains/runtime environments on a single physical system
    it can be beneficial to create an intermediate class describing common
    properties (such as :attr:`cpu_config`) and derived classes to specify
    the bespoke configuration.
    """

    cpu_config: CpuConfiguration
    """The CPU configuration of the architecture

    This describes the available compute capability on each compute node
    from which the job resource requirements can be derived.
    """

    launcher: Launcher
    """The MPI launcher that is used on the architecture

    This is used to derive the relevant launch command to execute the application
    using the resource requirements specified in a run's :any:`Job` description.
    """

    @classmethod
    @abstractmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, **kwargs):
        """
        Arch-specific general purpose executable execution

        This method must be implemented by architecture-specific implementations,
        either to launch :data:`cmd` directly or to build a job specification
        :any:`Job` and launch this via :meth:`run_job`.

        Parameters
        ----------
        cmd : list or str
            The command of the MPI executable (without the launch command)
        tasks : int
            The total number of MPI tasks to use
        cpus_per_task : int
            The number of threads to start for each MPI task
        threads_per_core : int
            The number of hyperthreads to use on each core
        launch_cmd : list or str, optional
            User-provided launch command that is used instead of generating
            a launch command based on :data:`job` specifications
        launch_user_options : list or str, optional
            User-provided launch command options that are added to the
            generated launch command. Ignored if :data:`launch_cmd` is given.
        logfile : str or :any:`pathlib.Path`, optional
            An optional logfile to store the output
        env : dict, optional
            Custom environment to use
        kwargs :
            Other arguments that may be used in the architecture implementation
            or may be passed on to :any:`execute`
        """

    @classmethod
    def run_job(cls, cmd, job, launch_cmd=None, launch_user_options=None,
                logfile=None, env=None, **kwargs):
        """
        Arch-specific general purpose executable execution for :any:`Job` specification

        This method can be used by the architecture-specific implementations.

        It launches :data:`cmd` using the resource requirements specified in :data:`job`.

        The architecture-specific :attr:`launcher` is used to generate the
        required launch command for that. The user can override this behaviour
        by providing a custom launch command in :data:`launch_cmd`.

        Parameters
        ----------
        cmd : list or str
            The command of the MPI executable (without the launch command)
        job : :any:`Job`
            The resource requirements of the job to be run
        launch_cmd : list or str, optional
            User-provided launch command that is used instead of generating
            a launch command based on :data:`job` specifications
        launch_user_options : list or str, optional
            User-provided launch command options that are added to the
            generated launch command. Ignored if :data:`launch_cmd` is given.
        logfile : str or :any:`pathlib.Path`, optional
            An optional logfile to store the output
        env : dict, optional
            Custom environment to use
        kwargs :
            Other arguments that may be used in the architecture implementation
            or may be passed on to :any:`execute`
        """
        assert isinstance(job, Job)
        assert job.cpu_config == cls.cpu_config

        if env is None:
            env = os.environ.copy()

        if launch_cmd is None:
            launch_cmd = as_tuple(cls.launcher.get_launch_cmd(job, user_options=launch_user_options))
        else:
            launch_cmd = as_tuple(launch_cmd)
        full_cmd = ' '.join(launch_cmd + as_tuple(cmd))
        execute(full_cmd, logfile=logfile, env=env, **kwargs)


class Workstation(Arch):
    """
    Default setup for ECMWF workstations.
    """

    class WorkstationCpuConfig(CpuConfiguration):
        """Most workstations have a quad-core CPU with hyperthreading"""

        sockets_per_node = 1
        cores_per_socket = 4
        threads_per_core = 2

    cpu_config = WorkstationCpuConfig

    launcher = MpirunLauncher

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, **kwargs):
        """Build job description using :attr:`cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task
        # TODO: Ensure proper pinning

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, cpus_per_task=cpus_per_task,
                  threads_per_core=threads_per_core)

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


class XC40(Arch):
    """
    Hardware and launcher setup for ECMWF's Cray XC40 system

    Toolchain specific settings are provided in derived
    classes :class:`XC40Cray` and :class:`XC40Intel` for Cray compiler and
    Intel Compiler, respectively
    """

    class XC40CpuConfig(CpuConfiguration):
        """Dual-socket Intel Xeon E5-2650 v4 (12 cores/24 threads, 2.2 GHz)"""

        sockets_per_node = 2
        cores_per_socket = 12
        threads_per_core = 2

    cpu_config = XC40CpuConfig

    launcher = AprunLauncher


class XC40Cray(XC40):
    """
    Cray compiler-toolchain setup for :any:`XC40`
    """

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, **kwargs):
        """Build job description using :attr:`XC40.cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task

        # Fill nodes without hyperthreading
        tasks_per_node = kwargs.pop('tasks_per_node', min(tasks, cls.cpu_config.cores_per_node))
        tasks_per_socket = tasks_per_node // 2

        # Binding-strategy -cc cpu
        bind = CpuBinding.BIND_CORES

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, tasks_per_node=tasks_per_node,
                  tasks_per_socket=tasks_per_socket, cpus_per_task=cpus_per_task,
                  threads_per_core=threads_per_core, bind=bind)

        # Strict memory containment
        if launch_user_options is None:
            launch_user_options = []
        launch_user_options += ['-ss']

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


class XC40Intel(XC40):
    """
    Intel compiler-toolchain setup for :any:`XC40`
    """

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, **kwargs):
        """Build job description using :attr:`XC40.cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task
        env['OMP_PLACES'] = 'threads'
        env['OMP_PROC_BIND'] = 'close'

        # Fill nodes without hyperthreading
        tasks_per_node = kwargs.pop('tasks_per_node', min(tasks, cls.cpu_config.cores_per_node))
        tasks_per_socket = tasks_per_node // 2

        # Binding-strategy -cc depth
        bind = CpuBinding.BIND_THREADS

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, tasks_per_node=tasks_per_node,
                  tasks_per_socket=tasks_per_socket, cpus_per_task=cpus_per_task,
                  threads_per_core=threads_per_core, bind=bind)

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


class AtosAa(Arch):
    """
    Hardware setup for ECMWF's aa system in Bologna
    """

    class AtosAaCpuConfig(CpuConfiguration):
        """Dual-socket AMD EPYC 7H12 (64 core/128 thread, 2.6 GHz)"""

        sockets_per_node = 2
        cores_per_socket = 64
        threads_per_core = 2

    cpu_config = AtosAaCpuConfig

    launcher = SrunLauncher


class AtosAaIntel(AtosAa):
    """
    Intel compiler-toolchain setup for :any:`AtosAa`
    """

    @classmethod
    def run(cls, cmd, tasks, cpus_per_task, threads_per_core, launch_cmd=None,
            launch_user_options=None, logfile=None, env=None, **kwargs):
        """Build job description using :attr:`cpu_config`"""

        # Setup environment
        if env is None:
            env = os.environ.copy()
        env['OMP_NUM_THREADS'] = cpus_per_task
        # TODO: Ensure proper pinning

        # Fill nodes without hyperthreading
        tasks_per_node = kwargs.pop('tasks_per_node', min(tasks, cls.cpu_config.cores_per_node))

        # Bind to cores
        bind = CpuBinding.BIND_CORES

        # Build job description
        job = Job(cls.cpu_config, tasks=tasks, tasks_per_node=tasks_per_node,
                  cpus_per_task=cpus_per_task, threads_per_core=threads_per_core, bind=bind)

        # Launch via generic run
        cls.run_job(cmd, job, launch_cmd=launch_cmd, launch_user_options=launch_user_options,
                    logfile=logfile, env=env, **kwargs)


arch_registry = {
    None: AtosAaIntel,
    'workstation': Workstation,
    'xc40': XC40Cray,
    'xc40cray': XC40Cray,
    'xc40intel': XC40Intel,
    'atos_aa': AtosAaIntel,
}
"""String-lookup of :any:`Arch` implementations"""
