import contextlib
import shutil
import timeit
from os import environ, getcwd
from subprocess import run, STDOUT, CalledProcessError

from ifsbench.logging import debug, info, error


__all__ = ['execute', 'symlink_data', 'copy_data', 'Timer']


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


def symlink_data(source, dest, force=True):
    """
    Utility to symlink input data if it doesn't exist.

    :param source: Path of the original file to link to
    :param dest: Path of the new symlink
    :param force: Force delete and re-link for existing symlinks
    """
    if not source.exists():
        warning('Trying to link non-existent file: %s' % source)

    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)

    if dest.exists():
        if not dest.resolve() == source and force:
            # Delete and re-link of path points somewhere else
            dest.unlink()
            debug('Symlinking %s -> %s' % (source, dest))
            dest.symlink_to(source)
    else:
        debug('Symlinking %s -> %s' % (source, dest))
        dest.symlink_to(source)


def copy_data(source, dest, force=False):
    """
    Utility to copy input data if it doesn't exist.

    Note, if the target file exists, the "last modified" time will be
    used to decide if the file should be copoed iver again, unless the
    copy is explicitly forced.

    :param source: Path of the input file to copy
    :param dest: Path of the target to copy :param source: to
    :param force: Force delete and copy for existing symlinks
    """
    if not source.exists():
        raise RuntimeError('Trying to copy non-existent file: %s' % source)

    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)

    if dest.exists():
        if force or source.stat().st_mtime > dest.stat().st_mtime:
            # Delete and re-link if `dest` points somewhere else
            dest.unlink()
            debug('Copying %s -> %s' % (source, dest))
            shutil.copyfile(source, dest)
    else:
        debug('Copying %s -> %s' % (source, dest))
        shutil.copyfile(source, dest)


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
