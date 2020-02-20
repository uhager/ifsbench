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

    def __init__(self, timestamp, spectral_norms=None, gridpoint_norms=None,
                 drhook=None, comment=None):
        self.timestamp = timestamp
        self.comment = comment

        self.spectral_norms = spectral_norms
        self.gridpoint_norms = gridpoint_norms
        self.drhook = drhook

    def __repr__(self):
        s = 'RunRecord::\n'
        s += '    timestamp: %s\n%s' % (self.timestamp)
        s += '    comment: %s\n%s' % (self.comment, self.sp_norms)
        return s

    def to_dict(self, orient='list'):
        """
        Return content of this `RunRecord` as a single Python dictionary.
        """
        d = self.metadata.copy()
        d['spectral_norms'] = self.spectral_norms.to_dict(orient=orient)

        # Encode gridpoint norms by taking cross-sections of each field
        fields = self.gridpoint_norms.index.unique(level=0)
        d['gridpoint_norms'] = OrderedDict({
            field: self.gridpoint_norms.xs(field).to_dict(orient=orient) for field in fields
        })

        if self.drhook is not None:
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

        return RunRecord(timestamp=nodefile.timestamp, spectral_norms=nodefile.spectral_norms,
                         gridpoint_norms=nodefile.gridpoint_norms, drhook=drhook, comment=comment)

    @classmethod
    def from_file(cls, filepath, mode='json', orient='columns'):
        """
        Load a stored benchmark result from file
        """
        filepath = Path(filepath)

        if mode == 'csv':
            return cls.from_hdf5(filepath=filepath)
        if mode == 'json':
            return cls.from_json(filepath=filepath.with_suffix('.json'), orient=orient)
        if mode == 'hdf5':
            return cls.from_hdf5(filepath=filepath.with_suffix('.hdf5'))

    @classmethod
    def from_hdf5(cls, filepath):
        """
        Load a stored benchmark result from a .csv file

        TODO: Warning this is currently untested!
        """
        with pd.HDFStore(filepath) as store:
            norms, metadata = _h5load(store, 'norms')

        return RunRecord(timestamp=metadata['timestamp'],
                         comment=metadata['comment'], norms=norms)

    @classmethod
    def from_csv(cls, filepath):
        """
        Load a stored benchmark result from a .csv file

        TODO: Warning this is currently untested!
        """
        drhook = None
        if (filepath/'drhook.csv').exists():
            drhook = DrHookRecord.from_file(filepath)

        norms = pd.read_csv(filepath.with_suffix('.norms.csv'), float_precision='round_trip')
        with filepath.with_suffix('.meta.json').open('r') as f:
            metadata = json.loads(f.read())
        return RunRecord(timestamp=metadata['timestamp'],
                         comment=metadata['comment'], norms=norms, drhook=drhook)

    @classmethod
    def from_json(cls, filepath, orient='columns'):
        """
        Load a stored benchmark result from a JSON file
        """
        with filepath.with_suffix('.json').open('r') as f:
            data = json.load(f)

        # Read and normalize spectral norms
        spectral_norms = pd.DataFrame.from_dict(data['spectral_norms'], orient=orient)
        spectral_norms.index.rename('step', inplace=True)
        for c in spectral_norms.columns:
            spectral_norms[c] = pd.to_numeric(spectral_norms[c])

        # Read and normalize gridpoint norms by field
        gp_norms = []
        for field, norms in data['gridpoint_norms'].items():
            norms = pd.DataFrame().from_dict(norms, orient=orient)
            norms.index.rename('step', inplace=True)
            norms['field'] = field
            gp_norms += [norms]

        gridpoint_norms = pd.concat(gp_norms)
        gridpoint_norms.set_index(['field', gridpoint_norms.index], inplace=True)
        for c in gridpoint_norms.columns:
            gridpoint_norms[c] = pd.to_numeric(gridpoint_norms[c])

        drhook = None
        if 'drhook' in data:
            drhook = DrHookRecord.from_dict(data=data['drhook']['data'],
                                            metadata=data['drhook']['metadata'],
                                            orient=orient)

        return RunRecord(timestamp=data['timestamp'], comment=data['comment'], drhook=drhook,
                         spectral_norms=spectral_norms, gridpoint_norms=gridpoint_norms)

    def write(self, filepath, comment=None, mode='json', orient='list'):
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

    def compare_norms(self, result, reference, field='', norm='', exit_on_error=False):
        """
        Compare a single time series of norms

        :param result: Time series of norms in result data
        :param reference: Time series of norms in reference data
        :param field: Name of field that is being compared
        :param norm: Name of norm that is used for comparison
        :param exit_on_error: Flag to force immediate termination
        """
        if not (result == reference).all():
            error('FAILURE: Norm %s of field %s deviates from reference:' % (norm, field))
            analysis = pd.DataFrame({'Result': result, 'Reference': reference,
                                     'Difference': reference - result})
            info('\nField: %s\n%s' % (field, analysis))

            # Either soft-fail or return false
            if exit_on_error:
                exit(-1)
            else:
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

            # Validate all recorded spectral norms
            is_valid_sp = True
            for field in self.spectral_norms.columns:
                is_valid = self.compare_norms(
                    result=self.spectral_norms[field],
                    reference=reference.spectral_norms[field],
                    field=field, exit_on_error=exit_on_error
                )
                is_valid_sp = is_valid_sp and is_valid

            # Validate avg/min/max norms for all recorded gridpoint fields
            is_valid_gp = True
            for field in self.gridpoint_norms.index.unique(level=0):
                for norm in ['avg', 'min', 'max']:
                    is_valid = self.compare_norms(
                        result=self.gridpoint_norms.loc[(field, norm)],
                        reference=reference.gridpoint_norms.loc[(field, norm)],
                        field=field, norm=norm, exit_on_error=exit_on_error
                    )
                    is_valid_gp = is_valid_gp and is_valid

            if is_valid_sp and is_valid_gp:
                success('VALIDATED: Result matches reference in %s' % (refpath))
                return True
            else:
                if exit_on_error:
                    exit(-1)
                else:
                    return False

        except FileNotFoundError:
            warning('Reference not found: %s Skipping validation...' % refpath)
