"""
Test :any:`IFS` and adjacent classes
"""
import datetime
import pandas as pd
from pathlib import Path
import pytest
from ifsbench import NODEFile

    
def nodelist_path():
    """Return the path to the nodefiles directory."""
    main_path = Path(__file__).parent.resolve()

    return main_path/'nodefiles'


@pytest.fixture
def all_nodelists():
    return (
        nodelist_path/'nodefile_default',
        nodelist_path/'nodefile_pred_corr'
    )

@pytest.mark.parametrize(
    'node_path,timestamp',
    (
        (nodelist_path()/'nodefile_default', datetime.datetime(2022, 12, 8, 10, 40, 51)),
        (nodelist_path()/'nodefile_pred_corr', datetime.datetime(2022, 12, 8, 10, 40, 51)),
    )
)
def test_nodefile_timestamp(node_path, timestamp):
    """
    Test that the output of the "timestamp" method matches the timestamp in the
    nodefile. 
    """
    nodefile = NODEFile(node_path)

    assert nodefile.timestamp == timestamp

@pytest.mark.parametrize(
    'node_path,nrows, ncolumns',
    (
        (nodelist_path()/'nodefile_default', 26, 5),
        (nodelist_path()/'nodefile_pred_corr', 26, 10),
    )
)
def test_spectral_norms(node_path, nrows, ncolumns):
    """
    Test the spectral_norms property against some reference values.
    """
    nodefile = NODEFile(node_path)

    norms = nodefile.spectral_norms

    # Verify that we get a pandas DataFrame and not something else.
    assert type(norms) == pd.DataFrame

    # For the moment, just compare the shape of the DataFrame to some reference
    # values. In the future, we should probably test against the actual values.
    assert norms.shape == (nrows, ncolumns)

@pytest.mark.parametrize(
    'node_path,nrows, ncolumns',
    (
        (nodelist_path()/'nodefile_default', 26, 24),
        (nodelist_path()/'nodefile_pred_corr', 26, 24),
    )
)
def test_grid_norms(node_path, nrows, ncolumns):
    nodefile = NODEFile(node_path)

    norms = nodefile.gridpoint_norms

    assert type(norms) == pd.DataFrame

    assert norms.shape == (nrows, ncolumns)

      
