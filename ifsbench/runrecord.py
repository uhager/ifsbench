from pathlib import Path
from collections import OrderedDict
import pandas as pd
import json

from ifsbench.logging import debug, info, warning, success, error
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

    def __init__(self, timestamp, norms, drhook=None, comment=None):
        self.timestamp = timestamp
        self.comment = comment

        self.norms = norms
        self.drhook = drhook

    def __repr__(self):
        s = 'RunRecord::\n'
        s += '    timestamp: %s\n%s' % (self.timestamp)
        s += '    comment: %s\n%s' % (self.comment, self.norms)
        return s

    def to_dict(self, orient='index'):
        """
        Return content of this `RunRecord` as a single Python dictionary.
        """
        d = self.metadata.copy()
        d['norms'] = self.norms.to_dict(orient=orient)
        d['drhook'] = self.drhook.to_dict(orient=orient)
        return d

    @property
    def metadata(self):
        return OrderedDict([
            ('comment', str(self.comment)),
            ('timestamp', str(self.timestamp)),
        ])

    @classmethod
    def from_run(cls, nodefile, comment=None, drhook=None):
        """
        Create a `RunRecord` object from the output of a benchamrk run.

        :param nodefile: Path to "NODE_xxx" file to read norms and metadata from.
        :param comment: (Optional) comment to store with this record
        :param drhook: (Optional) basepath (glob expression) for DrHook output files
        """

        # Currently we assume we always get some NODE file output
        nodefile = NODEFile(Path(nodefile))

        if drhook is not None:
            drhook = DrHookRecord.from_raw(drhook)

        return RunRecord(timestamp=nodefile.timestamp, norms=nodefile.norms,
                         drhook=drhook, comment=comment)

    @classmethod
    def from_file(cls, filepath, mode='json', orient='index'):
        """
        Load a stored benchmark result from file
        """
        filepath = Path(filepath)

        if mode == 'json':
            with filepath.with_suffix('.json').open('r') as f:
                data = json.load(f)

            # Read and normalize norms
            norms = pd.DataFrame.from_dict(data['norms'], orient=orient)
            for c in norms.columns:
                norms[c] = pd.to_numeric(norms[c])
            norms.set_index('step', inplace=True)

            drhook = DrHookRecord.from_dict(data=data['drhook']['data'],
                                            metadata=data['drhook']['metadata'],
                                            orient=orient)

            return RunRecord(timestamp=data['timestamp'], comment=data['comment'],
                             norms=norms, drhook=drhook)

        if mode == 'hdf5':
            # TODO: Warning untested!
            filepath = filepath.with_suffix('.h5')
            with pd.HDFStore(filepath) as store:
                norms, metadata = _h5load(store, 'norms')
            return RunRecord(timestamp=metadata['timestamp'],
                             comment=metadata['comment'], norms=norms)

        if mode == 'csv':
            # TODO: Warning untested!
            drhook = None
            if (filepath/'drhook.csv').exists():
                drhook = DrHookRecord.from_file(filepath)

            norms = pd.read_csv(filepath.with_suffix('.norms.csv'), float_precision='round_trip')
            with filepath.with_suffix('.meta.json').open('r') as f:
                metadata = json.loads(f.read())
            return RunRecord(timestamp=metadata['timestamp'],
                             comment=metadata['comment'], norms=norms, drhook=drhook)

    def write(self, filepath, comment=None, mode='json', orient='index'):
        """
        Write a benchmark result to file
        """
        if comment is not None:
            self.comment = comment

        filepath = Path(filepath)

        if mode == 'json':
            with filepath.with_suffix('.json').open('w') as f:
                json.dump(self.to_dict(orient=orient), f, indent=4)

        if mode == 'hdf5':
            # TODO: Warning untested!
            _h5store(filepath.with_suffix('.h5'), 'norms', df=self.norms, **self.metadata)

        if mode == 'csv':
            # TODO: Warning untested!
            self.norms.to_csv(filepath.with_suffix('.norms.csv'))
            with filepath.with_suffix('.meta.json').open('w') as f:
                f.write(json.dumps(self.metadata))

        if self.drhook is not None and mode != 'json':
            self.drhook.write(filepath)

    def compare_fields(self, reference):
        """
        Compare fields against reference record.

        :param reference: A second `RunRecord` object to compare against
        """
        for field in ['log_prehyds', 'vorticity', 'divergence', 'temperature', 'kinetic_energy']:
            equal = (reference.norms[field] == self.norms[field]).all()
            if not equal:
                error('FAILURE: Norm of field "%s" deviates from reference:' % field)
                analysis = pd.DataFrame({
                    'Result': reference.norms[field],
                    'Reference': self.norms[field],
                    'Difference': reference.norms[field] - self.norms[field],
                })
                info('\nField: %s\n%s' % (field, analysis))
                return False

        return True

    def validate(self, refpath, exit_on_error=False):
        """
        Validate record against stored reference result based on norms-checking

        :param refpath: Path to reference record
        :param exit_on_error: Fail script with `exit(-1)` if records don't match
        """

        try:
            debug('Validating results against reference in %s' % refpath)
            reference = self.from_file(filepath=refpath)
            is_valid = self.compare_fields(reference)

            if is_valid:
                success('VALIDATED: Result matches reference in %s' % (refpath))
                return True
            else:
                if exit_on_error:
                    exit(-1)
                else:
                    return False

        except FileNotFoundError:
            warning('Reference not found: %s Skipping validation...' % refpath)
