import f90nml
from pathlib import Path


__all__ = ['IFSNamelist']


class IFSNamelist(object):
    """
    Class to manage construction and validation of IFS-specific namelists.
    """

    def __init__(self, template=None, namelist=None):
        self.nml = f90nml.Namelist()
        self.nml.uppercase = True
        self.nml.end_comma = True
        self.template = None if template is None else Path(template)

        if self.template is not None:
            self.add(self.template)

        if namelist is not None:
            self.add(namelist)

    def __getitem__(self, key):
        key = key.lower()
        return self.nml[key]

    def __setitem__(self, key, value):
        key = key.lower()
        self.nml[key] = value

    def __delitem__(self, key):
        key = key.lower()
        del self.nml[key]

    def __contains__(self, key):
        key = key.lower()
        return key in self.nml

    def __len__(self):
        return len(self.nml)

    def add(self, filepath):
        """
        Add contents of another namelist from file
        """
        self.nml.update(f90nml.read(filepath))

    def write(self, filepath, force=True):
        self.nml.write(filepath, force=force)
