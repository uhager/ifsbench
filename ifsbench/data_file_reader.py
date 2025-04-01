from abc import ABC, abstractmethod
from typing import List

import xarray as xr

__all__ = ['DataFileReader', 'NetcdfFileReader']


class DataFileReader(ABC):

    @classmethod
    @abstractmethod
    def read_data(cls, input_path: str) -> List[xr.Dataset]:
        raise NotImplementedError()


class NetcdfFileReader(DataFileReader):

    @classmethod
    def read_data(cls, input_path: str) -> List[xr.Dataset]:

        # Specifying the engine is not strictly necessary since xarray
        # will determine the file type, but we want to use the grib implementation
        # for GRIB files, otherwise this code can fail in cryptic ways.
        # Explicitly setting the engine results in a clearer error.
        return [xr.open_dataset(input_path, engine='netcdf4')]
