"""
Test :any:`Job` and its ability to derive job size
"""

import pytest

from ifsbench import Job, CpuConfiguration, Binding


@pytest.mark.parametrize('cpu_config,jobargs,jobattrs', [
    # Only specify number of tasks:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 64},
     {'tasks': 64, 'nodes': 4, 'tasks_per_node': None, 'tasks_per_socket': None,
      'cpus_per_task': 1, 'threads': 64, 'smt': 1, 'bind': Binding.BIND_NONE}),
    # Specify nodes and number of tasks per node:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_node': 16},
     {'tasks': 64, 'nodes': 4, 'tasks_per_node': 16, 'tasks_per_socket': None,
      'cpus_per_task': 1, 'threads': 64, 'smt': 1, 'bind': Binding.BIND_NONE}),
    # Specify nodes and number of tasks per socket:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_socket': 8},
     {'tasks': 64, 'nodes': 4, 'tasks_per_node': 16, 'tasks_per_socket': 8,
      'cpus_per_task': 1, 'threads': 64, 'smt': 1, 'bind': Binding.BIND_NONE}),
    # Specify nodes and number of tasks per socket with hyperthreading:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_socket': 16, 'smt': 2},
     {'tasks': 128, 'nodes': 4, 'tasks_per_node': 32, 'tasks_per_socket': 16,
      'cpus_per_task': 1, 'threads': 128, 'smt': 2, 'bind': Binding.BIND_NONE}),
    # Undersubscribe nodes:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'nodes': 4, 'tasks_per_socket': 2},
     {'tasks': 16, 'nodes': 4, 'tasks_per_node': 4, 'tasks_per_socket': 2,
      'cpus_per_task': 1, 'threads': 16, 'smt': 1, 'bind': Binding.BIND_NONE}),
    # Less tasks than available:
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 60, 'nodes': 4},
     {'tasks': 60, 'nodes': 4, 'tasks_per_node': None, 'tasks_per_socket': None,
      'cpus_per_task': 1, 'threads': 60, 'smt': 1, 'bind': Binding.BIND_NONE}),
    # Specify number of tasks that is less than total available in required nodes
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 60},
     {'tasks': 60, 'nodes': 4, 'tasks_per_node': None, 'tasks_per_socket': None,
      'cpus_per_task': 1, 'threads': 60, 'smt': 1, 'bind': Binding.BIND_NONE}),
    # Hybrid MPI+OpenMP
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 16, 'cpus_per_task': 4},
     {'tasks': 16, 'nodes': 4, 'tasks_per_node': None, 'tasks_per_socket': None,
      'cpus_per_task': 4, 'threads': 64, 'smt': 1, 'bind': Binding.BIND_NONE}),
    # Hybrid MPI+OpenMP+SMT
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 16, 'cpus_per_task': 8, 'smt': 2},
     {'tasks': 16, 'nodes': 4, 'tasks_per_node': None, 'tasks_per_socket': None,
      'cpus_per_task': 8, 'threads': 128, 'smt': 2, 'bind': Binding.BIND_NONE}),
    # Hybrid MPI+OpenMP+SMT undersubscribed
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 14, 'cpus_per_task': 8, 'smt': 2},
     {'tasks': 14, 'nodes': 4, 'tasks_per_node': None, 'tasks_per_socket': None,
      'cpus_per_task': 8, 'threads': 112, 'smt': 2, 'bind': Binding.BIND_NONE}),
    # Hybrid MPI+OpenMP+SMT with binding
    ({'sockets_per_node': 2, 'cores_per_socket': 8, 'threads_per_core': 2},
     {'tasks': 16, 'cpus_per_task': 8, 'smt': 2, 'bind': Binding.BIND_CORES},
     {'tasks': 16, 'nodes': 4, 'tasks_per_node': None, 'tasks_per_socket': None,
      'cpus_per_task': 8, 'threads': 128, 'smt': 2, 'bind': Binding.BIND_CORES}),
])
def test_job(cpu_config, jobargs, jobattrs):
    """
    Test various configuration specifications and fill-in for derived values
    """

    class MyCpuConfig(CpuConfiguration):
        """Dummy cpu configuration"""
        sockets_per_node = cpu_config['sockets_per_node']
        cores_per_socket = cpu_config['cores_per_socket']
        threads_per_core = cpu_config['threads_per_core']

    job = Job(MyCpuConfig, **jobargs)

    for attr, value in jobattrs.items():
        if value is None:
            with pytest.raises(AttributeError):
                _ = getattr(job, attr)
        else:
            assert getattr(job, attr) == value
