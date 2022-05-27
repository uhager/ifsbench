"""
Test various implementations of :any:`Launcher`
"""

import pytest

from ifsbench import (
    CpuConfiguration, CpuBinding, CpuDistribution, Job,
    SrunLauncher, AprunLauncher, MpirunLauncher
)


@pytest.fixture(scope='module', name='cpu_config')
def fixture_cpu_config():
    """
    A typical :any:`CpuConfiguration`
    """
    class MyCpuConfig(CpuConfiguration):
        """Intentionally awkward values"""
        sockets_per_node = 3
        cores_per_socket = 37
        threads_per_core = 3

    return MyCpuConfig


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--cpu-bind=none'}),
    (AprunLauncher, {'aprun', '-n 185', '-cc none'}),
    (MpirunLauncher, {'mpirun', '-np 185', '--bind-to none'})
])
def test_mpi_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification"""
    job = Job(cpu_config, tasks=185, bind=CpuBinding.BIND_NONE)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--cpus-per-task=4', '--cpu-bind=none'}),
    (AprunLauncher, {'aprun', '-n 185', '-d 4', '-cc none'}),
    (MpirunLauncher, {'mpirun', '-np 185', '-cpus-per-proc 4', '--bind-to none'})
])
def test_hybrid_mpi_job(cpu_config, launcher, cmd):
    """A hybrid MPI + OpenMP :any:`Job` specification"""
    job = Job(cpu_config, tasks=185, cpus_per_task=4, bind=CpuBinding.BIND_NONE)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--ntasks-per-core=2', '--cpu-bind=threads'}),
    (AprunLauncher, {'aprun', '-n 185', '-j 2', '-cc depth'}),
    (MpirunLauncher, {'mpirun', '-np 185', '--bind-to hwthread'})
])
def test_mpi_smt_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with hyperthreading"""
    job = Job(cpu_config, tasks=185, threads_per_core=2, bind=CpuBinding.BIND_THREADS)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--nodes=7', '--ntasks-per-node=3', '--cpu-bind=sockets'}),
    (AprunLauncher, {'aprun', '-n 21', '-N 3', '-cc numa_node'}),
    (MpirunLauncher, {'mpirun', '-np 21', '-npernode 3', '--bind-to socket'})
])
def test_mpi_per_node_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with resources specified per node"""
    job = Job(cpu_config, nodes=7, tasks_per_node=3, bind=CpuBinding.BIND_SOCKETS)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--nodes=7', '--ntasks-per-socket=30', '--cpu-bind=cores'}),
    (AprunLauncher, {'aprun', '-n 630', '-S 30', '-cc cpu'}),
    (MpirunLauncher, {'mpirun', '-np 630', '-npersocket 30', '--bind-to core'})
])
def test_mpi_per_socket_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with resources specified per socket"""
    job = Job(cpu_config, nodes=7, tasks_per_socket=30, bind=CpuBinding.BIND_CORES)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--nodes=2', '--ntasks-per-socket=10', '--cpus-per-task=3'}),
    (AprunLauncher, {'aprun', '-n 60', '-S 10', '-d 3'}),
    (MpirunLauncher, {'mpirun', '-np 60', '-npersocket 10', '-cpus-per-proc 3'})
])
def test_hybrid_per_socket_job(cpu_config, launcher, cmd):
    """A hybrid :any:`Job` specification with resources specified per socket"""
    job = Job(cpu_config, nodes=2, tasks_per_socket=10, cpus_per_task=3)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--distribution=block:*'}),
    (AprunLauncher, {'aprun', '-n 185'}),
    (MpirunLauncher, {'mpirun', '-np 185'})
])
def test_mpi_distribute_remote_block_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with the distribution of ranks
    across nodes prescribed
    """
    job = Job(cpu_config, tasks=185, distribute_remote=CpuDistribution.DISTRIBUTE_BLOCK)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--distribution=*:cyclic'}),
    (AprunLauncher, {'aprun', '-n 185'}),
    (MpirunLauncher, {'mpirun', '-np 185', '--map-by numa'})
])
def test_mpi_distribute_local_cyclic_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with the distribution of ranks
    across sockets prescribed
    """
    job = Job(cpu_config, tasks=185, distribute_local=CpuDistribution.DISTRIBUTE_CYCLIC)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--distribution=block:block'}),
    (AprunLauncher, {'aprun', '-n 185'}),
    (MpirunLauncher, {'mpirun', '-np 185', '--map-by core'})
])
def test_mpi_distribute_block_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with the distribution of ranks
    fully prescribed
    """
    job = Job(cpu_config, tasks=185, distribute_remote=CpuDistribution.DISTRIBUTE_BLOCK,
              distribute_local=CpuDistribution.DISTRIBUTE_BLOCK)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--my-option'}),
    (AprunLauncher, {'aprun', '-n 185', '--my-option'}),
    (MpirunLauncher, {'mpirun', '-np 185', '--my-option'})
])
def test_mpi_custom_option(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with custom option handed through"""
    job = Job(cpu_config, tasks=185)
    assert set(launcher.get_launch_cmd(job, user_options='--my-option')) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--my-option', '--full-custom'}),
    (AprunLauncher, {'aprun', '-n 185', '--my-option', '--full-custom'}),
    (MpirunLauncher, {'mpirun', '-np 185', '--my-option', '--full-custom'})
])
def test_mpi_custom_options(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with custom options handed through"""
    job = Job(cpu_config, tasks=185)
    assert set(launcher.get_launch_cmd(job, user_options=['--my-option', '--full-custom'])) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, set()),
    (AprunLauncher, set()),
    (MpirunLauncher, set())
])
def test_mpi_non_parallel(cpu_config, launcher, cmd):
    """A non-parallel :any:`Job` specification"""
    job = Job(cpu_config, tasks=1)
    assert set(launcher.get_launch_cmd(job)) == cmd
