"""Seal code, settings and final-test selection before reading final outcomes."""
from pathlib import Path
import hashlib
import json
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'audit/V2_FREEZE.json'
if TARGET.exists():raise SystemExit('Freeze already exists')
if list((ROOT/'results').glob('confirmation_*')) or list((ROOT/'results').glob('eia_confirmation_*')):
    raise SystemExit('Confirmation outcomes already present')
files=[p for directory in ('src','scripts') for p in (ROOT/directory).glob('*.py')]
hashes={str(p.relative_to(ROOT)).replace('\\','/'):
    hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
margin=json.loads((ROOT/'audit/margin_calibration.json').read_text())['margin_kg_per_kwh']
protocol={
 'timestamp_utc':datetime.now(timezone.utc).isoformat(),
 'version_1':'Completed frozen deliverable preserved unmodified; 2024-2025 version-1 results were already inspected.',
 'research_question':'When does a finite-scenario carbon guard fail against a separately replayed consequential response, after isolating meter, flexibility and storage?',
 'synthetic_final':{'year':2025,'daily_stride':4,'independent_generation_seeds':[314159,271828],
                    'regimes':['coal_first','gas_first','solar_rich'],
                    'weather':'previously available measured NASA weather; synthetic load/PV shocks independently generated per seed',
                    'status':'no new synthetic seed generated or evaluated before this freeze'},
 'external_final':{'source':'EIA-930 ERCO demand, solar, wind and EIA-estimated production CO2',
                   'year':2024,'first_eligible_day':'2024-02-01','daily_stride':4,
                   'response':'2022-fitted associational residual-load derivative; model-generated counterfactual, not observed causal response',
                   'leakage':'Seven 2024-01-01 UTC EIA input rows appeared at end of 2023 source-year CSV and were inspected; Jan 1-Jan 31 excluded prospectively.'},
 'policies':['B0','M0','M1','S0','S1','B3','CV8','CV32','CV128',
             'CV32_SEAS','CV32_S11','CV32_S23','MARGIN','G_worst','ROBOX'],
 'margin_kg_per_kwh':margin,
 'scenario_sampling':'8 original; 32 and 128 development blocks; repeated seeds 11,23 and quarter-conditioned 32',
 'carbon_factor_sensitivity':'forecast multipliers 0.85 and 1.15 for CV8/CV32/MARGIN; scenario-residual scales 0.5 and 1.5 for CV8/CV32',
 'evaluation':'paired identical realizations; cost, emissions, positive violation mass/count, 95th percentile, service/ledger feasibility, solver status/runtime, forecast and scenario coverage, error decomposition; independent replay',
 'interpretation':'margin has no unconditional coverage guarantee; public ERCOT check has no observed intervention response; no submission-readiness inference from PDF compilation',
 'code_sha256':hashes}
TARGET.write_text(json.dumps(protocol,indent=2)+'\n')
print(json.dumps({'freeze':str(TARGET),'python_files':len(hashes),'margin':margin}))
