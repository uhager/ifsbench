from typing import Dict, List

import pytest
from pydantic import ValidationError

from ifsbench import ConfigMixin


class TestImpl(ConfigMixin):
    field_str: str
    field_int: int
    field_list: List[Dict[str, str]]


def test_from_config_succeeds():

    config = {
        'field_str': 'val_str',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
    }
    ti = TestImpl.from_config(config)

    assert ti.field_str == 'val_str'


def test_from_config_invalid_fails():

    config = {
        'field_str': 999.0,
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
    }
    with pytest.raises(ValidationError):
        TestImpl.from_config(config)


def test_dumb_config_succeeds():

    config = {
        'field_str': 'val_str',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
    }
    ti = TestImpl.from_config(config)

    assert ti.dump_config() == config


def test_dumb_config_with_class_succeeds():

    config = {
        'field_str': 'val_str',
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
    }
    ti = TestImpl.from_config(config)

    expected = config.copy()
    expected['classname'] = 'TestImpl'
    assert ti.dump_config(with_class=True) == expected


def test_from_config_invalid_class_member_fails():

    class TestInvalidImpl(ConfigMixin):
        classname: str
        field_int: int
        field_list: List[Dict[str, str]]

    config = {
        'classname': 999.0,
        'field_int': 666,
        'field_list': [
            {'sub1': 'val1', 'sub2': 'val2'},
        ],
    }

    with pytest.raises(ValidationError) as exceptinfo:
        TestInvalidImpl(**config)
    expected = 'Value error, Invalid ConfigMixin class: contains reserved member name(s). Reserved:'

    assert expected in str(exceptinfo.value)
