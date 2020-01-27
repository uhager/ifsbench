

__all__ = ['WS']


class Environment(object):
    """
    Definition and configuration of the environment in which to run IFS.
    """

    def run(self, binary):
        pass

    def run_parallel(self, binary):
        pass


class Workstation(Environment):

    pass


WS = Workstation()
