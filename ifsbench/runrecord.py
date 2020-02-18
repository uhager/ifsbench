from pathlib import Path
import pandas as pd
import json

from ifsbench.logging import debug, info, error
from ifsbench.nodefile import NODEFile
from ifsbench.drhook import DrHookRecord


__all__ = ['RunRecord']


def _h5store(filename, key, df, **kwargs):
    """
    https://stackoverflow.com/questions/29129095/save-additional-attributes-in-pandas-dataframe/29130146#29130146
    """
    store = pd.HDFStore(filename)
    store.put(key, df)
    store.get_storer(key).attrs.metadata = kwargs
    store.close()


def _h5load(store, key):
    """
    https://stackoverflow.com/questions/29129095/save-additional-attributes-in-pandas-dataframe/29130146#29130146
    """
    data = store[key]
    metadata = store.get_storer(key).attrs.metadata
    return data, metadata


class RunRecord(object):
    """
    Class to encapsulate, store and load all metadata associated with
    an individual test or benchmark run.
    """

    def __init__(self, name, timestamp, norms, drhook=None, comment=None):
        self.name = name
        self.timestamp = timestamp
        self.comment = comment

        self.norms = norms
        self.drhook = drhook

    def __repr__(self):
        s = 'RunRecord: %s  :: %s\n' % (self.name, self.timestamp)
        s += '    comment: %s\n%s' % (self.comment, self.norms)
        return s

    @property
    def metadata(self):
        return {
            'name': self.name,
            'timestamp': str(self.timestamp),
            'comment': str(self.comment),
        }

    @classmethod
    def from_file(cls, filepath, mode='csv'):
        """
        Load a stored benchmark result from file
        """
        filepath = Path(filepath)
        if mode == 'hdf5':
            filepath = filepath.with_suffix('.h5')
            with pd.HDFStore(filepath) as store:
                norms, metadata = _h5load(store, 'norms')
            return RunRecord(name=metadata['name'], timestamp=metadata['timestamp'],
                             comment=metadata['comment'], norms=norms)

        if mode == 'csv':
            drhook = None
            if (filepath/'drhook.csv').exists():
                drhook = DrHookRecord.from_file(filepath)

            norms = pd.read_csv(filepath.with_suffix('.norms.csv'), float_precision='round_trip')
            with filepath.with_suffix('.meta.json').open('r') as f:
                metadata = json.loads(f.read())
            return RunRecord(name=metadata['name'], timestamp=metadata['timestamp'],
                             comment=metadata['comment'], norms=norms, drhook=drhook)

    def write(self, filepath, mode='csv'):
        """
        Write a benchmark result to file
        """
        filepath = Path(filepath)
        if mode == 'hdf5':
            _h5store(filepath.with_suffix('.h5'), 'norms', df=self.norms, **self.metadata)

        if mode == 'csv':
            self.norms.to_csv(filepath.with_suffix('.norms.csv'))
            with filepath.with_suffix('.meta.json').open('w') as f:
                f.write(json.dumps(self.metadata))

        if self.drhook is not None:
            self.drhook.write(filepath)

    def validate(self, nodefile):
        """
        Validate nodefile against stored result based on norms-checking
        """
        if not isinstance(nodefile, NODEFile):
            raise NotImplementedError('Can currently only validate against NODEFile objects')

        debug('%s: Validating results in %s', self.name, nodefile.filepath)

        for field in ['log_prehyds', 'vorticity', 'divergence', 'temperature', 'kinetic_energy']:
            equal = (nodefile.spectral_norms[field] == self.norms[field]).all()
            if not equal:
                error('FAILURE: Norm of field "%s" deviates from reference:' % field)
                analysis = pd.DataFrame({
                    'Result': nodefile.spectral_norms[field],
                    'Reference': self.norms[field],
                    'Difference': nodefile.spectral_norms[field] - self.norms[field],
                })
                info('\nField: %s\n%s' % (field, analysis))
                return False

        return True
