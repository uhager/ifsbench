"""
Handling and modifying of Fortran namelists for IFS
"""
from collections import OrderedDict
from pathlib import Path
import f90nml


__all__ = ['IFSNamelist', 'sanitize_namelist', 'namelist_diff']


class IFSNamelist:
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
        other_nml = sanitize_namelist(f90nml.read(filepath))
        self.nml.update(other_nml)

    def write(self, filepath, force=True):
        self.nml.write(filepath, force=force)


def sanitize_namelist(nml, merge_strategy='first'):
    """
    Sanitize a given namelist

    Currently, this only removes redundant namelist groups by applying one
    of the following merge strategies:

    * `'first'`: For multiply defined namelist groups, retain only the first.
    * `'last'`: For multiply defined namelist groups, retain only the last.
    * `'merge_first'`: For multiply defined namelist groups, merge variable
      definitions from all groups. Conflicts are resolved by using the first
      occurence of a variable.
    * `'merge_last'`: For multiply defined namelist groups, merge variable
      definitions from all groups. Conflicts are resolved by using the last
      occurence of a variable.

    Parameters
    ----------
    nml : :any:`f90nml.Namelist`
        The namelist to sanitise
    merge_strategy : str, optional
        The merge strategy to use.

    Returns
    -------
    f90nml.Namelist
        The sanitised namelist
    """
    nml = nml.copy()
    for key in nml:
        if isinstance(nml[key], list):
            if merge_strategy == 'first':
                nml[key] = nml[key][0]
            elif merge_strategy == 'last':
                nml[key] = nml[key][-1]
            elif merge_strategy == 'merge_first':
                merged = f90nml.Namelist({key: {}})
                for values in reversed(nml[key]):
                    merged.patch(f90nml.Namelist({key: values}))
                nml[key] = merged[key]
            elif merge_strategy == 'merge_last':
                merged = f90nml.Namelist({key: {}})
                for values in nml[key]:
                    merged.patch(f90nml.Namelist({key: values}))
                nml[key] = merged[key]
            else:
                raise ValueError('Invalid merge strategy: {}'.format(merge_strategy))
    return nml


def namelist_diff(nml, other_nml):
    """
    Find differences between :any:`f90nml.Namelist` objects :attr:`nml` and
    :attr:`other_nml`

    Parameters
    ----------
    nml : :any:`f90nml.Namelist`
        A namelist object
    other_nml : :any:`f90nml.Namelist`
        A namelist object to compare to the first

    Returns
    -------
    :any:`OrderedDict`
        Differences between the two namelists as 2-tuple with the corresponding
        values from :attr:`nml` and :attr:`other_nml`. Values or groups that
        are present only in one are reported as `None` for the other.

        .. note::

            In case an entire namelist group is present only in one, then it
            is returned in the tuple as a `dict` with the other value `None`.
            For example:

            .. code-block::

                {
                    ...
                    'group': (None, {'var1': 42, 'var2': 23}),
                    ...
                }
    """
    diff = OrderedDict()

    # Run through groups present in nml
    for group, values in nml.items():
        other_values = other_nml.get(group)
        if isinstance(values, f90nml.Namelist):
            if isinstance(other_values, f90nml.Namelist):
                group_diff = namelist_diff(values, other_values)
                if group_diff:
                    diff[group] = group_diff
            else:
                diff[group] = (values.todict(), other_values)
        elif values != other_values:
            diff[group] = (values, other_values)

    # Add any groups present only in other_nml
    for group, values in other_nml.items():
        if group not in nml:
            if isinstance(values, f90nml.Namelist):
                diff[group] = (None, values.todict())
            else:
                diff[group] = (None, values)

    return diff
