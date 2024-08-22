import re

import cfgrib
import pandas as pd
import xarray as xr

__all__ = ['GribFile']

# Dimensions over which to calculate statistics. Other dimensions will be kept separate.
_STAT_DIMS = set(['values', 'latitudes', 'longitudes'])

# Statistics to calculate, has to be implemented in _calc_stat.
# Percentiles have to be given in a form that matches r'[p,P](\d{1,2})$'.
_STAT_NAMES =  ['mean', 'min', 'max', 'p5', 'p10', 'p90', 'p95']

# Dimension name to add to statistics datasets and use for merging.
# This will be the column name in the dataframe with values from
# _STAT_NAMES
_STAT_DIM_NAME = 'stat'

class GribFile:

    def __init__(self, input_path: str):
        self._input_path = input_path
        self._stats = []

    def get_stats(self) -> list[pd.DataFrame]:
        """Create dataframe with statistics over location.

        Dimensions to calculate the statistics over are specified by
        _STAT_DIMS, other dimensions are preserved. 
        Statistics to calculate are given by _STAT_NAMES.
        N.B. The grib file has to be compliant with standards,
        otherwise cfgrib will not be able to assemble datasets from it.

        Returns: List of dataframes containing the requested statistics.
        """
        if self._stats:
            return self._stats

        dss = self._read_grib(self._input_path)
        for ds in dss:
            stat_dims = list(set(ds.sizes.keys()) & _STAT_DIMS)
            stats_dss = [self._create_stat_ds(ds, stat_name, stat_dims) for stat_name in _STAT_NAMES]
            ds_stats = xr.concat(stats_dss, dim=_STAT_DIM_NAME)
            self._stats.append(ds_stats.to_dataframe())
        return self._stats

    @classmethod
    def _read_grib(cls, input_path: str) -> list[xr.Dataset]:
        """Reads GRIB file and returns data as dataframe.

        Note that cfgrib can be fickle and the GRIB data needs to be to spec.
            The data in the file is sorted into datasets based on levels and other parameters;
            this means that a single GRIB file can result in any number of dataframes.
        
        Args:
            input_path: Path to input GRIB file.

        Returns: List of datasets containing the data from the file.
        """
        return cfgrib.open_datasets(input_path, backend_kwargs={'indexpath': ''})

    @classmethod
    def _calc_stat(cls, ds: xr.Dataset, stat_name: str, stat_dims: list[str]) -> xr.Dataset:
        """Creates datasets containing the statistical value specified by stat_name. """
        if stat_name == 'mean':
            return ds.mean(dim=stat_dims)
        elif stat_name == 'min':
            return ds.min(dim=stat_dims)
        elif stat_name == 'max':
            return ds.max(dim=stat_dims)
        
        percentile_check = re.match(r'[p,P](\d{1,2})$', stat_name)
        if percentile_check:
            percentile = int(percentile_check.group(1))
            ds_stat = ds.quantile(percentile / 100., dim=stat_dims)
            # `quantile` removes dimensionless coordinates and adds a new coordinate 'quantiles'.
            # This has to be undone to match the other stats datasets.
            return ds_stat.drop_vars('quantile').assign_coords(ds.coords).drop_dims(stat_dims)

        raise ValueError('Unknown stat requested: %s', stat_name)
    
    @classmethod
    def _create_stat_ds(cls, ds: xr.Dataset, stat_name: str, stat_dims: list[str]) -> xr.Dataset:
        ds_stat = cls._calc_stat(ds, stat_name, stat_dims)                               
        return ds_stat.assign_coords({_STAT_DIM_NAME: stat_name}).expand_dims(_STAT_DIM_NAME)
    
