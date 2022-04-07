"""
Hardware and job resource description classes
"""
from abc import ABC
from enum import Enum, auto
from .logging import error
from .util import classproperty


__all__ = ['CpuConfiguration', 'Binding', 'Job']


class CpuConfiguration(ABC):
    """
    Abstract base class to describe the hardware configuration of compute nodes

    :any:`Arch` should provide an implementation of this class to describe the
    CPU configuration of the available nodes.

    Attributes
    ----------
    sockets_per_node : int
        The number of sockets (sometimes this is also used to describe NUMA domains)
        available on each node. This must be specified in a derived class.
    cores_per_socket : int
        The number of physical cores per socket. This must be specified in a derived class.
    threads_per_core : int
        The number of logical cores per physical core (i.e. the number of SMT threads
        each core can execute). Typically, this is 1 (no hyperthreading), 2 or 4.
        This must be specified in a derived class.
    cores_per_node : int
        The number of physical cores per node. This value is automatically derived
        from the above properties.
    threads_per_node : int
        The number of logical cores per node (threads). This value is automatically derived
        from the above properties.
    """

    sockets_per_node: int

    cores_per_socket: int

    threads_per_core: int

    @classproperty
    def cores_per_node(self):
        """
        The number of physical cores per node
        """
        return self.sockets_per_node * self.cores_per_socket

    @classproperty
    def threads_per_node(self):
        """
        The number of logical cores (threads) per node
        """
        return self.cores_per_node * self.threads_per_core


class Binding(Enum):
    """
    Description of CPU binding strategy to use, for which the launch
    command should provide the appropriate options
    """
    BIND_NONE = auto()
    """Disable all binding specification"""

    BIND_SOCKETS = auto()
    """Bind tasks to sockets"""

    BIND_CORES = auto()
    """Bind tasks to cores"""

    BIND_THREADS = auto()
    """Bind tasks to hardware threads"""

    BIND_USER = auto()
    """Indicate that a different user-specified strategy should be used"""


class Job:
    """
    Description of a parallel job's resource requirements

    Provided with a CPU configuration (:data:`cpu_config`) and at least one of

    * the total number of MPI tasks (:data:`tasks`)
    * the number of nodes (:data:`nodes`) and the number of tasks per node
      (:data:`tasks_per_node`)
    * the number of nodes (:data:`nodes`) and the number of tasks per socket
      (:data:`tasks_per_socket`)

    Optionally, multi-threading can be specified by providing a value larger than 1
    (the default) for :data:`cpus_per_task`. Symmetric multi-threading (hyperthreading)
    can be enabled with :data:`use_smt`.

    Parameters
    ----------
    cpu_config : :any:`CpuConfiguration`
        The description of the available CPUs in the target system
    tasks : int, optional
        The total number of MPI tasks to be used.
        Default: :attr:`nodes` * :attr:`tasks_per_node`
    nodes : int, optional
        The total number of nodes to be used.
        Default: ceil(:attr:`threads` / available_threads_per-node) with the number of
        available threads dependent on the use of SMT.
    tasks_per_node : int, optional
        Launch a specific number of tasks per node. Can be derived from :attr:`tasks_per_socket`
        if that is specified
    tasks_per_socket : int, optional
        Launch a specific number of tasks per socket
    cpus_per_task : int, optional
        The number of computing elements (threads) available to each task. Default: 1
    smt : int, optional
        Enable symmetric multi-threading (hyperthreading). Default: 1
    bind : :any:`Binding`, optional
        Specify the binding strategy to use for pinning. Default: :any:`Binding.BIND_NONE`
    """

    def __init__(self, cpu_config, tasks=None, nodes=None, tasks_per_node=None,
                 tasks_per_socket=None, cpus_per_task=None, smt=None, bind=None):

        self.cpu_config = cpu_config
        self._tasks = tasks
        self._nodes = nodes
        self._tasks_per_node = tasks_per_node
        self._tasks_per_socket = tasks_per_socket
        self._cpus_per_task = cpus_per_task or 1
        self._smt = smt or 1
        self._bind = Binding.BIND_NONE if bind is None else bind

        try:
            tasks = self.tasks
            nodes = self.nodes
            threads = self.threads
        except AttributeError as excinfo:
            error(('Need to specify at least one of:\n'
                   'number of tasks or (tasks_per_node and nodes) or (tasks_per_socket and nodes)'))
            raise excinfo

        if nodes < 1:
            error(f'Invalid number of nodes: {nodes}')
            raise ValueError
        if tasks < 1:
            error(f'Invalid number of tasks: {nodes}')
            raise ValueError
        if threads < tasks:
            error(f'Invalid number of threads: {threads}')
            raise ValueError

    @property
    def tasks(self):
        """
        The total number of MPI tasks
        """
        if self._tasks is not None:
            return self._tasks
        return self.nodes * self.tasks_per_node

    @property
    def nodes(self):
        """
        The total number of nodes
        """
        if self._nodes is not None:
            return self._nodes
        threads_per_node = self.cpu_config.cores_per_node * self.smt
        return (self.threads + threads_per_node - 1) // threads_per_node

    @property
    def tasks_per_node(self):
        """
        The number of tasks on each node
        """
        if self._tasks_per_node is None:
            return self.tasks_per_socket * self.cpu_config.sockets_per_node
        return self._tasks_per_node

    @property
    def tasks_per_socket(self):
        """
        The number of tasks on each socket
        """
        if self._tasks_per_socket is None:
            raise AttributeError
        return self._tasks_per_socket

    @property
    def cpus_per_task(self):
        """
        The number of processing units per task
        """
        return self._cpus_per_task

    @property
    def smt(self):
        """
        Symmetric multi-threading, i.e. logical tasks per physical core
        """
        return self._smt

    @property
    def bind(self):
        """
        The binding strategy to use
        """
        return self._bind

    @property
    def threads(self):
        """
        The total number of threads across all tasks
        """
        return self.tasks * self.cpus_per_task
