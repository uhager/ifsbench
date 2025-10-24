# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Type, Union

from pydantic import model_validator, TypeAdapter, Field
from pydantic_core.core_schema import ValidatorFunctionWrapHandler
from typing_extensions import Annotated, Literal

from ifsbench.config_mixin import PydanticConfigMixin
from ifsbench.data import DataHandler
from ifsbench.env import EnvHandler
from ifsbench.job import Job

__all__ = ['Application', 'DefaultApplication']


class Application(PydanticConfigMixin):
    """
    Base class for applications that can be launched.
    """

    # application_type is used to distinguish Application subclasses and has
    # to be defined in all subclasses.
    application_type: str

    _subclasses: ClassVar[Dict[str, Type[Any]]] = {}
    _discriminating_type_adapter: ClassVar[TypeAdapter]

    @model_validator(mode='wrap')
    @classmethod
    def _parse_into_subclass(
        cls, v: Any, handler: ValidatorFunctionWrapHandler
    ) -> 'Application':
        if cls is Application:
            return Application._discriminating_type_adapter.validate_python(v)
        return handler(v)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        Application._subclasses[cls.model_fields['application_type'].default] = cls
        Application._discriminating_type_adapter = TypeAdapter(
            Annotated[
                Union[tuple(Application._subclasses.values())],
                Field(discriminator='application_type'),
            ]
        )

    @abstractmethod
    def get_data_handlers(self, run_dir: Path, job: Job) -> List[DataHandler]:
        """
        Return necessary data handlers.

        Return all application-specific handler objects that must be run before
        launching the executable.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[DataHandler]:
            List of DataHandler objects.
        """
        return NotImplemented

    @abstractmethod
    def get_env_handlers(self, run_dir: Path, job: Job) -> List[EnvHandler]:
        """
        Return necessary environment handlers.

        Return all application-specific environment handler objects that are
        needed for launching the executable.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[EnvHandler]:
            List of EnvHandler objects.
        """
        return NotImplemented

    @abstractmethod
    def get_library_paths(self, run_dir: Path, job: Job) -> List[Path]:
        """
        Return necessary library paths.

        Return all library paths that are required to launch this executable.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[pathlib.Path]:
            List of the library paths.
        """
        return NotImplemented

    @abstractmethod
    def get_command(self, run_dir: Path, job: Job) -> List[str]:
        """
        Return the corresponding command.

        Parameters
        ----------
        run_dir: :any:`pathlib.Path`
            The working directory from where the executable will be launched.
        job: Job
            The parallel job setup.

        Returns
        -------
        list[str]:
            The command and (if necessary) corresponding flags.
        """
        return NotImplemented


class DefaultApplication(Application):
    """
    Default application implementation.

    Simple implementation of the application class where all returned data is
    static and doesn't depend on the ``run_dir`` or ``job`` parameters.

    Parameters
    ----------
    command: list[str]
        The command that corresponds to this application.
    data_handlers: list[DataHandler]
        The DataHandler list that is returned by get_data_handlers.
    env_handlers: list[EnvHandler]
        The EnvHandler list that is returned by get_env_handlers.
    library_paths: list[pathlib.Path]
        The library path list that is returned by get_library_paths.
    """

    application_type: Literal['DefaultApplication'] = 'DefaultApplication'

    command: List[str]
    data_handlers: List[DataHandler] = Field(default_factory=list)
    env_handlers: List[EnvHandler] = Field(default_factory=list)
    library_paths: List[Path] = Field(default_factory=list)

    def get_data_handlers(self, run_dir: Path, job: Job) -> List[DataHandler]:
        del run_dir, job  # Unused
        return list(self.data_handlers)

    def get_env_handlers(self, run_dir: Path, job: Job) -> List[EnvHandler]:
        del run_dir, job  # Unused
        return list(self.env_handlers)

    def get_library_paths(self, run_dir: Path, job: Job) -> List[Path]:
        del run_dir, job  # Unused
        return list(self.library_paths)

    def get_command(self, run_dir: Path, job: Job) -> List[str]:
        del run_dir, job  # Unused
        return list(self.command)
