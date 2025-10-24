# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pathlib
import shutil
from typing import Optional, Union

from ifsbench.data.datahandler import DataHandler
from ifsbench.logging import debug

__all__ = ['ExtractHandler']


class ExtractHandler(DataHandler):
    """
    DataHandler that extracts a given archive to a specific directory.

    Parameters
    ----------
    archive_path: str or :any:`pathlib.Path`
        The path to the archive that will be extracted. If a relative path
        is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.

    target_dir: str, :any:`pathlib.Path` or None
        The directory where the archive will be unpacked. If a relative path
        is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.
    """

    archive_path: pathlib.Path
    target_dir: Optional[pathlib.Path] = None

    def execute(self, wdir: Union[str, pathlib.Path], **kwargs) -> None:
        wdir = pathlib.Path(wdir)

        if not self.archive_path.is_absolute():
            archive_path = wdir/self.archive_path
        else:
            archive_path = self.archive_path

        target_dir = wdir
        if self.target_dir is not None:
            if self.target_dir.is_absolute():
                target_dir = self.target_dir
            else:
                target_dir = wdir / self.target_dir

        debug(f"Unpack archive {str(archive_path)} to {str(target_dir)}.")
        shutil.unpack_archive(archive_path, target_dir)
