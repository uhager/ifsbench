from pathlib import Path
from collections import OrderedDict
from enum import Enum, unique
import re
import pandas as pd
import numpy as np

from ifsbench.logging import debug

__all__ = ['DrHook', 'DrHookRecord']


@unique
class DrHook(Enum):
    """
    Enum class to provide environment presets for different DrHook modes.
    """

    OFF = 0
    PROF = 1

    __env_map__ = {
        OFF : {
            'DR_HOOK': '0',
        },
        PROF : {
            'DR_HOOK': '1',
            'DR_HOOK_IGNORE_SIGNALS': '0',
            'DR_HOOK_OPT': 'prof',
        }
    }

    @property
    def env(self):
        return self.__class__.__env_map__[self.value]


class DrHookRecord(object):
    """
    Class to encapsulate a DrHook performance record for a single benchmark run.
    """
    sre_number = r'[\w\-\+\.]+'
    sre_tag = r'[\w\(\)\*_-@]+'

    re_program = re.compile(r"program='(?P<program>.*)'")
    sre_walltime = r'Wall-time is (?P<walltime>%s) sec on proc#%s \((?P<nprocs>%s) procs, (?P<threads>%s) threads\)' % (
        sre_number, sre_number, sre_number, sre_number
    )
    re_walltime = re.compile(sre_walltime)
    sre_memory = r'Memory usage : %s MB (heap), %s MB (rss), %s MB (stack), %s MB (vmpeak), %s (paging)' % (
        sre_number, sre_number, sre_number, sre_number, sre_number
    )
    re_memory = re.compile(sre_memory)

    sre_row = r'(?P<id>%s) +(?P<percent>%s) +(?P<cumul>%s) +(?P<self>%s) +(?P<total>%s) +(?P<calls>%s)' \
              r' +%s +%s +(?P<routine>.*)' % (
                  sre_number, sre_number, sre_number, sre_number, sre_number, sre_number, sre_number, sre_number
              )
    re_row = re.compile(sre_row)

    def __init__(self, data, metadata):
        self.data = data
        self.metadata = metadata

    def to_dict(self, orient='index'):
        """
        Return content of this `RunRecord` as a single Python dictionary.
        """
        d = OrderedDict()
        d['metadata'] = self.metadata.to_dict(orient=orient)
        d['data'] = self.data.to_dict(orient=orient)
        return d

    def pprint(self):
        """
        Pretty-print content of the merged DrHook results.
        """
        s = 'The name of the executable : %s\n' % self.metadata['program']
        s += 'Number of MPI-tasks        : %s\n' % self.metadata['nprocs']
        s += 'Number of OpenMP-threads   : %s\n' % self.metadata['threads']
        s += 'Wall-times over %s MPI-tasks (secs) : Min=%.3f, Max=%.3f, Avg=%.3f, StDev=%.3f\n' % (
            self.metadata['nprocs'], self.metadata['mintime'], self.metadata['maxtime'],
            self.metadata['avgtime'], self.metadata['stdtime']
        )
        s += 'Routines whose total time (i.e. sum) > 0.010 secs will be included in the listing\n'
        s += '  Avg-%   Avg.time   Min.time   Max.time   St.dev  Imbal-%   # of calls : Name of the routine\n'
        for _, row in self.data.iterrows():
            s += ' %6.2f%%    %6.3f    %6.3f    %6.3f    %6.3f    %6.2f    %9.d : %s\n' % (
                row['avgPercent'], row['avgTime'], row['minTime'], row['maxTime'],
                row['stddev'], row['imbalance'], row['numCalls'], row['routine']
            )
        return s

    def write(self, filepath, orient='index'):
        """
        Write an aggregated benchmark result to file
        """
        filepath = Path(filepath)
        self.data.to_csv(filepath.with_suffix('.drhook.csv'))
        self.metadata.to_csv(filepath.with_suffix('.drhook.meta.csv'))

        # Pretty print a total for human consumption
        with filepath.with_suffix('.drhook.txt').open('w') as f:
            f.write(self.pprint())

    @classmethod
    def from_dict(cls, data, metadata, orient='index'):
        """
        Load DrHook output from dumped dictionaries into `pd.DataFrame`s
        """
        return DrHookRecord(data=pd.DataFrame.from_dict(data, orient=orient),
                            metadata=pd.DataFrame.from_dict(metadata, orient=orient))

    @classmethod
    def from_raw(cls, filepath):
        """
        Load raw drhook output and aggregate into merged performance record
        """
        filepath = Path(filepath)
        data, metadata = cls.parse_profiles(filepath)
        return DrHookRecord(data, metadata)

    @classmethod
    def from_file(cls, filepath):
        """
        Load a stored aggregated benchmark result from file
        """
        filepath = Path(filepath)
        data = pd.read_csv(filepath.with_suffix('.csv'), float_precision='round_trip')
        metadata = pd.read_csv(filepath.with_suffix('.meta.csv'), float_precision='round_trip')
        return DrHookRecord(data, metadata)

    @classmethod
    def parse_profiles(cls, filepath):
        """
        Parse the raw DrHook (per-process) profile files into a ``pandas.DataFrame``.
        """
        debug('Parsing DrHook profile: %s' % filepath)

        filepath = Path(filepath)
        columns = ['id', 'percent', 'cumul', 'self', 'total', 'calls', 'routine']

        dfs = []
        metas = []
        for path in filepath.parent.glob(filepath.name):
            with Path(path).open('r') as f:
                raw = f.read()

            # Parse metadata into series object
            # m = [m.groupdict() for m in cls.re_walltime.finditer(raw)]
            m = cls.re_program.search(raw).groupdict()
            m.update(cls.re_walltime.search(raw).groupdict())
            # m_memory = cls.re_walltime.search(raw)
            # m.update(m_memory if m_memory else {}}
            metas += [pd.Series(m).to_frame().transpose()]

            rows = [m.groups() for m in cls.re_row.finditer(raw)]
            df = pd.DataFrame(rows, columns=columns)
            df.set_index('id', inplace=True)

            # Extract the thread ID into individual column and drop '*'
            df['thread'] = df['routine'].apply(lambda n: int(n.split('@')[-1]))
            df['routine'] = df['routine'].apply(lambda n: n.split('@')[0].replace('*', ''))
            dfs += [df]

        # Concatenate all DrHook profiles
        data = pd.concat(dfs)
        meta = pd.concat(metas)

        # Provide across process statistics for metadata
        meta['walltime'] = pd.to_numeric(meta['walltime'], errors='coerce')
        meta['mintime'] = meta['walltime'].min()
        meta['maxtime'] = meta['walltime'].max()
        meta['avgtime'] = meta['walltime'].mean()
        meta['stdtime'] = meta['walltime'].std()

        meta.drop(['walltime'], axis=1, inplace=True)
        meta.drop_duplicates(inplace=True)

        # Clean up and sanity check values
        data['percent'] = pd.to_numeric(data['percent'].fillna(0), errors='coerce')
        data['cumul'] = pd.to_numeric(data['cumul'].fillna(0), errors='coerce')
        data['self'] = pd.to_numeric(data['self'].fillna(0), errors='coerce')
        data['total'] = pd.to_numeric(data['total'].fillna(0), errors='coerce')
        data['calls'] = pd.to_numeric(data['calls'].fillna(0), errors='coerce')

        # Normalize statistics across processes and threads
        grp = data.groupby(['routine'])
        data['avgPercent'] = grp['percent'].transform(np.mean)
        data['avgTime'] = grp['self'].transform(np.mean)
        data['minTime'] = grp['self'].transform(np.min)
        data['maxTime'] = grp['self'].transform(np.max)
        data['stddev'] = grp['self'].transform(np.std)
        data['avgTimeTotal'] = grp['total'].transform(np.mean)
        data['minTimeTotal'] = grp['total'].transform(np.min)
        data['maxTimeTotal'] = grp['total'].transform(np.max)
        data['numCalls'] = grp['calls'].transform(np.sum)
        data['cumulative'] = grp['cumul'].transform(np.max)
        data['thread'] = grp['thread'].transform(np.max)

        # Drop raw per-process/thread values and compute imbalance
        data.drop(['percent', 'self', 'total', 'cumul', 'calls'], axis=1, inplace=True)
        data.drop_duplicates(inplace=True)
        data['imbalance'] = (data['maxTime'] - data['minTime']) / data['maxTime'] * 100

        return data, meta
