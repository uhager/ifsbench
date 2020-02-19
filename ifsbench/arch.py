from abc import ABC, abstractmethod

from .util import execute


__all__ = ['Arch', 'Workstation', 'CrayXC40']


class Arch(ABC):
    """
    Machine and compiler architecture on which to run the IFS,
    comprising of compiler and environment assumptions about
    MPI-parallel runs.

    For example `arch.CRAY_XC40`
    """

    @classmethod
    @abstractmethod
    def run(cls, cmd, **kwargs):
        """
        Arch-specific general purpose executable execution.
        """
        pass


class Workstation(Arch):
    """
    Default setup for ECMWF workstations.
    """

    @classmethod
    def run(cls, cmd, nproc=1, nthread=1, hyperthread=1, logfile=None, env=None, **kwargs):
        env['OMP_NUM_THREADS'] = nthread
        # TODO: Ensure proper pinning

        if nproc > 1:
            cmd = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            cmd = 'mpirun -np {nproc} {cmd}'.format(nproc=nproc, cmd=cmd)
        execute(cmd, logfile=logfile, env=env, **kwargs)


class CrayXC40(Arch):
    """
    Default setup for ECMWF's Cray XC40 system.
    """

    @classmethod
    def run(cls, cmd, nproc=1, nproc_node=None, nthread=1, hyperthread=1,
            logfile=None, env=None, **kwargs):

        if nproc_node is None:
            nproc_node = max(nproc, 24)

        env['OMP_NUM_THREADS'] = nthread
        # TODO: Ensure proper pinning

        launcher = 'aprun -n %{nproc} -N %{nproc_node} -d %{nthread} -j %{hyperthread}'.format(
            nproc=nproc, nproc_node=nproc_node, nthread=nthread, hyperthread=hyperthread
        )
        cmd = [launcher, cmd]

        execute(cmd, logfile=logfile, env=env, **kwargs)
