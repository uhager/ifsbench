"""
Utilities for working with file system paths
"""

from enum import Enum, auto
import re

__all__ = ['SpecialRelativePath']


class SpecialRelativePath:
    """
    Define a search and replacement pattern for special input files
    that need to have a particular name or relative path

    It is essentially a wrapper for :any:`re.sub`.

    Parameters
    ----------
    pattern : str or :any:`re.Pattern`
        The search pattern to match a path against
    repl : str
        The replacement string to apply
    """

    def __init__(self, pattern, repl):
        if isinstance(pattern, str):
            self.pattern = re.compile(pattern)
        self.repl = repl

    class NameMatch(Enum):
        """
        Enumeration of available types of name matches

        Attributes
        ----------
        EXACT :
            Match the name exactly as is
        LEFT_ALIGNED :
            Match the name from the start but it can be followed
            by other characters
        RIGHT_ALIGNED :
            Match the name from the end but it can be preceded by
            other characters
        FREE :
            Match the name but allow for other characters before
            and after
        """
        EXACT = auto()
        LEFT_ALIGNED = auto()
        RIGHT_ALIGNED = auto()
        FREE = auto()

    @classmethod
    def from_filename(cls, filename, repl, match=NameMatch.FREE):
        r"""
        Create a :class:`SpecialRelativePath` object that matches
        a specific file name

        Parameters
        ----------
        filename : str
            The filename (or part of it) that should match
        repl : str
            The relative path to retrun. :data:`repl` can reference components
            of the matched path: original filename as ``\g<name>``, path
            without filename as ``\g<parent>``, matched part of the filename
            as ``\g<match>`` and parts of the filename before/after the
            matched section as ``\g<pre>``/``\g<post>``, respectively.
        match : :any:`SpecialRelativePath.NameMatch`, optional
            Determines if the file name should be matched exactly
        """
        pattern = r"^(?P<parent>.*?\/)?(?P<name>"
        if match in (cls.NameMatch.RIGHT_ALIGNED, cls.NameMatch.FREE):
            pattern += r"(?P<pre>[^\/]*?)"
        pattern += fr"(?P<match>{filename})"
        if match in (cls.NameMatch.LEFT_ALIGNED, cls.NameMatch.FREE):
            pattern += r"(?P<post>[^\/]*?)"
        pattern += r")$"
        return cls(pattern, repl)

    @classmethod
    def from_dirname(cls, dirname, repl, match=NameMatch.FREE):
        r"""
        Create a :class:`SpecialRelativePath` object that matches
        paths that have a certain subdirectory in their path

        Parameters
        ----------
        dirname : str
            The directory name (or part of it) that should match
        repl : str
            The relative path to retrun. :data:`repl` can reference components
            of the matched path: original dirname as ``\g<name>``, path
            without matched directory as ``\g<parent>``, matched part of the
            directory name as ``\g<match>``, path following the matched
            directory as ``\g<child>``, and parts of the directory name
            before/after the matched section as ``\g<pre>``/``\g<post>``,
            respectively.
        match : :any:`SpecialRelativePath.NameMatch`, optional
            Determines if the directory name should be matched exactly
        """
        pattern = r"^(?P<parent>.*?\/)?(?P<name>"
        if match in (cls.NameMatch.RIGHT_ALIGNED, cls.NameMatch.FREE):
            pattern += r"(?P<pre>[^\/]*?)"
        pattern += fr"(?P<match>{dirname})"
        if match in (cls.NameMatch.LEFT_ALIGNED, cls.NameMatch.FREE):
            pattern += r"(?P<post>[^\/]*?)"
        pattern += r")(?P<child>\/.*?)$"
        return cls(pattern, repl)

    def __call__(self, path):
        """
        Apply :any:`re.sub` with :attr:`SpecialRelativePath.pattern`
        and :attr:`SpecialRelativePath.repl` to :data:`path`
        """
        return self.pattern.sub(self.repl, str(path))
