import contextlib
import timeit
from os import environ, getcwd
from subprocess import run, STDOUT, CalledProcessError

from ifsbench.logging import debug, info, error


__all__ = ['execute', 'Timer']


def execute(args, cwd=None, env=None, **kwargs):
    """
    Execute a single command with a given director or envrionment.
    """
    # Normalize args to a list of strings
    if isinstance(args, str):
        args = args.split(' ')
    args = [str(arg) for arg in args]

    debug('User env: %s' % env)
    if env is not None:
        # Inject user-defined environment
        run_env = environ.copy()
        run_env.update(env)
    else:
        run_env = None

    # Ensure all env variables are strings
    run_env = {k: str(v) for k, v in run_env.items()}

    debug('Run directory: %s' % cwd)
    info('Executing: %s' % ' '.join(args))
    cwd = getcwd() if cwd is None else str(cwd)
    stdout = kwargs.pop('stdout', None)
    stderr = kwargs.pop('stderr', STDOUT)
    try:
        run(args, check=True, cwd=cwd, env=run_env, stdout=stdout, stderr=stderr, **kwargs)
    except CalledProcessError as e:
        error('Execution failed with return code: %s', e.returncode)
        raise e


@contextlib.contextmanager
def Timer(name=None):
    """
    Utility to do inline timing of code blocks
    """
    start_time = timeit.default_timer()
    yield
    end_time = timeit.default_timer()
    time = end_time - start_time
    print('Timer::%s: %.3f s' % (name, time))
