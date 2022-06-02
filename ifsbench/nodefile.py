import re
from pathlib import Path
from datetime import datetime
import pandas as pd


__all__ = ['NODEFile']


class NODEFile:
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

    # Captures generic block of field norms per timestep
    sre_tstep_norms = sre_header_norms + r'(?P<norms>.*?)NSTEP.*?STEPO'
    re_tstep_norms = re.compile(sre_tstep_norms, re.MULTILINE | re.DOTALL)

    # Individual gridpoint norm entries (per field)
    sre_gp_norms = fr'GPNORM\s*(?P<field>{sre_name})\s*AVERAGE\s*MINIMUM\s*MAXIMUM\s*AVE\s*'
    sre_gp_norms += fr'(?P<avg>{sre_number})\s*(?P<min>{sre_number})\s*(?P<max>{sre_number})'
    re_gp_norms = re.compile(sre_gp_norms, re.MULTILINE)

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.content = self.filepath.read_text(encoding='utf-8')

    @property
    def timestamp(self):
        """
        Timestamp of the run that produced this NODE file.
        """
        match = self.re_timestamp.search(self.content)
        return datetime.strptime(f"{match.group('date')} {match.group('time')}", '%Y-%m-%d %H:%M:%S')

    @property
    def spectral_norms(self):
        """
        Timeseries of spectral norms as recorded in the logfile
        """
        entries = [m.groupdict() for m in self.re_sp_norms.finditer(self.content)]
        data = pd.DataFrame(entries)
        data['step'] = pd.to_numeric(data['step'])
        data.set_index('step', inplace=True)

        # Ensure numeric values in data
        for c in data.columns:
            data[c] = pd.to_numeric(data[c])
        return data

    @property
    def gridpoint_norms(self):
        """
        Timeseries of spectral norms as recorded in the logfile
        """

        # Create a Dataframe for all fields per timestep from regexes
        data_raw = []
        for m in self.re_tstep_norms.finditer(self.content):
            step_match = m.groupdict()
            entries = [m.groupdict() for m in self.re_gp_norms.finditer(step_match['norms'])]
            for e in entries:
                e['step'] = step_match['step']
            data_raw += [pd.DataFrame(entries)]

        # Concatenate and sanitizes dataframes and create step-field mulit-index
        data = pd.concat(data_raw)
        data['step'] = pd.to_numeric(data['step'])
        data.set_index(['field', 'step'], inplace=True)
        for c in data.columns:
            data[c] = pd.to_numeric(data[c])

        return data
