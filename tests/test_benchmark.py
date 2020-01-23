from ifsbench import FCBenchmark
from pathlib import Path


class T21FC(FCBenchmark):
    """
    Example configuration of a T21 forceast benchmark.
    """

    input_files = [
        Path('...')
    ]
    

def test_simple_setup(self, here):
    """
    Test input file verification for a simple benchmark setup.
    """
    benchmark = T21FC.from_files()
    benchmark.check_input()


if __name__ == "__main__":
    """
    Really just for demo purposes....
    """

    # Example of how to create and run one of the above...
    ifs = IFSExecutable(build_dir=, install_dir='...')

    # benchmark = T21FC.from_tarball('path_to_tarball', run_dir='./')

    namelist = IFSNamelist('path_to_default_namelist')
    benchmark = T21FC.from_files('path_to_glob_for_input', namelist=namelist)

    benchmark.check_input()  # <= check that all required input data is found
    benchmark.run(ifs=ifs, env=env.XC40)
