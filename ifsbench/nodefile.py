import re
from pandas import DataFrame, to_numeric
from pathlib import Path
from datetime import datetime


__all__ = ['NODEFile']


class NODEFile(object):
    """
    Utility reader to parse NODE.001_01 log files and extract norms.
    """

    sre_timestamp = r'Date :\s*(?P<date>[\d-]+)\s*Time :\s*(?P<time>[\d:]+)'
    re_timestamp = re.compile(sre_timestamp)

    sre_number = r'[\w\-\+\.]+'
    sre_name = r'[\w\(\)]+'

    sre_header_norms = r'NORMS AT NSTEP CNT4\s*(?P<step>[\d]+)\s*'
    sre_sp_norms = r'SPECTRAL NORMS -\s*' + sre_name + r'\s*(?P<log_prehyds>' + sre_number + r')+'
    sre_sp_norms += r'\s*LEV\s*VORTICITY\s*DIVERGENCE\s*TEMPERATURE\s*KINETIC ENERGY\s*'
    sre_sp_norms += r'AVE\s*(?P<vorticity>' + sre_number + r')\s*(?P<divergence>' + sre_number
    sre_sp_norms += r')\s*(?P<temperature>' + sre_number + r')\s*(?P<kinetic_energy>' + sre_number + r')'
    re_sp_norms = re.compile(sre_header_norms + sre_sp_norms, re.MULTILINE)

    # TODO: Extend to capture GP norms.
    # sre_gp_norms = r'GPNORM\s*\w+\s*AVERAGE\s*MINIMUM\s*MAXIMUM\s*AVE\s*[\w-+.]+\s*[\w-+.]+\s*[\w-+.]+'
    # sre_all_norms = r'NORMS AT NSTEP CNT4\s*(?P<tstep>[\d]+)\s*' + sre_sp_norms
    # re_all_norms = re.compile(sre_all_norms, re.MULTILINE)

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        with self.filepath.open() as f:
            self.content = f.read()

    @property
    def timestamp(self):
        """
        Timestamp of the run that produced this NODE file.
        """
        match = self.re_timestamp.search(self.content)
        return datetime.strptime('%s %s' % (match.group('date'), match.group('time')), '%Y-%m-%d %H:%M:%S')

    @property
    def spectral_norms(self):
        """
        Timeseries of spectral norms as recorded in the logfile
        """
        entries = [m.groupdict() for m in self.re_sp_norms.finditer(self.content)]
        data = DataFrame(entries)

        # Ensure numeric values in data
        for c in data.columns:
            data[c] = to_numeric(data[c])
        return data

    @property
    def norms(self):
        """
        `pandas.Dataframe` object containing all norms extracted from this NODE file.
        """
        # TODO: Add more norms and concatenate DataFrames
        return self.spectral_norms
