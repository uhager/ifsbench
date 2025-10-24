# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import abstractmethod
from pathlib import Path

from typing import Union

from ifsbench.serialisation_mixin import SubclassableSerialisationMixin

__all__ = ["DataHandler", "absolutise_path"]


class DataHandler(SubclassableSerialisationMixin):
    """
    Base class for data pipeline steps.

    Each DataHandler object describes one step in the data pipeline. Multiple
    DataHandler objects can be executed sequentially to perform specific data
    setup tasks.
    """

    @abstractmethod
    def execute(self, wdir: Union[str, Path], **kwargs):
        """
        Run this data handling operation in a given directory.

        Parameters
        ----------
        wdir    : str or :any:`pathlib.Path`
            The directory where the data handling should take place.
            Subclasses of DataHandler should operate relative to this path,
            unless absolute paths are given.
        """
        return NotImplemented


def absolutise_path(wdir: Union[str, Path], target: Path) -> Path:
    """
    Ensure target is an absolute path.

    Parameters
    wdir    : str or :any:`pathlib.Path`
        If the target path is not absolute, it will be in this directory.
    target  : :any:`pathlib.Path`
        Path which if not absolute will be inside wdir

    Returns:
       Path to target as absolute pathlib.Path

    """
    if target.is_absolute():
        return target

    return Path(wdir) / target
