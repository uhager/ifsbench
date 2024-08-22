from pathlib import Path
import pytest

from ifsbench import gribfile
from ifsbench import GribFile


@pytest.fixture(name='here')
def fixture_here():
    """Return the full path of the test directory"""
    return Path(__file__).parent.resolve() / 'gribfiles'

   
@pytest.mark.skipif(not gribfile.CFGRIB_AVAILABLE, reason='could not import cfgrib, likely missing eccodes.')
def test_get_stats_pressurelevels_single_dataset(here):
    input_path = here / 'model_output_data_pl.grb2'

    gf = GribFile(input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 1
    
    df = dfs[0]
    # shape ((2step x 2 level x 7 stats), (time, valid_time, u, v))
    assert df.shape == (28, 4) 
    assert sorted(list(df.columns)) == sorted(['time', 'valid_time', 'u', 'v'])

    # Sanity check relative values
    ds = df.to_xarray()
    for data_var in ['u', 'v']:
        for s in ds.step:
            for p in ds.isobaricInhPa:
                print(f'{data_var} - {s} - {p}')
                d = ds[data_var].sel(step=s, isobaricInhPa=p)
                assert d.sel(stat='min') < d.sel(stat='p5') < d.sel(stat='p10') < d.sel(stat='mean') < d.sel(stat='p90') < d.sel(stat='p95') < d.sel(stat='max')

                
@pytest.mark.skipif(not gribfile.CFGRIB_AVAILABLE, reason='could not import cfgrib, likely missing eccodes.')
def test_get_stats_two_datasets(here):
    input_path = here / 'model_output_data_rad.grb2'

    gf = GribFile(input_path)
    dfs = gf.get_stats()

    assert len(dfs) == 2
    
    df = dfs[0]
    # shape ((2step x 7 stats), (time, valid_time, nominalTop, ttr))
    assert df.shape == (14, 4) 
    assert sorted(list(df.columns)) == sorted(['time', 'valid_time', 'ttr', 'nominalTop'])

    # Sanity check relative values
    ds = df.to_xarray()
    for s in ds.step:
            d = ds['ttr'].sel(step=s)
            assert d.sel(stat='min') < d.sel(stat='p5') < d.sel(stat='p10') < d.sel(stat='mean') < d.sel(stat='p90') < d.sel(stat='p95') < d.sel(stat='max')

    df = dfs[1]
    # shape ((2step x 7 stats), (time, valid_time, nominalTop, ssr))
    assert df.shape == (14, 4) 
    assert sorted(list(df.columns)) == sorted(['time', 'valid_time', 'ssr', 'surface'])

    # Sanity check relative values
    ds = df.to_xarray()
    for s in ds.step:
        d = ds['ssr'].sel(step=s)
        assert d.sel(stat='min') <= d.sel(stat='p5') <= d.sel(stat='p10') < d.sel(stat='mean') < d.sel(stat='p90') < d.sel(stat='p95') <= d.sel(stat='max')


@pytest.mark.skipif(not gribfile.CFGRIB_AVAILABLE, reason='could not import cfgrib, likely missing eccodes.')
def test_get_stats_unknown_stat_raises(here):
    stat_names = gribfile._STAT_NAMES
    input_path = here / 'model_output_data_rad.grb2'
    gf = GribFile(input_path)

    gribfile._STAT_NAMES =  ['x90']

    with pytest.raises(ValueError):
        gf.get_stats()

    gribfile._STAT_NAMES = stat_names


@pytest.mark.skipif(not gribfile.CFGRIB_AVAILABLE, reason='could not import cfgrib, likely missing eccodes.')
def test_get_stats_keeps_stats(here):
    input_path = here / 'model_output_data_pl.grb2'
    gf = GribFile(input_path)
    dfs = gf.get_stats()

    df_ret = dfs[0]
    df_kept = gf._stats[0]

    assert df_ret is df_kept
