from typing import Dict, List, Union

from pydantic import BaseModel, model_validator
from typing_extensions import Self

__all__ = ['ConfigMixin', 'CLASSNAME', 'RESERVED_NAMES']

CLASSNAME = 'classname'
RESERVED_NAMES = [
    CLASSNAME,
]


class ConfigMixin(BaseModel):

    @classmethod
    def from_config(
        cls, config: Dict[str, Union[str, float, int, bool, List, None]]
    ) -> 'ConfigMixin':
        return cls(**config)

    def dump_config(
        self, with_class: bool = False
    ) -> Dict[str, Union[str, float, int, bool, List]]:
        config = self.model_dump(exclude_none=True)
        if with_class:
            config['classname'] = type(self).__name__
        return config

    @model_validator(mode='before')
    def validate_variable_names_not_reserved(self) -> Self:
        if any(var in self.keys() for var in RESERVED_NAMES):
            raise ValueError(
                f'Invalid ConfigMixin class: contains reserved member name(s). Reserved: {RESERVED_NAMES}'
            )
        return self
