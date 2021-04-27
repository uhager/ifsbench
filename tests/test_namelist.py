"""
Tests for handling namelists
"""
from pathlib import Path
import pytest
import f90nml
from ifsbench import sanitize_namelist, namelist_diff, gettempdir


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


def test_namelist_diff():
    nml1_string = """
&a
    foo = 1
    bar = 2
/
&b
    bar = 1
    foo = 2
/
    """.strip()
    nml2_string = """
&a
    bar = 2
    foo = 1
/
&b
    foo = 2
    bar = 1
/
    """.strip()
    nml3_string = """
&a
    bar = 1
    foobar = 3
/
&c
    foofoo = 4
/
    """.strip()

    nml1_file = gettempdir()/'nml1'
    with nml1_file.open('w') as f:
        f.write(nml1_string)
    nml1 = f90nml.read(nml1_file)

    nml2_file = gettempdir()/'nml2'
    with nml2_file.open('w') as f:
        f.write(nml2_string)
    nml2 = f90nml.read(nml2_file)

    nml3_file = gettempdir()/'nml3'
    with nml3_file.open('w') as f:
        f.write(nml3_string)
    nml3 = f90nml.read(nml3_file)

    assert not namelist_diff(nml1, nml1.copy())
    assert not namelist_diff(nml1, nml2)
    assert namelist_diff(nml1, nml3) == {
        'a': {
            'foo': (1, None),
            'bar': (2, 1),
            'foobar': (None, 3),
        },
        'b': ({'bar': 1, 'foo': 2}, None),
        'c': (None, {'foofoo': 4}),
    }

    nml1_file.unlink()
    nml2_file.unlink()
    nml3_file.unlink()
