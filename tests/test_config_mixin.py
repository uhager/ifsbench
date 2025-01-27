import pytest
from typing import Optional

from ifsbench import ConfigMixin


class TestConfigFromLocals(ConfigMixin):
    def __init__(self, field1: int, field2: float, field3: str):
        self.set_config_from_init_locals(locals())

    @classmethod
    def config_format(cls):
        return cls._format_from_init()


class TestConfigSet(ConfigMixin):
    def __init__(self, field1: int, field2: float, field3: str):
        config = {'field1': field1, 'field2': field2, 'field3': field3}
        self.set_config(config)

    @classmethod
    def config_format(cls):
        del cls
        return {'field1': type(int), 'field2': type(float), 'field3': type(str)}


class TestConfigNestedConfigFormat(ConfigMixin):

    @classmethod
    def config_format(cls):
        del cls
        return {
            'field1': int,
            'field2': float,
            'field3': {'field3a': str, 'field3b': int},
        }


class TestConfigOptional(ConfigMixin):
    def __init__(self, field1: int, field2: Optional[str] = None):
        self.set_config_from_init_locals(locals())

    @classmethod
    def config_format(cls):
        return cls._format_from_init()


class TestConfigList(ConfigMixin):

    @classmethod
    def config_format(cls):
        del cls
        return {
            'field1': int,
            'field2': float,
            'field3': [
                {
                    str: int,
                },
            ],
        }


VALUE1 = 3
VALUE2 = 3.1
VALUE3 = 'some/path'


def test_set_config_succeeds():

    tc = TestConfigSet(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    config = tc.get_config()

    expected = {'field1': VALUE1, 'field2': VALUE2, 'field3': VALUE3}
    assert config == expected


def test_set_config_already_set_fails():

    tc = TestConfigSet(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    config = {'field1': VALUE1, 'field2': VALUE2, 'field3': VALUE3}

    with pytest.raises(ValueError) as exceptinfo:
        tc.set_config(config)
    assert str(exceptinfo.value) == f'Config already set.'


def test_set_config_from_init_locals_succeeds():

    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    config = tc.get_config()

    expected = {'field1': VALUE1, 'field2': VALUE2, 'field3': VALUE3}
    assert config == expected


def test_set_config_from_init_optional_set_succeeds():

    tc = TestConfigOptional(field1=VALUE1, field2=VALUE3)
    conf = tc.get_config()

    expected = {'field1': VALUE1, 'field2': VALUE3}
    assert conf == expected


def test_set_config_from_init_optional_none_succeeds():

    tc = TestConfigOptional(field1=VALUE1)
    config = tc.get_config()

    expected = {'field1': VALUE1, 'field2': None}
    assert config == expected


def test_set_config_already_set_fails():

    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    with pytest.raises(ValueError):
        tc.set_config({'something': 'other'})


def test_update_config_succeeds():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)

    tc.update_config(field='field1', value=4)
    config = tc.get_config()

    expected = {'field1': 4, 'field2': VALUE2, 'field3': VALUE3}
    assert config == expected


def test_update_config_add_field_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)

    with pytest.raises(ValueError) as exceptinfo:
        tc.update_config(field='field4', value=4)
    assert (
        str(exceptinfo.value)
        == f'field4 not part of config {tc.get_config()}, not setting'
    )


def test_update_config_wrong_type_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)

    with pytest.raises(ValueError) as exceptinfo:
        tc.update_config(field='field1', value='should be int')
    assert (
        str(exceptinfo.value)
        == 'Cannot update config: wrong type <class \'str\'> for field field1'
    )


def test_validate_config_succeeds():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    to_validate = {'field1': VALUE1, 'field2': VALUE2, 'field3': VALUE3}
    tc.validate_config(config=to_validate)


def test_validate_config_unsupported_type_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    to_validate = {'field1': set(), 'field2': VALUE2, 'field3': VALUE3}
    with pytest.raises(ValueError) as exceptinfo:
        tc.validate_config(config=to_validate)
    assert str(exceptinfo.value) == f'Unsupported config value type for {set()}'


def test_validate_config_wrong_type_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    to_validate = {'field1': 'some string', 'field2': VALUE2, 'field3': VALUE3}
    with pytest.raises(ValueError) as exceptinfo:
        tc.validate_config(config=to_validate)
    assert (
        str(exceptinfo.value)
        == '"field1" has type <class \'str\'>, expected <class \'int\'>'
    )


