from abc import ABC, abstractmethod

from .util import execute


__all__ = ['Arch', 'Workstation', 'CrayXC40', 'arch_registry']


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
    def run(cls, cmd, nproc=1, nthread=1, hyperthread=1, logfile=None,
            env=None, launch=None, **kwargs):
        env['OMP_NUM_THREADS'] = nthread
        # TODO: Ensure proper pinning

        if launch is None:
            if nproc > 1:
                launch = 'mpirun -np {nproc}'.format(nproc=nproc)

        cmd = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
        cmd = '{launch}{cmd}'.format(cmd=cmd, launch='' if launch is None else ('%s ' % launch), )
        execute(cmd, logfile=logfile, env=env, **kwargs)


class CrayXC40(Arch):
    """
    Default setup for ECMWF's Cray XC40 system.
    """

    @classmethod
    def run(cls, cmd, nproc=1, nproc_node=None, nthread=1, hyperthread=1,
            logfile=None, env=None, launch=None, **kwargs):

        if nproc_node is None:
            nproc_node = min(nproc, 24)

        env['OMP_NUM_THREADS'] = nthread
        # TODO: Ensure proper pinning

        launcher = 'aprun -n {nproc} -N {nproc_node} -d {nthread} -j {hyperthread}'.format(
            nproc=nproc, nproc_node=nproc_node, nthread=nthread, hyperthread=hyperthread
        )
        cmd = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
        cmd = '{launcher} {cmd}'.format(launcher=launcher, cmd=cmd)

        execute(cmd, logfile=logfile, env=env, **kwargs)


arch_registry = {
    None: Workstation,
    'xc40': CrayXC40,
    'cray': CrayXC40,
}
