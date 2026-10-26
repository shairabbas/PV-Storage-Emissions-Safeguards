"""Read-only numerical and implementation audit of the immutable version-1 delivery."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
V1=ROOT.parent/'Carbon_Storage_Study_20261019'
TOL=1e-5

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    freeze=json.loads((V1/'audit/PRODUCTION_FREEZE.json').read_text())
    manifest=json.loads((V1/'DELIVERY_MANIFEST.json').read_text())
    for entry in manifest['files']:
        path=V1/entry['path']
        assert path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],entry['path']
    annual=pd.read_csv(V1/'tables/annual.csv')
    assert len(annual)==63
    detail=json.loads((V1/'audit/independent_replay.json').read_text())
    assert len(detail)==111 and sum(x['hours'] for x in detail)==588456
    residual=max(x['max_error'] for x in detail)
    assert residual<TOL
    records=[]
    for row in annual.itertuples():
        folder=V1/'results'/f'{row.year}_{row.regime}'
        day=pd.read_csv(folder/f'{row.policy}_daily.csv')
        base=pd.read_csv(folder/'B0_daily.csv')
        cfg=json.loads((folder/f'{row.policy}_config.json').read_text())
        assert len(day)==row.days==len(base) and day.date.equals(base.date)
        assert all(str(x).startswith('2022') for x in cfg['residual_dates_development_only'])
        assert abs(day.real_cost.sum()-row.cost)<TOL
        assert abs(day.delta_emissions.sum()/1000-row.delta_tonnes)<TOL
        assert abs(day.attributed_imports.sub(base.attributed_imports).sum()/1000-row.attribution_delta_tonnes)<TOL
        assert abs(day.reference_cost.sum()-base.real_cost.sum())<TOL
        assert day.task_error.abs().max()<TOL and day.end_energy_error.abs().max()<TOL
        assert day.carbon_error.abs().max()<TOL and day.energy_error.abs().max()<TOL
        assert day.budget_error.abs().max()<TOL and day.unserved_energy.abs().max()<TOL
        assert day.max_meter_power.max()<=cfg['settings']['grid_limit']+TOL
        assert int(day.fallback.sum())==row.fallbacks==0
        assert int((day.delta_emissions>1e-5).sum())==row.positive_days
        assert abs(100*(1-day.real_cost.sum()/base.real_cost.sum())-row.cost_saving_pct)<TOL
        assert day.gap.max()<1.01e-7
        if row.policy!='B0':
            assert (day.status_code==0).all()
        records.append({'year':row.year,'regime':row.regime,'policy':row.policy,
                        'days':len(day),'delta_tonnes':row.delta_tonnes,
                        'cost':row.cost,'positive_days':row.positive_days})
    for file in ('main.pdf','supplement.pdf'):
        assert (V1/'manuscript'/file).exists()
    report={'v1_manifest_sha256':sha(V1/'DELIVERY_MANIFEST.json'),
            'v1_archive_sha256':sha(ROOT.parent/'Carbon_Storage_Study_20261019_reproducibility.zip'),
            'frozen_utc':freeze['created_utc'],'audited_manifest_files':len(manifest['files']),
            'annual_runs':len(records),'annual_days':sum(x['days'] for x in records),
            'independent_replay_runs':len(detail),'independent_replay_hours':sum(x['hours'] for x in detail),
            'independent_replay_max_error':residual,
            'numerical_claims':'All 63 annual CSV rows exactly reconstruct from daily outputs within 1e-5; eight key claim/constraint columns checked.',
            'code_findings':[
                'Future realized weather/factors enter B5 oracle only; causal policies use prior finalized series plus known calendar/tariff.',
                '2022 scenario residual blocks are fixed at eight and shared over all test days; no calibration or season conditioning.',
                'Forecast grid feasibility can differ from realized grid feasibility; simulator rejects realized overload, none in accepted runs.',
                'Carbon ledger receives realized average factors ex post; source-proxy objective and marginal-dispatch evaluator are distinct.',
                'B0 independent billing uses gross community meters, while all carbon policies use common aggregate physical meter; disclosed correction retained.',
                'Expense includes grid bill, degradation and flexible-task discomfort; excludes equipment capital and social generator cost.',
                'Daily empirical surrogate has no out-of-sample chance guarantee; actual dispatch can cross merit-order breakpoints.'
            ],
            'scientific_corrections':'No new numerical correction found. Preserve v1 outputs and freeze. The reported positive-day frequencies are model-estimated violation frequencies, not chance-constraint coverage certificates.'}
    (ROOT/'audit/v1_implementation_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('audited_manifest_files','annual_runs','annual_days','independent_replay_max_error')},indent=2))

if __name__=='__main__':main()
