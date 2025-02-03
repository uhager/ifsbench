from pathlib import Path
from typing import Dict, List, Union

from pydantic import BaseModel, model_validator
from typing_extensions import Self

__all__ = ['ConfigMixin', 'CLASSNAME', 'RESERVED_NAMES']

# Reserved strings:
# 'classname' is used in the configuration to indicate which class has to be
# constructed with that configuration and cannot be used for member variables
# in implementing classes.
CLASSNAME = 'classname'
RESERVED_NAMES = [
    CLASSNAME,
]


class ConfigMixin(BaseModel):
    """
    Base class for handling configurations in a format that can be used for storage.

    Uses pydantic for type checking and managing the config dictionary.
    """

    @classmethod
    def from_config(
        cls, config: Dict[str, Union[str, float, int, bool, List, None]]
    ) -> 'ConfigMixin':
        """Create instance based on config.

        Args:
            config: names and values for member variables.

        Returns:
            class instance
        """
        return cls(**config)

    def dump_config(
        self, with_class: bool = False
    ) -> Dict[str, Union[str, float, int, bool, Path, List]]:
        """Get configuration for output.

        Args:
            with_class: Add CLASSNAME key with class name to configuration.

        Returns:
            Configuration that can be used to create instance.
        """
        config = self.model_dump(exclude_none=True)
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
