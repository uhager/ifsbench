from typing import Dict, List, Union

from pydantic import BaseModel

__all__ = ['ConfigMixin', 'CLASSNAME', 'RESERVED_STRINGS']

CLASSNAME = 'classname'
RESERVED_STRINGS = [CLASSNAME,]

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
