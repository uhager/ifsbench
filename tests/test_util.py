"""
Tests for utility routines
"""
import os
from pathlib import Path
from subprocess import CalledProcessError
import pytest

from ifsbench.util import gettempdir, execute


def test_gettempdir():
    """
    Test that gettempdir() yields a read- and writable location.
    """
    tmpdir = gettempdir()

    assert isinstance(tmpdir, Path)
    assert tmpdir.is_dir()
    assert os.access(tmpdir, os.R_OK)
    assert os.access(tmpdir, os.W_OK)


def test_execute():
    """
    Test some aspects of the execute() utility.
    """
    execute('true')
    with pytest.raises(CalledProcessError):
        execute('false')

    logfile = gettempdir()/'test_execute.log'
    execute(['echo', 'foo', 'bar'], logfile=logfile)
    with logfile.open('r') as f:
        assert f.read() == 'foo bar\n'

    execute(['env'], logfile=logfile, env={'FOO': 'bar', 'BAR': 'foo'})
    with logfile.open('r') as f:
        env_str = f.read()
        assert 'FOO=bar' in env_str
        assert 'BAR=foo' in env_str
