from abc import ABC, abstractmethod
from typing import Any, get_args, get_origin, get_type_hints, Optional, TypeVar, Union

__all__ = ['ConfigMixin', 'CONF']


CONF = Union[int, float, str, bool, dict, list, None]


def _config_from_locals(config: dict[str, Any]) -> None:
    print(f'from locals: config={config}, type={type(config)}')
    config = config.copy()
    config.pop('self', None)
    config.pop('cls', None)
    return config


class ConfigMixin(ABC):
    """
    Base class for handling configurations in a format that can be used for storage.

    The contents of the config are based on the parameters required by the implementing
    classes constructor. Because of this, additional entries cannot be added to an existing config.
    However, the values of individual entries can be updated with a value of the same type.

    The required format can be either created based on the constructor, or explicitly set by
    implementing the `config_format` method.

    Parameters
    ----
    config: dictionary containing parameter names and their values
    """

    _config = None

    @classmethod
    @abstractmethod
    def config_format(cls) -> dict[str, type | dict]:
        raise NotImplementedError()

    @classmethod
    def _format_from_init(cls) -> dict[str, type | dict]:
        format = dict(get_type_hints(cls.__init__, include_extras=False))
        print(f'format initial={format}, type={type(format)}')
        format = _config_from_locals(format)
        print(f'format cleaned: {format}')
        return format

    def set_config_from_init_locals(self, config: dict[str, Any]):
        config = _config_from_locals(config)
        self.set_config(config)

    def set_config(self, config: dict[str, CONF]) -> None:
        if self._config:
            raise ValueError('Config already set.')
        self._config = config

    def get_config(self) -> dict[str, CONF]:
        return self._config

    def update_config(self, field: str, value: CONF) -> None:
        if field not in self._config:
            raise ValueError(f'{field} not part of config {self._config}, not setting')
        if type(value) != type(self._config[field]):
            raise ValueError(
                f'Cannot update config: wrong type {type(value)} for field {field}'
            )
        self._config[field] = value

    @classmethod
    def validate_config(cls, config: dict[str, CONF]):
        format = cls.config_format()
        cls._validate_config_from_format(config, format)

    @classmethod
    def _validate_config_from_format(
        cls, config: dict[str, CONF], format: dict[str, type | dict]
    ):
        print(f'config: {config}')
        print(f'format: {format}')

        for key, value in config.items():
            if not isinstance(value, CONF):
                # check that the given value is a valid config type
                raise ValueError(f'Unsupported config value type for {value}')
            if key not in format:
                raise ValueError(f'unexpected key "{key}" in config, expected {format}')

        for key, value in format.items():

            if (key not in config) and (type(None) not in get_args(value)):
                # format key has to be in config unless it's optional
                raise ValueError(f'"{key}" required but not in {config}')
            if isinstance(value, dict):
                # nested, check that field also nested in config, then recursively check dict.
                if not isinstance(config[key], dict):
                    raise ValueError(
                        f'"{key}" has type {type(config[key])}, expected {value}'
                    )
                cls._validate_config_from_format(config[key], format[key])
            elif isinstance(value, list):
                # For now, only check both are lists and first entry type is correct, don't check every entry.
                if not isinstance(config[key], list):
                    raise ValueError(
                        f'"{key}" has type {type(config[key])}, expected {value}'
                    )
                if type(value[0]) != type(config[key][0]):
                    raise ValueError(
                        f'list entries for "{key}" have type {type(config[key][0])}, expected {type(value[0])}'
                    )
            elif get_origin(value) == Union and type(None) in get_args(value):
                # Optional: check matching type or None
                opt_type = get_args(value)
                if key in config and type(config[key]) not in opt_type:
                    raise ValueError(
                        f'wrong type for optional {type(value)}: {config[key]}'
                    )
            elif type(config[key]) != value:
                # types of format and config have to match
                raise ValueError(
                    f'"{key}" has type {type(config[key])}, expected {value}'
                )
