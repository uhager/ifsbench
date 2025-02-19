import json
import pathlib
import re
from typing import Dict, List, Union

import pandas as pd

__all__ = ['EnsembleStats', 'ENSEMBLE_DATA_PATH']

ENSEMBLE_DATA_PATH = 'ensemble_data'
AVAILABLE_BASIC_STATS = ['min', 'max', 'mean', 'median', 'sum', 'std']

_JSON_ORIENT = 'columns'


def _percentile(nth):
    def _qtile(data):
        return data.quantile(nth / 100.0)

    _qtile.__name__ = 'p{:02.0f}'.format(nth)
    return _qtile


class EnsembleStats:

    def __init__(self, data: List[pd.DataFrame]):
        self._raw_data = data
        dfc = pd.concat(data)
        self._group = dfc.groupby(dfc.index)

    @classmethod
    def from_data(cls, raw_data: List[pd.DataFrame]) -> 'EnsembleStats':
        return cls(raw_data)

    @classmethod
    def from_config(cls, config: Dict[str, str]) -> 'EnsembleStats':
        if not ENSEMBLE_DATA_PATH in config:
            raise ValueError(f'missing config entry {ENSEMBLE_DATA_PATH}')
        if len(config) > 1:
            raise ValueError(
                f'unexpected entries in config: {config}, expected only {ENSEMBLE_DATA_PATH}'
            )
        input_path = pathlib.Path(config[ENSEMBLE_DATA_PATH])
        with open(input_path, 'r') as jin:
            jdata = json.load(jin)
        dfs = [pd.DataFrame.from_dict(json.loads(entry)) for entry in jdata]
        return cls(dfs)

    def dump_data_to_json(self, output_file: Union[pathlib.Path, str]):
        js = [df.to_json(orient=_JSON_ORIENT) for df in self._raw_data]
        with open(output_file, 'w') as outf:
            json.dump(js, outf)

    def calc_stats(self, stats: Union[str, List[str]]) -> pd.DataFrame:
        if isinstance(stats, str):
            stats = [stats]
        to_request = []
        for stat in stats:
            percentile_check = re.match(r'[p,P](\d{1,2})$', stat)
            if percentile_check:
                ptile_value = int(percentile_check.group(1))
                to_request.append(_percentile(ptile_value))
            elif stat in AVAILABLE_BASIC_STATS:
                to_request.append(stat)
            else:
                raise ValueError(
                    f'Unknown stat requested: {stat}. Supported: {AVAILABLE_BASIC_STATS} and percentiles in format like [p25, P90]'
                )
        return self._group.agg(to_request)