def test_validate_config_field_not_in_config_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    to_validate = {'field1': VALUE1, 'field2': VALUE2}
    with pytest.raises(ValueError) as exceptinfo:
        tc.validate_config(config=to_validate)
    assert str(exceptinfo.value) == f'"field3" required but not in {to_validate}'


def test_validate_config_field_not_in_format_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    to_validate = {
        'field1': VALUE1,
        'field2': VALUE2,
        'field3': VALUE3,
        'field4': 'unexpected field',
    }
    with pytest.raises(ValueError) as exceptinfo:
        tc.validate_config(config=to_validate)
    assert (
        str(exceptinfo.value)
        == f'unexpected key "field4" in config, expected {tc.config_format()}'
    )


def test_validate_config_nested_succeedss():
    tc = TestConfigNestedConfigFormat()
    to_validate = {
        'field1': VALUE1,
        'field2': VALUE2,
        'field3': {'field3a': 'path', 'field3b': 42},
    }
    tc.validate_config(config=to_validate)


def test_validate_config_nested_dict_mismatch_fails():
    tc = TestConfigNestedConfigFormat()
    to_validate = {
        'field1': VALUE1,
        'field2': {'field2a': 4.4},
        'field3': {'field3a': 'path', 'field3b': 42},
    }
    with pytest.raises(ValueError) as exceptinfo:
        tc.validate_config(config=to_validate)
    assert (
        str(exceptinfo.value)
        == '"field2" has type <class \'dict\'>, expected <class \'float\'>'
    )


def test_validate_config_nested_config_not_in_format_fails():
    tc = TestConfigNestedConfigFormat()
    to_validate = {
        'field1': VALUE1,
        'field2': VALUE2,
        'field3': {'field3a': 'path', 'field3b': 42, 'field3c': 'surplus'},
    }
    with pytest.raises(ValueError) as exceptinfo:
        tc.validate_config(config=to_validate)
    expected = tc.config_format()['field3']
    assert (
        str(exceptinfo.value)
        == f'unexpected key "field3c" in config, expected {expected}'
    )


def test_validate_config_optional_set_succeeds():

    tc = TestConfigOptional(field1=VALUE1, field2=VALUE3)
    to_validate = {'field1': VALUE1, 'field2': VALUE3}

    tc.validate_config(to_validate)


def test_validate_config_optional_not_given_succeeds():

    tc = TestConfigOptional(field1=VALUE1, field2=VALUE3)
    to_validate = {'field1': VALUE1}

    tc.validate_config(to_validate)


def test_validate_config_list_succeeds():
    tc = TestConfigList()
    to_validate = {
        'field1': VALUE1,
        'field2': VALUE2,
        'field3': [
            {'field3a': 'path', 'field3b': 'another path'},
            {'field3a': 'path2', 'field3b': 'another path2'},
        ],
    }
    tc.validate_config(config=to_validate)


def test_validate_config_list_wrong_type_fails():
    tc = TestConfigList()
    to_validate = {
        'field1': VALUE1,
        'field2': VALUE2,
        'field3': ['path', 'another path'],
    }
    with pytest.raises(ValueError) as exceptinfo:
        tc.validate_config(config=to_validate)
    assert (
        str(exceptinfo.value)
        == f'list entries for "field3" have type <class \'str\'>, expected <class \'dict\'>'
    )


def test_update_config_succeeds():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)
    config = tc.get_config().copy()

    tc.update_config('field1', 5)

    out_conf = tc.get_config()
    config['field1'] = 5

    assert out_conf == config


def test_update_config_new_field_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)

    with pytest.raises(ValueError) as exceptinfo:
        tc.update_config('field4', 5)
    assert (
        str(exceptinfo.value)
        == f'field4 not part of config {tc.get_config()}, not setting'
    )


def test_update_config_wrong_type_fails():
    tc = TestConfigFromLocals(field1=VALUE1, field2=VALUE2, field3=VALUE3)

    with pytest.raises(ValueError) as exceptinfo:
        tc.update_config('field1', 3.3)
    assert (
        str(exceptinfo.value)
        == f'Cannot update config: wrong type <class \'float\'> for field field1'
    )
