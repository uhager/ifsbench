# (C) Copyright 2024- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import re
from pathlib import Path
from datetime import datetime
import pandas as pd


__all__ = ['NODEFile']


class NODEFile:
    """
    Utility reader to parse NODE.001_01 log files and extract norms.
    """

    # Regex to extract the data from a nodefile.
    sre_timestamp = r'Date :\s*(?P<date>[\d-]+)\s*Time :\s*(?P<time>[\d:]+)'
    re_timestamp = re.compile(sre_timestamp)

    # Regex for floating point numbers.
    sre_number = r'[\w\-\+\.]+'

    # Regex for property names.
    sre_name = r'[\w\(\)\s]+'

    # Regex for parsing a "SPECTRAL NORMS" block. It returns three groups:
    # * log_prehyds: Holds the log_prehyds value.
    # * headers: Whitespace separated string that holds the name of the
    #   properties that are stored.
    # * values: Whitespace separated string that holds the corresponding
    #   values.
    sre_sp_norms = r'SPECTRAL NORMS -\s*' + sre_name + r'\s*(?P<log_prehyds>'
    sre_sp_norms += sre_number + r')+\s*LEV'
    sre_sp_norms += r'(?P<headers>.*?)AVE'
    sre_sp_norms += r'(?P<values>[0-9Ee\-\+\.\s]+)'
    re_sp_norms = re.compile(sre_sp_norms, re.MULTILINE | re.DOTALL)

    # Regex for parsing a single gridpoint norm block.
    sre_gp_norms = fr'GPNORM\s*(?P<field>{sre_name})\s*AVERAGE\s*MINIMUM\s*MAXIMUM\s*AVE\s*'
    sre_gp_norms += fr'(?P<avg>{sre_number})\s*(?P<min>{sre_number})\s*(?P<max>{sre_number})'
    re_gp_norms = re.compile(sre_gp_norms, re.MULTILINE)

    # Each result block in the node file starts with "NORMS AT NSTEP CNT4",
    # followed by a block name (optional) and the step index (required).
    # As far as I can see it, a block, always ends with a line that starts with
    # "NSTEP".
    it_str = r'NORMS AT NSTEP (.*?)\s+(\d+)(.*?)NSTEP'
    re_it_str = re.compile(it_str, re.MULTILINE | re.DOTALL)

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

    def _iterate_step_data(self):
        """
        Each nodefile stores the results at the different time steps.
        Additionally, there may be different "groups" for each time step (for
        example results for the predictor/corrector or just "standard" data).

        This function yields tuples of the type (group name, step index,
        content).
        """
        # Use the re_it_str regex to find all step blocks. This returns a tuple
        # that contains (group name, step index, block content).
        matches = self.re_it_str.findall(self.content)

        for group_name, step, content in matches:
            # Strip the group name of all whitespaces and parenthesis.
            group_name = group_name.strip(' ()')
            step = int(step)
            content = content.strip()

            yield group_name, step, content

    @staticmethod
    def _construct_dataframe(raw_data, default_value=0):
        """
        Build a dataframe from a dict of <step index, data dict> pairs. All
        not-specified values are set to the default_value.
        This is necessary, as pandas sets unspecified values to NaN which may
        cause major problems when validating results.
        """

        # Create the data frame from the actual data.
        data = pd.DataFrame(raw_data.values())

        # If the DataFrame is empty, return now as some of the subsequent steps
        # may fail in this case.
        if data.empty:
            return data

        for c in data.columns:
            data[c] = pd.to_numeric(data[c])

        data.set_index('step', inplace=True)

        # Find non-assigned values in the dataframe.
        isna = data.isna()

        # Set all non-assigned values to the default value.
        data.mask(isna, default_value, inplace=True)

        return data

    @staticmethod
    def _sanitise_float(value):
        # Unfortunately we need this hack. IFS sometimes outputs
        # floating point numbers in a non-standard exponential way,
        # writing 0.1-2 instead of 0.1e-2. Python can't parse the
        # former. Therefore we do a little check here to detect values
        # that contain a "-" but no "e".
        if '-' in value and ('e' not in value.lower()) and not value.startswith("-"):
            value = value.replace('-', 'e-')
        return value

    @property
    def spectral_norms(self):
        """
        Return the spectral norms that are stored in the logfile as a
        pandas.DataFrame object.

        Each row of the DataFrame corresponds to a single timestep whereas each
        columns corresponds to a property.
        """

        # Initially, we use a dict that maps from time steps to the
        # corresponding data.
        raw_data = {}

        # Iterate over all data blocks in the node file.
        for group_name, step, content in self._iterate_step_data():

            # Try to look for spectral norm data in the current data block.
            match = self.re_sp_norms.search(content)
            if match is None:
                continue


            # If no data exists yet for the timestep, create a new dictionary
            # for it, which also holds the timestep
            if step not in raw_data:
                raw_data[step] = {'step': step}


            # Check if the block has a name or not. If it does, create a prefix
            # that is added to all stored properties.
            if group_name:
                prefix = group_name + '_'
            else:
                prefix = ''

            # Split the headers where there are at least two whitespaces (some
            # property names include a single whitespace but two properties are
            # usually separated by multiple whitespaces).
            headers = re.split(r'\s{2,}', match['headers'].strip())
            values = re.split(r'\s+', match['values'].strip())

            # Add the key/value pairs to the actual data dict.
            for name, value in zip(headers, values):
                raw_data[step][prefix+name] = self._sanitise_float(value)

            raw_data[step][prefix+'log_prehyds'] = self._sanitise_float(
                match['log_prehyds'])

        data = self._construct_dataframe(raw_data, default_value=0)

        return data

    @property
    def gridpoint_norms(self):
        """
        Timeseries of spectral norms as recorded in the logfile
        """

        # Initially, we use a dict that maps from time steps to the
        # corresponding data.
        raw_data = {}

        # Iterate over all data blocks in the node file.
        for group_name, step, content in self._iterate_step_data():

            # Each data block may contain different grid point properties
            # (humidity, snow, rain, ...). Parse each of them.
            entries = [m.groupdict() for m in self.re_gp_norms.finditer(content)]

            if step not in raw_data:
                raw_data[step] = {'step': step}

            row_data = {}

            # Loop over all grid point properties. Each grid point property
            # usually  holds several values (min, max, average). Each such
            # value should end up in a separate column of the data frame (e.g.
            # the average rain value should end up in the "RAIN avg" column.
            for entry in entries:
                # Get the name of the current value (and strip all still
                # remaining whitespaces).
                name = entry.pop('field').strip()

                # Prepend the name by the name of the group
                # (predictor/corrector/nothing) if applicable.
                if group_name:
                    prefix=f"{group_name}_{name} "
                else:
                    prefix=f"{name} "

                for key, value in entry.items():
                    row_data[prefix+key] = self._sanitise_float(value)

            # Combine the previous data for timestep "step" with the data that
            # was just read.
            raw_data[step] = {**raw_data[step], **row_data}

        data = self._construct_dataframe(raw_data, default_value=0)

        return data
