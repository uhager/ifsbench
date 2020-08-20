from abc import ABC, abstractmethod
from math import ceil

from .util import execute


__all__ = ['Arch', 'Workstation', 'TEMS', 'XC40Cray', 'XC40Cray', 'arch_registry']


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


class TEMS(Arch):
    """
    Default setup for ECMWF's TEMS system using SLURM
    """
 
    @classmethod
    def run(cls, cmd, nproc=1, nproc_node=None, nthread=1, hyperthread=1,
            logfile=None, env=None, launch=None, **kwargs):
 
        if nproc_node is None:
            nproc_node = min(nproc, 128)
 
        env['OMP_NUM_THREADS'] = nthread
 
        if hyperthread == 1:
            cpupertask = nthread*2
        else:
            cpupertask = nthread
        
        nnode = ceil(nproc*nthread/nproc_node)
 
        launcher = 'srun -p compute -q np -N {nnode} -n {nproc} --cpu-bind=cores '\
                '--cpus-per-task={cpupertask}'.format(nnode=nnode,nproc=nproc,cpupertask=cpupertask)
        cmd = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
        cmd = '{launcher} {cmd}'.format(launcher=launcher, cmd=cmd)
        #cmd = 'ldd ' + cmd
 
        execute(cmd, logfile=logfile, env=env, **kwargs)


class XC40Cray(Arch):
    """
    Default setup for ECMWF's Cray XC40 system with Cray compiler toolchain.
    """

    @classmethod
    def run(cls, cmd, nproc=1, nproc_node=None, nthread=1, hyperthread=1,
            logfile=None, env=None, launch=None, **kwargs):

        if nproc_node is None:
            nproc_node = min(nproc, 24)

        env['OMP_NUM_THREADS'] = nthread

        # From Paddy:
        # Cray: aprun -m8000h -cc cpu -n 72 -N 12 -S 6 -j 2 -d 6 -ss
        # TODO: Try again with `-m8000h` (for some reason get OOM-killed)

        launcher = 'aprun -cc cpu -n {nproc} -N {nproc_node} -S {nproc_numa} '\
        '-d {nthread} -j {hyperthread} -ss'.format(
            nproc=nproc, nproc_node=nproc_node, nproc_numa=int(nproc_node/2),
            nthread=nthread, hyperthread=hyperthread
        )
        cmd = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
        cmd = '{launcher} {cmd}'.format(launcher=launcher, cmd=cmd)

        execute(cmd, logfile=logfile, env=env, **kwargs)


class XC40Intel(Arch):
    """
    Default setup for ECMWF's Cray XC40 system with Intel toolchain
    """

    @classmethod
    def run(cls, cmd, nproc=1, nproc_node=None, nthread=1, hyperthread=1,
            logfile=None, env=None, launch=None, **kwargs):

        if nproc_node is None:
            nproc_node = min(nproc, 24)

        # Ensure correct pinning on Intel
        env['OMP_NUM_THREADS'] = nthread
        env['OMP_PLACES'] = 'threads'
        env['OMP_PROC_BIND'] = 'close'

        # env['LD_PRELOAD'] = '/opt/cray/cce/8.5.8/craylibs/x86-64/libtcmalloc_minimal.so'

        launcher = 'aprun -cc depth -n {nproc} -N {nproc_node} -S {nproc_numa} '\
        '-d {nthread} -j {hyperthread}'.format(
            nproc=nproc, nproc_node=nproc_node, nproc_numa=int(nproc_node/2),
            nthread=nthread, hyperthread=hyperthread
        )
        cmd = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
        cmd = '{launcher} {cmd}'.format(launcher=launcher, cmd=cmd)

        execute(cmd, logfile=logfile, env=env, **kwargs)


arch_registry = {
    None: Workstation,
    'workstation': Workstation,
    'tems': TEMS,
    'xc40': XC40Cray,
    'xc40cray': XC40Cray,
    'xc40intel': XC40Intel,
}
