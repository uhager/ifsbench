"""
Some sanity tests for :any:`Arch` implementations
"""

import pytest
from conftest import Watcher
from ifsbench import logger, arch_registry


@pytest.fixture(name='watcher')
def fixture_watcher():
    """Return a :any:`Watcher` to check test output"""
    return Watcher(logger=logger, silent=True)


@pytest.mark.parametrize('arch,np,nt,hyperthread,expected', [
    ('atos_aa', 64, 4, 1, [
        'srun', '--ntasks=64', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
    ('atos_aa', 256, 4, 1, [
        'srun', '--ntasks=256', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
    ('atos_aa', 256, 16, 1, [
        'srun', '--ntasks=256', '--ntasks-per-node=8',
        '--cpus-per-task=16', '--ntasks-per-core=1'
    ]),
    ('atos_aa', 256, 16, 2, [
        'srun', '--ntasks=256', '--ntasks-per-node=16',
        '--cpus-per-task=16', '--ntasks-per-core=2'
    ]),
])
def test_arch_run(watcher, arch, np, nt, hyperthread, expected):
    """
    Verify the launch command for certain architecture configurations
    looks as expected
    """
    obj = arch_registry[arch]

    with watcher:
        obj.run('cmd', np, nt, hyperthread, dryrun=True)

    for string in expected:
        assert string in watcher.output

@pytest.mark.parametrize('arch,np,nt,hyperthread,gpus_per_task,expected', [
    ('atos_ac', 64, 4, 1, None, [
        'srun', '--ntasks=64', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--qos=np',
    ]),
    ('atos_ac', 64, 4, 1, 0, [
        'srun', '--ntasks=64', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--qos=np',
    ]),
    ('atos_ac', 64, 4, 1, 1, [
        'srun', '--ntasks=64', '--ntasks-per-node=4', '--qos=ng',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--gpus-per-task=1'
    ]),
    ('atos_ac', 64, 4, 1, 4, [
        'srun', '--ntasks=64', '--ntasks-per-node=1', '--qos=ng',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--gpus-per-task=4'
    ]),
    ('lumi_g', 256, 4, 1, None, [
        'srun', '--ntasks=256', '--ntasks-per-node=14', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
    ('lumi_g', 256, 4, 1, 0, [
        'srun', '--ntasks=256', '--ntasks-per-node=14', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
    ('lumi_g', 256, 4, 1, 1, [
        'srun', '--ntasks=256', '--ntasks-per-node=8', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--gpus-per-task=1'
    ]),
    ('lumi_g', 256, 4, 1, 4, [
        'srun', '--ntasks=256', '--ntasks-per-node=2', '--partition=standard-g',
        '--cpus-per-task=4', '--ntasks-per-core=1', '--gpus-per-task=4'
    ]),
])
def test_arch_gpu_run(watcher, arch, np, nt, gpus_per_task, hyperthread, expected):
    """
    Verify the launch command for certain architecture configurations
    looks as expected
    """
    obj = arch_registry[arch]

    with watcher:
        obj.run('cmd', np, nt, hyperthread, gpus_per_task=gpus_per_task, dryrun=True)

    for string in expected:
        assert string in watcher.output

