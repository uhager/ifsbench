# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from enum import auto, StrEnum
import pathlib
from typing import Any, Dict


import f90nml

from ifsbench.config_mixin import CONF, ConfigMixin
from ifsbench.data.datahandler import DataHandler
from ifsbench.logging import debug, info


__all__ = ['NamelistOverride', 'NamelistHandler', 'NamelistOperation']


class NamelistOperation(StrEnum):
    SET = auto()
    APPEND = auto()
    DELETE = auto()


class NamelistOverride(ConfigMixin):
    """
    Specify changes that will be applied to a namelist.

    Parameters
    ----------
    key: str or iterable of str
        The namelist entry that will be modified. Can be either a string
        where '/' separates the namelist name and the entry key or an iterable
        of strings of length two.

    mode: NamelistOperation
        What kind of operation is specified. Can be
            * Set a certain entry.
            * Append to an array entry.
            * Delete an entry.

    value: str or None
        The value that is set (SET operation) or appended (APPEND).
    """

    def __init__(
        self, namelist: str, entry: str, mode: NamelistOperation, value: CONF = None
    ):

        self.set_config_from_init_locals(locals())
        self._keys = (namelist, entry)
        self._mode = mode
        self._value = value

        if self._value is None:
            if self._mode in (NamelistOperation.SET, NamelistOperation.APPEND):
                raise ValueError("The new value must not be None!")

    @classmethod
    def from_keytuple(
        cls, key: tuple[str, str], mode: NamelistOperation, value: CONF = None
    ) -> 'NamelistOverride':
        if len(key) != 2:
            raise ValueError(f"The key tuple must be of length two, found key {key}.")
        return cls(key[0], key[1], mode, value)

    @classmethod
    def from_keystring(
        cls, key: str, mode: NamelistOperation, value: CONF = None
    ) -> 'NamelistOverride':
        keys = key.split('/')
        if len(keys) != 2:
            raise ValueError(
                f"The key string must contain single '/', found key {key}."
            )
        return cls(keys[0], keys[1], mode, value)

    @classmethod
    def from_config(cls, config: dict[str, CONF]) -> 'NamelistOverride':
        cls.validate_config(config)
        value = config['value'] if 'value' in config else None
        return cls(config['namelist'], config['entry'], config['mode'], value)

    @classmethod
    def config_format(cls) -> Dict[str, Any]:
        return cls._format_from_init()

    def apply(self, namelist):
        """
        Apply the stored changes to a namelist.

        Parameters
        ----------
        namelist: :any:`f90nml.Namelist`
            The namelist to which the changes are applied.
        """

        if self._keys[0] not in namelist:
            if self._mode == NamelistOperation.DELETE:
                return

            namelist[self._keys[0]] = {}

        namelist = namelist[self._keys[0]]
        key = self._keys[-1]

        if self._mode == NamelistOperation.SET:
            debug(f"Set namelist entry {str(self._keys)} = {str(self._value)}.")
            namelist[key] = self._value
        elif self._mode == NamelistOperation.APPEND:
            if key not in namelist:
                namelist[key] = []

            if not hasattr(namelist[key], 'append'):
                raise ValueError("Values can only be appended to arrays!")

            # f90nml doesn't seem to do any kind of checking, so we could
            # create arrays in the namelist where the entries have different
            # types.
            # This will most likely cause issues, so we verify here, that
            # the array entries have the same type.
            if len(namelist[key]) > 0:
                type_list = type(namelist[key][0])
                type_value = type(self._value)

                if type_list != type_value:
                    raise ValueError(
                        "The given value must have the same type as existing array entries!"
                    )

            debug(f"Append {str(self._value)} to namelist entry {str(self._keys)}.")

            namelist[key].append(self._value)

        elif self._mode == NamelistOperation.DELETE:
            if key in namelist:
                debug(f"Delete namelist entry {str(self._keys)}.")
                del namelist[key]


class NamelistHandler(DataHandler, ConfigMixin):
    """
    DataHandler specialisation that can modify Fortran namelists.

    Parameters
    ----------
    input_path: str or :any:`pathlib.Path`
        The path to the namelist that will be modified. If a relative path
        is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.

    output_path: str or :any:`pathlib.Path`
        The path to which the updated namelist will be written. If a relative
        path is given, this will be relative to the ``wdir`` argument in
        :meth:`execute`.

    overrides: iterable of :class:`NamelistOverride`
        The NamelistOverrides that will be applied.
    """

    def __init__(
        self, input_path: str, output_path: str, overrides: list[NamelistOverride]
    ):

        override_confs = [no.get_config() for no in overrides]
        self.set_config(
            {
                'input_path': input_path,
                'output_path': output_path,
                'overrides': override_confs,
            }
        )

        self._input_path = pathlib.Path(input_path)
        self._output_path = pathlib.Path(output_path)

        self._overrides = list(overrides)
        for override in self._overrides:
            if not isinstance(override, NamelistOverride):
                raise ValueError("Namelist overrides must be NamelistOverride objects!")

    @classmethod
    def config_format(cls) -> dict[str, Any]:
        return {
            'input_path': str,
            'output_path': str,
            'overrides': [
                {
                    str: CONF,
                },
            ],
        }

    @classmethod
    def from_config(cls, config: dict[str, CONF]) -> 'NamelistHandler':
        cls.validate_config(config)
        input_path = config['input_path']
        output_path = config['output_path']
        override_configs = config['overrides']
        overrides = [NamelistOverride.from_config(oc) for oc in override_configs]
        return cls(input_path, output_path, overrides)

    def execute(self, wdir, **kwargs):
        wdir = pathlib.Path(wdir)

        if self._input_path.is_absolute():
            input_path = self._input_path
        else:
            input_path = wdir / self._input_path

        # Do nothing if the input namelist doesn't exist.
        if not input_path.exists():
            info(f"Namelist {input_path} doesn't exist.")
            return

        if self._output_path.is_absolute():
            output_path = self._output_path
        else:
            output_path = wdir / self._output_path

        debug(f"Modify namelist {input_path}.")
        namelist = f90nml.read(input_path)

        for override in self._overrides:
            override.apply(namelist)

        namelist.write(output_path, force=True)
