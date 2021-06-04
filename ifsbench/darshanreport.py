"""
Darshan report parsing utilities.
"""
import io
import mmap
from contextlib import contextmanager
from pathlib import Path
import pandas as pd

from ifsbench.util import gettempdir, execute


__all__ = ['read_files_from_darshan', 'write_files_from_darshan', 'DarshanReport']


def read_files_from_darshan(report):
    """Obtain set of file names that are read according to POSIX and STDIO
    modules in the Darshan report"""
    prec = report.records['POSIX']
    preads = prec[(prec['<counter>'] == 'POSIX_READS') & (prec['<value>'] > 0)]
    srec = report.records['STDIO']
    sreads = srec[(srec['<counter>'] == 'STDIO_READS') & (srec['<value>'] > 0)]
    read_files = set(preads['<file name>']) | set(sreads['<file name>'])
    return read_files


def write_files_from_darshan(report):
    """Obtain set of file names that are written according to POSIX and STDIO
    modules in the Darshan report"""
    # Find all writes from modules POSIX and STDIO
    prec = report.records['POSIX']
    pwrites = prec[(prec['<counter>'] == 'POSIX_WRITES') & (prec['<value>'] > 0)]
    srec = report.records['STDIO']
    swrites = srec[(srec['<counter>'] == 'STDIO_WRITES') & (srec['<value>'] > 0)]
    write_files = set(pwrites['<file name>']) | set(swrites['<file name>'])
    return write_files


@contextmanager
def open_darshan_logfile(filepath):
    """
    Utility context manager to run darshan-parser on the fly if the given file
    path does not point to a darshan log text file.
    """
    filepath = Path(filepath)
    with filepath.open('rb') as logfile:
        is_parser_log = logfile.read(32).find(b'darshan log version:') != -1
    if not is_parser_log:
        logpath = gettempdir()/(filepath.stem + '.log')
        execute(['darshan-parser', str(filepath)], logfile=str(logpath))
        filepath = Path(logpath)
    try:
        logfile = filepath.open('r')
        report = mmap.mmap(logfile.fileno(), 0, prot=mmap.PROT_READ)
        yield report
    finally:
        logfile.close()


class DarshanReport:
    """
    Utility reader to parse the output of `darshan-parser`.

    This exists for compatibility reasons to emulate the behaviour of
    pydarshan's `DarshanReport` for Darshan versions prior to 3.3.

    Parameters
    ----------
    filepath : str or :any:`pathlib.Path`
        The file name of the log file with the output from `darshan-parser` or
        the runtime logfile produced by Darshan. If the latter is given,
        `darshan-parser` will be called to parse this and create the text
        output before reading.
    """

    def __init__(self, filepath):
        with open_darshan_logfile(filepath) as report:
            self._parse_report(report)

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
