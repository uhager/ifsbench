from abc import ABC, abstractmethod


class Benchmark(ABC):
    """
    Definition of a general benchmark setup.
    """

    def __init__(self, **kwargs):
        self.expid = kwargs.get('expid')
        self.rundir = kwargs.get('rundir', None)

    @property
    @classmethod
    @abstractmethod
    def input_files(self):
        """
        List of relative paths (strings or ``Path`` objects) that
        define all necessary input data files to run this benchmark.
        """
        pass


    @classmethod
    def from_path(cls, rundir=None, symlink=True):
        """
        Create instance of ``Benchmark`` object by globbing a set of
        input paths for the ncessary input data.
        """
        pass


    @classmethod
    def from_experiment(cls):
        """
        Create instance of ``Benchmark`` object from an experiment.

        Note, this requires the experiment to be suspended just before
        the template run is about to be executed, so that we can
        inspect the experiment run directory.
        """
        pass


    @classmethod
    def from_tarball(cls):
        """
        Create instance of ``Benchmark`` object from given tarball
        """
        pass


    def to_tarball(self, filepath):
        """
        Dump input files and configuration to a tarball for off-line
        benchmarking.
        """
        pass

    def check_input(self):
        """
        Check input file list matches benchmarjmk configuration. 
        """
    

class FCBenchmark(Benchmark):
    """
    Definition of a high-res forcecast benchmark.
    """

    pass




class T21FC(FCBenchmark):
    """
    Example configuration of a T21 forceast benchmark.
    """


if __name__ == "__main__":

    # Example of how to create and run one of the above...
    ifs = IFSExecutable(build_dir='...', install_dir='...')

    # benchmark = T21FC.from_tarball('path_to_tarball', run_dir='./')

    namelist = IFSNamelist('path_to_default_namelist')
    benchmark = T21FC.from_files('path_to_glob_for_input', namelist=namelist)

    benchmark.check_input()  # <= check that all required input data is found
    benchmark.run(ifs=ifs, env=env.XC40)
