"""
Some sanity tests for :any:`Arch` implementations
"""

import pytest
from conftest import Watcher
from ifsbench import logger, arch_registry, GPUSetup


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

@pytest.mark.parametrize('arch,np,nt,hyperthread,gpu_setup,expected', [
    ('atos_ac', 64, 4, 1, GPUSetup.GPU_NONE, [
        'srun', '--ntasks=64', '--ntasks-per-node=32',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
    ('atos_ac', 64, 4, 1, GPUSetup.GPU_ONE_TO_ONE, [
        'srun', '--ntasks=64', '--ntasks-per-node=4',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
    ('lumi_g', 256, 4, 1, GPUSetup.GPU_NONE, [
        'srun', '--ntasks=256', '--ntasks-per-node=14',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
    ('lumi_g', 256, 4, 1, GPUSetup.GPU_ONE_TO_ONE, [
        'srun', '--ntasks=256', '--ntasks-per-node=8',
        '--cpus-per-task=4', '--ntasks-per-core=1'
    ]),
])
def test_arch_gpu_run(watcher, arch, np, nt, gpu_setup, hyperthread, expected):
    """
    Verify the launch command for certain architecture configurations
    looks as expected
    """
    obj = arch_registry[arch]

    with watcher:
        obj.run('cmd', np, nt, hyperthread, gpu_setup=gpu_setup, dryrun=True)

    for string in expected:
        assert string in watcher.output



