
"""

from ifsbench.environment import CrayXC40

Benchmark().run(env=CrayXC40)
"""

class Environment(object):
    """
    Definition and configuration of the environment in which to run IFS.

    
    """

    def run(self, binary):
        pass


    def run_parallel(self, binary):
        pass
