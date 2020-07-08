import contextlib
import shutil
import timeit
from pathlib import Path
from os import environ, getcwd
from subprocess import run, STDOUT, CalledProcessError
from pprint import pformat

from ifsbench.logging import debug, info, warning, error


__all__ = ['execute', 'symlink_data', 'copy_data', 'Timer']


def execute(command, **kwargs):
    """
    Execute a single command with a given director or envrionment.

    :param command: String or list of strings with the command to execute
    :param cwd: Directory in which to execute command
    :param dryrun: Does not actually run command but log it
    """
    cwd = kwargs.pop('cwd', None)
    env = kwargs.pop('env', None)
    dryrun = kwargs.pop('dryrun', False)
    logfile = kwargs.pop('logfile', None)

    # Some string mangling to support lists and strings
    if isinstance(command, list):
        command = ' '.join(command)
    if isinstance(command, str):
        command = command.split(' ')

    debug('[ifsbench] User env:\n%s' % pformat(env, indent=2))
    if env is not None:
        # Inject user-defined environment
        run_env = environ.copy()
        run_env.update(env)
    else:
        run_env = None

    # Ensure all env variables are strings
    run_env = {k: str(v) for k, v in run_env.items()}

    stdout = kwargs.pop('stdout', None)
    stderr = kwargs.pop('stderr', STDOUT)

    # Log the command we're about to execute
    cwd = getcwd() if cwd is None else str(cwd)
    debug('[ifsbench] Run directory: ' + cwd)
    info('[ifsbench] Executing: ' + ' '.join(command))

    try:
        if not dryrun:
            if logfile is None:
                run(command, check=True, env=run_env,
                    stdout=stdout, stderr=stderr, **kwargs)
            else:
                with Path(logfile).open('w') as logfile:
                    run(command, check=True, cwd=cwd, env=run_env,
                        stdout=logfile, stderr=stderr, **kwargs)

    except CalledProcessError as e:
        error('Execution failed with return code: %s' % e.returncode)
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


def as_tuple(item, type=None, length=None):
    """
    Force item to a tuple.

    Partly extracted from: https://github.com/OP2/PyOP2/.
    """
    # Empty list if we get passed None
    if item is None:
        t = ()
    elif isinstance(item, str):
        t = (item,)
    else:
        # Convert iterable to list...
        try:
            t = tuple(item)
        # ... or create a list of a single item
        except (TypeError, NotImplementedError):
            t = (item,) * (length or 1)
    if length and not len(t) == length:
        raise ValueError("Tuple needs to be of length %d" % length)
    if type and not all(isinstance(i, type) for i in t):
        raise TypeError("Items need to be of type %s" % type)
    return t


def is_iterable(o):
    """
    Checks if an item is truly iterable using duck typing.

    This was added because :class:`pymbolic.primitives.Expression` provide an ``__iter__`` method
    that throws an exception to avoid being iterable. However, with that method defined it is
    identified as a :class:`collections.Iterable` and thus this is a much more reliable test.
    """
    try:
        iter(o)
    except TypeError:
        return False
    else:
        return True


def flatten(l):
    """
    Flatten a hierarchy of nested lists into a plain list.
    """
    newlist = []
    for el in l:
        if is_iterable(el) and not isinstance(el, (str, bytes)):
            for sub in flatten(el):
                newlist.append(sub)
        else:
            newlist.append(el)
    return newlist
