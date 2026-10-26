from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261019
REGIMES = ('coal_first', 'gas_first', 'solar_rich')


def dispatch(residual, regime):
    """Synthetic continuous merit-order dispatch, kW -> kg CO2 per hour."""
    x = np.maximum(np.asarray(residual, dtype=float), 0)
    order = ((6000., .4), (6000., .95), (8000., .75)) if regime == 'gas_first' else (
        (6000., .95), (6000., .4), (8000., .75))
    emissions = np.zeros_like(x)
    marginal = np.zeros_like(x)
    remaining = x.copy()
    for cap, ef in order:
        gen = np.minimum(remaining, cap)
        emissions += gen * ef
        marginal = np.where(remaining > 1e-8, ef, marginal)
        remaining -= gen
    if np.max(remaining, initial=0) > 1e-6:
        raise ValueError('Synthetic upstream fleet cannot supply required service')
    return emissions, marginal


def prepare(seed=SEED, save=True):
    out = ROOT / 'data'
    out.mkdir(exist_ok=True)
    folder = ROOT.parent / 'Hengsha_Hybrid_Storage_Research' / 'data' / 'NASA_POWER'
    snapshot = out / 'weather'
    if snapshot.exists():
        folder=snapshot
    else:
        # Preserve exact selected source versions within the reproducible project.
        for sub in ('processed','metadata','raw'):
            (snapshot/sub).mkdir(parents=True,exist_ok=True)
        for year in range(2021,2026):
            for sub,extension in (('processed','csv'),('metadata','json'),('raw','json')):
                suffix='_UTC' if sub=='processed' else ''
                name=f'POWER_Hengsha_reference_{year}{suffix}.{extension}'
                shutil.copyfile(folder/sub/name,snapshot/sub/name)
        folder=snapshot
    parts, sources = [], []
    for year in range(2021, 2026):
        name = f'POWER_Hengsha_reference_{year}_UTC.csv'
        path = folder / 'processed' / name
        meta_path = folder / 'metadata' / f'POWER_Hengsha_reference_{year}.json'
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        raw = folder / Path(meta['raw_file'].replace('\\', '/'))
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == meta['raw_sha256']
        df = pd.read_csv(path)
        parts.append(df)
        sources.append({'file':str(path.relative_to(ROOT.parent)),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'raw_sha256':meta['raw_sha256'], 'request_url':meta['request_url'],
            'metadata_file':str(meta_path.relative_to(ROOT.parent))})
    weather = pd.concat(parts, ignore_index=True)
    idx = pd.to_datetime(weather.timestamp_utc, utc=True)
    assert not idx.duplicated().any()
    assert (idx.diff().dropna() == pd.Timedelta(hours=1)).all()
    ghi = weather.GHI_hourly_mean_W_m2.to_numpy()
    assert np.isfinite(ghi).all() and (ghi >= 0).all()
    local = idx.dt.tz_convert('Asia/Shanghai')
    hour, doy = local.dt.hour.to_numpy(), local.dt.dayofyear.to_numpy()
    rng = np.random.default_rng(seed)
    innovation = rng.normal(size=(len(idx), 4))
    errors = np.zeros_like(innovation)
    for t in range(1, len(idx)):
        errors[t] = .85 * errors[t-1] + np.sqrt(1-.85**2) * innovation[t]
    daily = .5 + .28*np.cos((hour-19)*np.pi/12) + .18*np.cos((hour-8)*np.pi/6)
    seasonal = 1 + .12*np.cos(2*np.pi*(doy-205)/365.25)
    pv_noise = (1 + .08*np.random.default_rng(seed+991).normal(size=len(idx))) if seed != SEED else 1.
    result = pd.DataFrame({'timestamp_utc':idx.astype(str), 'hour_local':hour,
        'pv_unit':np.clip(.86*ghi/1000*pv_noise, 0, 1)})
    for i, (base, cap, phase) in enumerate(zip((125., 100., 85.), (330., 280., 230.), (0, 3, -3))):
        shape = 1 + .25*np.cos((hour-18-phase)*np.pi/12)
        total_mean = base*seasonal*shape
        critical = .8*total_mean*np.maximum(.45, 1+.065*errors[:,0]+.04*errors[:,i+1])
        result[f'critical_{i}'] = critical
        result[f'flex0_{i}'] = .2*total_mean
        result[f'pv_{i}'] = cap*result.pv_unit
    result['native'] = 8500 + 1600*daily + 500*np.cos(2*np.pi*doy/365.25) + 270*errors[:,0]
    # This is an explicitly synthetic upstream wind availability profile, not turbine modelling.
    wind = np.clip(weather.WS10M.to_numpy()/12, 0, 1)
    result['upstream_wind'] = 1200*wind
    result['price_buy'] = np.where((hour>=17)&(hour<=21), .24,
                                  np.where((hour>=8)&(hour<=16), .14, .08))
    result['price_sell'] = .035
    q0 = sum(result[f'critical_{i}']+result[f'flex0_{i}']-result[f'pv_{i}'] for i in range(3))
    for regime in REGIMES:
        pv_cap = 10500 if regime == 'solar_rich' else 5000
        result[f'background_{regime}'] = result.native - pv_cap*result.pv_unit - result.upstream_wind
        emissions, marginal = dispatch(result[f'background_{regime}']+q0, regime)
        result[f'mef_{regime}'] = marginal
        result[f'aef_{regime}'] = emissions / np.maximum(result.native+q0, 1)
    if save:
        result.to_csv(out/'benchmark.csv.gz', index=False, compression='gzip')
        (out/'source_manifest.json').write_text(json.dumps(sources, indent=2), encoding='utf-8')
        (out/'construction.json').write_text(json.dumps({'seed':seed,'rows':len(result),
        'development':'2021-2022','validation':'2023','test':'2024','confirmation':'2025',
        'class':'synthetic community/grid; weather-driven modelled PV; not measured operation',
            'units':'one-hour UTC intervals; kW = kWh per interval; kg CO2; synthetic USD tariffs'},indent=2))
    return result


def load():
    return pd.read_csv(ROOT/'data'/'benchmark.csv.gz')


def forecast(df, start, column):
    """Issued before start; no row >= start can be consumed."""
    if start < 7*24:
        raise ValueError('At least seven complete historical days are required')
    past = df[column].iloc[start-7*24:start].to_numpy().reshape(7,24)
    return .6*past[-1] + .4*past.mean(axis=0)


def residual_blocks(df, regime, count=8, seed=SEED, season=None, pool_years=('2022',)):
    times = pd.to_datetime(df.timestamp_utc, utc=True)
    mask = df.timestamp_utc.str.startswith(pool_years) & (times.dt.hour == 0)
    if season is not None:
        mask &= ((times.dt.month - 1)//3 == season)
    starts = np.flatnonzero(mask)
    starts = starts[starts >= 7*24]
    if count > len(starts):
        raise ValueError(f'Only {len(starts)} development residual days available')
    selected = np.random.default_rng(seed).choice(starts, size=count, replace=False)
    blocks = np.array([df[f'mef_{regime}'].iloc[s:s+24].to_numpy() -
                       forecast(df,s,f'mef_{regime}') for s in selected])
    return blocks, [str(df.timestamp_utc.iloc[s]) for s in selected]
