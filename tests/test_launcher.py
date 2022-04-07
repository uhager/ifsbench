"""
Test various implementations of :any:`Launcher`
"""

import pytest

from ifsbench import (
    CpuConfiguration, Binding, Job,
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
    job = Job(cpu_config, tasks=185, bind=Binding.BIND_NONE)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--ntasks=185', '--ntasks-per-core=2', '--cpu-bind=threads'}),
    (AprunLauncher, {'aprun', '-n 185', '-j 2', '-cc depth'}),
    (MpirunLauncher, {'mpirun', '-np 185', '--map-by core:PE=2', '--bind-to thread'})
])
def test_mpi_smt_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with hyperthreading"""
    job = Job(cpu_config, tasks=185, threads_per_core=2, bind=Binding.BIND_THREADS)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--nodes=7', '--ntasks-per-node=3', '--cpu-bind=sockets'}),
    (AprunLauncher, {'aprun', '-n 21', '-N 3', '-cc numa_node'}),
    (MpirunLauncher, {'mpirun', '-np 21', '-npernode 3', '--bind-to socket'})
])
def test_mpi_per_node_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with resources specified per node"""
    job = Job(cpu_config, nodes=7, tasks_per_node=3, bind=Binding.BIND_SOCKETS)
    assert set(launcher.get_launch_cmd(job)) == cmd


@pytest.mark.parametrize('launcher,cmd', [
    (SrunLauncher, {'srun', '--nodes=7', '--ntasks-per-socket=30', '--cpu-bind=cores'}),
    (AprunLauncher, {'aprun', '-n 630', '-S 30', '-cc depth'}),
    (MpirunLauncher, {'mpirun', '-np 630', '-npersocket 30', '--bind-to core'})
])
def test_mpi_per_socket_job(cpu_config, launcher, cmd):
    """An MPI-only :any:`Job` specification with resources specified per socket"""
    job = Job(cpu_config, nodes=7, tasks_per_socket=30, bind=Binding.BIND_CORES)
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
