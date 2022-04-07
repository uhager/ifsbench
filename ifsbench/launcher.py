from abc import ABC, abstractmethod

from .job import Binding
from .util import as_tuple


class Launcher(ABC):
    """
    Base class for MPI launch command implementations
    """

    job_options_map: dict
    """
    A mapping of :any:`Job` attributes to launch cmd options

    See :meth:`get_options_from_job` for how this is used to build
    launch command options.
    """

    bind_options_map: dict
    """
    A mapping of :any:`Binding` values to launch cmd options

    See :meth:`get_options_from_binding` for how this is used to build
    launch command options.
    """

    @classmethod
    def get_options_from_job(cls, job):
        """
        Build a list of launch command options from the provided :data:`job` specification

        This uses the :attr:`job_options_map` to compile all options according to what
        is specified in :data:`job`.
        The format of :attr:`job_options_map` should be a `dict` with the name of
        :any:`Job` attributes as keys and launch command-specific format strings as
        values, e.g., ``{'tasks': '--ntasks={}'}``.

        Only attributes from :attr:`job_options_map` that are defined (i.e. do not raise
        :any:`AttributeError`) are added to the list of options, thus this provides a
        direct mapping from the parameters provided to :any:`Job` to the launch command.

        Parameters
        ----------
        job : :any:`Job`
            The job description specifying required hardware resources

        Returns
        -------
        list
            A list of strings with the rendered job options
        """
        options = []
        for attr, option in cls.job_options_map.items():
            try:
                value = getattr(job, attr)
            except AttributeError:
                continue
            options += [option.format(value)]
        return options

    @classmethod
    def get_options_from_binding(cls, bind):
        """
        Build a list of launch command options from the provided :data:`bind` specification

        This uses the :attr:`bind_options_map` to map the specified binding strategy
        to the relevant launch command option. The format of :attr:`bind_options_map`
        should be a `dict` with the binding values declared in the enum :any:`Binding` as
        keys and (a list of) launch-command option strings as values, e.g.,
        ``{Binding.BIND_CORES: '--cpu-bind=cores'}``.

        Parameters
        ----------
        bind : :any:`Binding`

        Returns
        -------
        list
            A list of strings with the rendered job options
        """
        return list(as_tuple(cls.bind_options_map[bind]))

    @classmethod
    @abstractmethod
    def get_launch_cmd(cls, job):
        """
        Return the launch command for a provided :data:`job` specification

        This must be implemented by derived classes.

        Parameters
        ----------
        job : :any:`Job`
            The specification of hardware resources to use
        """


class SrunLauncher(Launcher):
    """
    :any:`Launcher` implementation for Slurm's srun
    """

    job_options_map = {
        'nodes': '--nodes={}',
        'tasks': '--ntasks={}',
        'tasks_per_node': '--ntasks-per-node={}',
        'tasks_per_socket': '--ntasks-per-socket={}',
        'cpus_per_task': '--cpus-per-task={}',
        'threads_per_core': '--ntasks-per-core={}'
    }

    bind_options_map = {
        Binding.BIND_NONE: ['--cpu-bind=none'],
        Binding.BIND_SOCKETS: ['--cpu-bind=sockets'],
        Binding.BIND_CORES: ['--cpu-bind=cores'],
        Binding.BIND_THREADS: ['--cpu-bind=threads'],
        Binding.BIND_USER: [],
    }

    @classmethod
    def get_launch_cmd(cls, job):
        """
        Return the srun command for the provided :data:`job` specification
        """
        cmd = ['srun']
        if hasattr(job, 'bind'):
            cmd += cls.get_options_from_binding(job.bind)
        cmd += cls.get_options_from_job(job)
        return cmd


class AprunLauncher(Launcher):
    """
    :any:`Launcher` implementation for Cray's aprun
    """

    job_options_map = {
        'tasks': '-n {}',
        'tasks_per_node': '-N {}',
        'tasks_per_socket': '-S {}',
        'cpus_per_task': '-d {}',
        'threads_per_core': '-j {}',
    }

    bind_options_map = {
        Binding.BIND_NONE: ['-cc none'],
        Binding.BIND_SOCKETS: ['-cc numa_node'],
        Binding.BIND_CORES: ['-cc depth'],
        Binding.BIND_THREADS: ['-cc depth'],
        Binding.BIND_USER: [],
    }

    @classmethod
    def get_launch_cmd(cls, job):
        """
        Return the aprun command for the provided :data:`job` specification
        """
        cmd = ['aprun']
        if hasattr(job, 'bind'):
            cmd += cls.get_options_from_binding(job.bind)
        cmd += cls.get_options_from_job(job)
        # Aprun has no option to specify relative to nodes, thus we have to
        # derive the number of tasks if they have not been specified explicitly
        if not hasattr(job, 'tasks'):
            cmd += [f'-n {job.get_tasks()}']
        return cmd


class MpirunLauncher(Launcher):
    """
    :any:`Launcher` implementation for a standard mpirun
    """

    job_options_map = {
        'tasks': '-np {}',
        'tasks_per_node': '-npernode {}',
        'tasks_per_socket': '-npersocket {}',
        'cpus_per_task': '-cpus-per-proc {}',
        'threads_per_core': '--map-by core:PE={}'
    }

    bind_options_map = {
        Binding.BIND_NONE: ['--bind-to none'],
        Binding.BIND_SOCKETS: ['--bind-to socket'],
        Binding.BIND_CORES: ['--bind-to core'],
        Binding.BIND_THREADS: ['--bind-to thread'],
        Binding.BIND_USER: [],
    }

    @classmethod
    def get_launch_cmd(cls, job):
        """
        Return the mpirun command for the provided :data:`job` specification
        """
        cmd = ['mpirun']
        if hasattr(job, 'bind'):
            cmd += cls.get_options_from_binding(job.bind)
        cmd += cls.get_options_from_job(job)
        # Mpirun has no option to specify relative to nodes, thus we have to
        # derive the number of tasks if they have not been specified explicitly
        if not hasattr(job, 'tasks'):
            cmd += [f'-np {job.get_tasks()}']
        return cmd
