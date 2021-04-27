"""
Tests for handling namelists
"""
from pathlib import Path
import pytest
import f90nml
from ifsbench import sanitize_namelist, gettempdir


def test_sanitize_namelist():
    nml_string = """
&a
    foo = 4
    foobar = 3
/
&b
    bar = 1
    foo = 2
/
&a
    foo = 1
    bar = 2
/
    """.strip()

    nml_file = gettempdir()/'nml'
    with nml_file.open('w') as f:
        f.write(nml_string)
    nml = f90nml.read(nml_file)
    
    sanitized = sanitize_namelist(nml, merge_strategy='first')
    assert sanitized.todict() == {'a': {'foo': 4, 'foobar': 3}, 'b': {'bar': 1, 'foo': 2}}
    
    sanitized = sanitize_namelist(nml, merge_strategy='last')
    assert sanitized.todict() == {'a': {'foo': 1, 'bar': 2}, 'b': {'bar': 1, 'foo': 2}}
    
    sanitized = sanitize_namelist(nml, merge_strategy='merge_first')
    assert sanitized.todict() == {'a': {'foo': 4, 'foobar': 3, 'bar': 2}, 'b': {'bar': 1, 'foo': 2}}
    
    sanitized = sanitize_namelist(nml, merge_strategy='merge_last')
    assert sanitized.todict() == {'a': {'foo': 1, 'foobar': 3, 'bar': 2}, 'b': {'bar': 1, 'foo': 2}}

    nml_file.unlink()
