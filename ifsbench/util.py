# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Collection of utility routines
"""
from os import environ, getcwd
from pathlib import Path
from pprint import pformat
from subprocess import Popen, STDOUT, PIPE, CalledProcessError
import sys

from ifsbench.logging import debug, info, error


__all__ = ['execute', 'auto_post_mortem_debugger']


def execute(command, **kwargs):
    """
    Execute a single command with a given directory or environment.

    Parameters
    ----------
    command : list of str
        The (components of the) command to execute.
    cwd : str, optional
        Directory in which to execute command.
    dryrun : bool, optional
        Do not actually run the command but log it (default: `False`).
    logfile : str, optional
        Write stdout to this file (default: `None`).
    stdout : optional
        Overwrite `stdout` attribute of :any:`subprocess.run`. Ignored if
        :attr:`logfile` is given (default: `None`).
    stderr : optional
        Overwrite `stderr` attribute of :any:`subprocess.run` (default: `None`).
    """
    cwd = kwargs.pop('cwd', None)
    env = kwargs.pop('env', None)
    dryrun = kwargs.pop('dryrun', False)
    logfile = kwargs.pop('logfile', None)


    debug(f'[ifsbench] User env:\n{pformat(env, indent=2)}')
    if env is not None:
        # Inject user-defined environment
        run_env = environ.copy()
        run_env.update(env)

        # Ensure all env variables are strings
        run_env = {k: str(v) for k, v in run_env.items()}
    else:
        run_env = None

    stdout = kwargs.pop('stdout', None)
    stderr = kwargs.pop('stderr', STDOUT)

    # Log the command we're about to execute
    cwd = getcwd() if cwd is None else str(cwd)
    debug('[ifsbench] Run directory: ' + cwd)
    info('[ifsbench] Executing: ' + ' '.join(command))

    if dryrun:
        # Only print the environment when in dryrun mode.
        info('[ifsbench] Environment: ' + str(run_env))
        return

    cmd_args = {
        'cwd': cwd, 'env': run_env, 'text': True, 'stderr': stderr
    }

    if logfile:
        # If we're file-logging, intercept via pipe
        _log_file = Path(logfile).open('w', encoding='utf-8') # pylint: disable=consider-using-with
        cmd_args['stdout'] = PIPE
    else:
        _log_file = None
        cmd_args['stdout'] = stdout


    def _read_and_multiplex(p):
        """
        Read from ``p.stdout.read()`` and write to log and sys.stdout.
        """
        line = p.stdout.read()
        if line:
            # Forward to user output
            sys.stdout.write(line)

            # Also flush to logfile
            _log_file.write(line)
            _log_file.flush()

    try:
        # Execute with our args and outside args
        with Popen(command, **cmd_args, **kwargs) as p:

            if logfile:
                # Intercept p.stdout and multiplex to file and sys.stdout
                while p.poll() is None:
                    _read_and_multiplex(p)

            # Check for successful completion
            ret = p.wait()

            if logfile:
                # Read one last time to catch racy process output
                _read_and_multiplex(p)

        if ret:
            raise CalledProcessError(ret, command)

    except CalledProcessError as excinfo:
        error(f'Execution failed with return code: {excinfo.returncode}')
        raise excinfo

    finally:
        if _log_file:
            _log_file.close()

def as_tuple(item, dtype=None, length=None):
    """
    Force item to a tuple, even if `None` is provided.
    """
    # Stop complaints about `type` in this function
    # pylint: disable=redefined-builtin

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
        raise ValueError(f'Tuple needs to be of length {length: d}')
    if dtype and not all(isinstance(i, dtype) for i in t):
        raise TypeError(f'Items need to be of type {dtype}')
    return t

def auto_post_mortem_debugger(type, value, tb):  # pylint: disable=redefined-builtin
    """
    Exception hook that automatically attaches a debugger

    Activate by setting ``sys.excepthook = auto_post_mortem_debugger``

    Adapted from
    https://code.activestate.com/recipes/65287-automatically-start-the-debugger-on-an-exception/
    """
    is_interactive = hasattr(sys, 'ps1')
    no_tty = not sys.stderr.isatty() or not sys.stdin.isatty() or not sys.stdout.isatty()
    if is_interactive or no_tty or type == SyntaxError:
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback # pylint: disable=import-outside-toplevel
        import pdb # pylint: disable=import-outside-toplevel
        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        # ...then start the debugger in post-mortem mode.
        pdb.post_mortem(tb)   # pylint: disable=no-member
