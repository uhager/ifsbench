"""
Darshan report parsing utilities.
"""
import io
import mmap
import subprocess
from pathlib import Path
import pandas as pd


__all__ = ['DarshanReport']


class DarshanReport:
    """
    Utility reader to parse the output of `darshan-parser`.

    This exists for compatibility reasons to emulate the behaviour of
    pydarshan's `DarshanReport` for Darshan versions prior to 3.3.

    Either :attr:`parser_log` or :attr:`darshan_log` have to be provided.

    Parameters
    ----------
    parser_log : str or :any:`pathlib.Path`
        The file name of the log file with the output from `darshan-parser`.
    darshan_log : str or :any:`pathlib.Path`
        The file name of the runtime logfile produced by Darshan. When given,
        `darshan-parser` will be used to parse this and create the
        :attr:`parser_log` on the fly. If :attr:`parser_log` is given this
        will be ignored.
    """

    def __init__(self, parser_log=None, darshan_log=None):
        if parser_log is None:
            if darshan_log is None:
                raise ValueError('darshan_log or parser_log must be provided.')
            self._parse_report(self._from_darshan_parser(darshan_log))
        else:
            parser_log = Path(parser_log)
            with parser_log.open('r') as logfile:
                report = mmap.mmap(logfile.fileno(), 0, prot=mmap.PROT_READ)
                self._parse_report(report)

    @staticmethod
    def _from_darshan_parser(darshan_log):
        path = Path(darshan_log)
        cmd = 'darshan-parser'
        result = subprocess.run([cmd, str(path)], capture_output=True, check=True)
        return result.stdout

    @staticmethod
    def _parse_key_values(report, start, end):
        pairs = {}
        for line in report[start:end].splitlines():
            line = line.decode()
            if not line.startswith('# ') or ': ' not in line:
                # skip empty/decorative lines
                continue
            key, value = line[1:].split(': ', maxsplit=1)
            key, value = key.strip(), value.strip()
            if key in pairs:
                pairs[key] = pairs[key] + ', ' + value
            else:
                pairs[key] = value
        return pairs

    def _parse_report(self, report):
        #report = report.decode()

        # Get log version
        ptr = report.find(b'darshan log version:')
        line_start = report.find(b'\n', ptr)
        self.version = report[ptr + len(b'darshan log version:'):line_start].strip()

        # Find output regions
        start_regions = report.find(b'log file regions')
        start_mounts = report.find(b'mounted file systems')
        start_columns = report.find(b'description of columns')

        # Find module outputs
        modules = []
        end = start_columns
        ptr = report.find(b' module data', end)
        while ptr != -1:
            start = report.rfind(b'\n#', 0, ptr)
            module_name = report[start+2:ptr].strip().decode()
            table_start = report.find(b'#<module>', ptr)
            end = report.find(b'\n\n', table_start)
            modules += [(module_name, start, table_start, end)]
            ptr = report.find(b' module data', end)

        # Parse key-value regions
        self.header = self._parse_key_values(report, 0, start_regions)
        self.logfile_regions = self._parse_key_values(report, start_regions, start_mounts)
        self.file_systems = self._parse_key_values(report, start_mounts, start_columns)
        self.columns = self._parse_key_values(report, start_columns, modules[0][1])

        # Parse modules
        self._records = {}
        self._name_records = {}
        for module, start, table_start, end in modules:
            desc_start = report.find(b'description of', start)
            self._name_records[module] = self._parse_key_values(report, desc_start, table_start)
            module_record = io.StringIO(report[table_start:end].decode())
            self._records[module] = pd.read_csv(module_record, sep='\t', index_col=False)

    @property
    def records(self):
        """
        Return a `dict` of :any:`pandas.DataFrame` containing all records.

        See the `documentation of darshan-parser output
        <https://www.mcs.anl.gov/research/projects/darshan/docs/darshan-util.html#_guide_to_darshan_parser_output>`_
        for available modules and the meaning of record fields.

        Returns
        -------
        `dict` of `pandas.DataFrame`
            Dictionary of module name to DataFrame mappings.
        """
        return self._records

    @property
    def name_records(self):
        """
        Return a `dict` of columns names and their descriptions for each module.

        Returns
        -------
        `dict` of `dict`
            Column descriptions for each module.
        """
        return self._name_records
