from abc import ABC, abstractmethod
from typing import Any, Dict, get_args, get_origin, get_type_hints, List, Union

__all__ = ['ConfigMixin', 'CONF']


CONF = Union[int, float, str, bool, Dict, List, None]


def _config_from_locals(config: Dict[str, Any]) -> None:
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

    _mixin_config = None

    @classmethod
    @abstractmethod
    def config_format(cls) -> Dict[str, Any]:
        raise NotImplementedError()

    @classmethod
    def _format_from_init(cls) -> Dict[str, Any]:
        format_definition = dict(get_type_hints(cls.__init__, include_extras=False))
        format_definition = _config_from_locals(format_definition)
        return format_definition

    def set_config_from_init_locals(self, config: Dict[str, Any]):
        config = _config_from_locals(config)
        self.set_config(config)

    def set_config(self, config: Dict[str, CONF]) -> None:
        if self._mixin_config:
            raise ValueError('Config already set.')
        self._mixin_config = config

    def get_config(self) -> Dict[str, CONF]:
        return self._mixin_config

    def update_config(self, field: str, value: CONF) -> None:
        if field not in self._mixin_config:
            raise ValueError(f'{field} not part of config {self._mixin_config}, not setting')
        if not isinstance(value, type(self._mixin_config[field])):
            raise ValueError(
                f'Cannot update config: wrong type {type(value)} for field {field}'
            )
        self._mixin_config[field] = value

    @classmethod
    def validate_config(cls, config: Dict[str, CONF]):
        format_definition = cls.config_format()
        cls._validate_config_from_format(config, format_definition)

    @classmethod
    def _validate_config_from_format(
        cls, config: Dict[str, CONF], format_definition: Dict[str, Any]
    ):

        for key, value in config.items():
            if not isinstance(value, CONF):
                # check that the given value is a valid config type
                raise ValueError(f'Unsupported config value type for {value}')
            if key not in format_definition:
                raise ValueError(f'unexpected key "{key}" in config, expected {format_definition}')

        for key, value in format_definition.items():

            if (key not in config) and (type(None) not in get_args(value)):
                # format_definition key has to be in config unless it's optional
                raise ValueError(f'"{key}" required but not in {config}')
            if isinstance(value, Dict):
                # nested, check that field also nested in config, then recursively check dict.
                if not isinstance(config[key], Dict):
                    raise ValueError(
                        f'"{key}" has type {type(config[key])}, expected {value}'
                    )
                cls._validate_config_from_format(config[key], format_definition[key])
            elif isinstance(value, List):
                # For now, only check both are lists and first entry type is correct, don't check every entry.
                if not isinstance(config[key], list):
                    raise ValueError(
                        f'"{key}" has type {type(config[key])}, expected {value}'
                    )
                if not isinstance(value[0], type(config[key][0])):
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
            elif not isinstance(config[key], value):
                # types of format and config have to match
                raise ValueError(
                    f'"{key}" has type {type(config[key])}, expected {value}'
                )
