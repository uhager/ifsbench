from pathlib import Path

import xarray as xr

from ifsbench import GribFile


def _read_grib(input_path: str, short_name: str) -> xr.Dataset:
    ds = xr.open_dataset(
        input_path,
        engine='cfgrib',
        backend_kwargs={
            'filter_by_keys': {'shortName': short_name},
            'indexpath': '',
            'read_keys': ['packingError']
        })
    return ds


def _test_data_dir() -> Path:
    curr_path = Path(__file__).parent.resolve()
    return curr_path / 'gribfiles'

   
def test_get_stats_pressurelevels_single_dataset():
    input_path = _test_data_dir() / 'model_output_data_pl.grb2'

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

                
def test_get_stats_two_datasets():
    input_path = _test_data_dir() / 'model_output_data_rad.grb2'

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



            
