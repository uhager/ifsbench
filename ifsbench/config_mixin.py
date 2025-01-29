from typing import Dict, List, Union

from pydantic import BaseModel

__all__ = ['ConfigMixin']


class ConfigMixin(BaseModel):

    @classmethod
    def from_config(
        cls, config: Dict[str, Union[str, float, int, bool, List, None]]
    ) -> 'ConfigMixin':
        return cls(**config)

    def dump_config(self) -> Dict[str, Union[str, float, int, bool, List]]:
        return self.model_dump(exclude_none=True)
