from pathlib import Path
import pandas as pd
import pytest

from ifsbench import DarshanReport


@pytest.fixture(scope='module', name='here')
def fixture_here():
    return Path(__file__).parent


def test_darshanreport_from_parser_log(here):
    """Verify that darshan-parser log is read correctly."""
    report = DarshanReport(here/'darshan.log')

    # Records loaded and available?
    assert len(report.records) == 3
    for module, count in {'POSIX': 16362, 'STDIO': 8904, 'LUSTRE': 1322}.items():
        assert isinstance(report.records[module], pd.DataFrame)
        assert isinstance(report.name_records[module], dict)
        assert len(report.records[module]) == count

    # Anything else raises an exception?
    with pytest.raises(KeyError):
        _ = report.records['foo']
    with pytest.raises(KeyError):
        _ = report.name_records['foo']
