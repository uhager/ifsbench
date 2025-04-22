# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from pydantic import (
    BaseModel,
    model_validator,
    ModelWrapValidatorHandler,
    TypeAdapter,
    Field,
)
from pydantic_core.core_schema import ValidatorFunctionWrapHandler
from typing_extensions import Annotated, Literal, Self

__all__ = ['ConfigMixin', 'PydanticConfigMixin', 'pydantic_subclass_resolution', 'CLASSNAME', 'RESERVED_NAMES']

# Reserved strings:
# 'classname' is used in the configuration to indicate which class has to be
# constructed with that configuration and cannot be used for member variables
# in implementing classes.
CLASSNAME = 'classname'
RESERVED_NAMES = [
    CLASSNAME,
]


class ConfigMixin(ABC):

    @classmethod
    @abstractmethod
    def from_config(
        cls, config: Dict[str, Union[str, float, int, bool, List, None]]
    ) -> 'ConfigMixin':
        """Create instance based on config.

        Args:
            config: names and values for member variables.

        Returns:
            class instance
        """
        raise NotImplementedError()

    @abstractmethod
    def dump_config(
        self, with_class: bool = False
    ) -> Dict[str, Union[str, float, int, bool, List]]:
        """Get configuration for output.

        Args:
            with_class: Add CLASSNAME key with class name to configuration.

        Returns:
            Configuration that can be used to create instance.
        """
        raise NotImplementedError()


class PydanticConfigMixin(ConfigMixin, BaseModel, use_enum_values=True):
    """
    Base class for handling configurations in a format that can be used for storage.

    Uses pydantic for type checking and managing the config dictionary.
    """

    @classmethod
    def from_config(
        cls, config: Dict[str, Union[str, float, int, bool, List, None]]
    ) -> 'PydanticConfigMixin':
        """Create instance based on config.

        Args:
            config: names and values for member variables.

        Returns:
            class instance
        """
        return cls(**config)

    def dump_config(
        self, with_class: bool = False
    ) -> Dict[str, Union[str, float, int, bool, List]]:
        """Get configuration for output.

        Args:
            with_class: Add CLASSNAME key with class name to configuration.

        Returns:
            Configuration that can be used to create instance.
        """
        config = self.model_dump(exclude_none=True, round_trip=True)
        for k, v in config.items():
            if isinstance(v, Path):
                config[k] = str(v)
        if with_class:
            config['classname'] = type(self).__name__
        return config

    @model_validator(mode='before')
    def _validate_variable_names_not_reserved(self) -> Self:
        if any(var in self.keys() for var in RESERVED_NAMES):
            raise ValueError(
                f'Invalid ConfigMixin class: contains reserved member name(s). Reserved: {RESERVED_NAMES}'
            )
        return self


def pydantic_subclass_resolution(inner_cls):

    @classmethod
    @model_validator(mode='wrap')
    def _parse_into_subclass(
        cls, v: Any, handler: ValidatorFunctionWrapHandler
    ) -> Self:
        print(f'[DEBUG] parse_into\ninner_cls: {inner_cls}, cls: {cls}, Self: {Self}, v: {v}')
        if cls is inner_cls:
            print(f'[DEBUG] cls is Self')
            return cls._discriminating_type_adapter.validate_python(v)
        print(f'[DEBUG] cls is not Self')
        return handler(v)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        print(f'[DEBUG] __pyd_init_subc, inner_cls: {inner_cls}, cls: {cls}')
        cls._subclasses[cls.model_fields[cls._discriminator_tag].default] = cls
        print(f'[DEBUG] {cls} subclasses: {cls._subclasses}')
        cls._discriminating_type_adapter = TypeAdapter(
            Annotated[
                Union[tuple(cls._subclasses.values())],
                Field(discriminator=cls._discriminator_tag),
            ]
        )
        print(f'[DEBUG] {inner_cls} - {cls} type_adapter:\n{cls._discriminating_type_adapter}')

    setattr(inner_cls, '_parse_into_subclass', _parse_into_subclass)
    setattr(inner_cls, '__pydantic_init_subclass__', __pydantic_init_subclass__)
    return inner_cls
