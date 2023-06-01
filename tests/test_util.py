"""
Tests for utility routines
"""
import os
from pathlib import Path
from subprocess import CalledProcessError
import pytest
import tempfile

from ifsbench.util import execute


def test_execute():
    """
    Test some aspects of the execute() utility.
    """
    # Very trivial executables with success/error exit codes
    execute('true')
    with pytest.raises(CalledProcessError):
        execute('false')

    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        # basic logfile capture validation
        logfile = Path(tmp_dir)/'test_execute.log'
        execute(['echo', 'foo', 'bar'], logfile=logfile)
        assert logfile.read_text() == 'foo bar\n'

        # verify env
        execute(['env'], logfile=logfile, env={'FOO': 'bar', 'BAR': 'foo'})
        with logfile.open('r') as f:
            env_str = f.read()
            assert 'FOO=bar' in env_str
            assert 'BAR=foo' in env_str

        # no output executable
        execute(['true'], logfile=logfile)
        assert logfile.read_text() == ''

        # Output a lot of lines
        text = 'abc\n' * 100
        execute(['echo', text], logfile=logfile)
        assert logfile.read_text() == text + '\n'
