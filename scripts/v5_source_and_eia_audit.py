"""Read-only source provenance and independent 2023 level-error diagnostics."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'Carbon_Storage_Study_final_candidate_20261021'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    source_files = sorted(p for p in SOURCE.rglob('*') if p.is_file())
    source_manifest = [{'path': p.relative_to(SOURCE).as_posix(),
                        'bytes': p.stat().st_size, 'sha256': digest(p)}
                       for p in source_files]
    (ROOT / 'audit/v5_source_manifest.json').write_text(
        json.dumps({'source': SOURCE.name, 'file_count': len(source_files),
                    'files': source_manifest}, indent=2) + '\n', encoding='utf-8')

    data = pd.read_csv(ROOT / 'data/eia_erco_2022_2023.csv.gz')
    time = pd.to_datetime(data.utc_end, utc=True)
    val = data[(time.dt.year == 2023) & data.eia_estimated_co2.notna()].copy()
    time = pd.to_datetime(val.utc_end, utc=True)
    r = (val.demand_mw - val.solar_mw - val.wind_mw).to_numpy() / 10000
    design = np.column_stack((np.ones(len(val)), r, r*r,
        np.sin(2*np.pi*time.dt.hour/24), np.cos(2*np.pi*time.dt.hour/24),
        np.sin(2*np.pi*time.dt.dayofyear/365.25),
        np.cos(2*np.pi*time.dt.dayofyear/365.25)))
    coef = np.array(json.loads((ROOT / 'audit/eia_response_model.json').read_text())['coefficients'])
    observed = val.eia_estimated_co2.to_numpy()
    predicted = design @ coef
    error = predicted - observed
    # Same-hour previous-day persistence is a contextual level-prediction benchmark.
    history = pd.Series(observed, index=time)
    lag = history.reindex(time - pd.Timedelta(days=1)).to_numpy()
    ok = np.isfinite(lag)
    report = {
        'validation_hours': len(val),
        'mean_observed_tonnes_per_hour': float(observed.mean()),
        'mae_tonnes_per_hour': float(np.abs(error).mean()),
        'normalized_mae_fraction_of_mean_observed': float(np.abs(error).mean()/observed.mean()),
        'bias_predicted_minus_observed_tonnes_per_hour': float(error.mean()),
        'rmse_tonnes_per_hour': float(np.sqrt(np.mean(error**2))),
        'median_error_tonnes_per_hour': float(np.median(error)),
        'error_p05_p95_tonnes_per_hour': np.quantile(error,[.05,.95]).tolist(),
        'quarter_mae_tonnes_per_hour': {str(q): float(np.abs(error[time.dt.quarter.to_numpy()==q]).mean()) for q in range(1,5)},
        'previous_day_same_hour_persistence_mae_tonnes_per_hour': float(np.abs(observed[ok]-lag[ok]).mean()),
        'persistence_comparison_hours': int(ok.sum()),
        'interpretation': 'Predictive level diagnostics of an observational EIA-estimated CO2 regression; no causal marginal validation.'
    }
    (ROOT / 'audit/v5_eia_level_diagnostics.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_files_hashed':len(source_files),'eia':report},indent=2))


if __name__ == '__main__':
    main()
