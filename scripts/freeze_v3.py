"""Record the bounded V3 scenario replication before any new schedule is run."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'audit/V3_REPLICATION_FREEZE.json'
if target.exists():raise SystemExit('V3 freeze exists')
if list((ROOT/'results').glob('v3_cv128_*')):raise SystemExit('New outcomes already present')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
protocol={'frozen_utc':datetime.now(timezone.utc).isoformat(),
 'parent':'Version 2 copied byte-for-byte; its 907-file manifest verified before V3 edits.',
 'interpretation':'All 2025 synthetic dates and original scenario draws were already inspected in V2. New scenario draws are prospective replication of this inspected benchmark, not untouched external confirmation.',
 'new_runs':{'policy':'CV128 only','scenario_draw_seeds':[11,23],
    'matched_existing_CV32_policies':['CV32_S11','CV32_S23'],
    'demand_seeds':[314159,271828],
    'regimes':['coal_first','gas_first','solar_rich'],
    'year':2025,'every_nth_day':4,'days_per_run':92,'number_of_new_runs':12},
 'analysis':{'daily_loss':'max(delta_emissions_kg,0)',
    'paired_difference':'CV128 minus CV32 on identical synthetic demand seed, regime, calendar date, scenario draw seed',
    'resampling':'stratified by demand seed and scenario draw; circular blocks of 1,2,4,7 sampled observations (=4,8,16,28 calendar days); 2000 deterministic replicates each; descriptive conditional intervals',
    'primary_interval_block':4,
    'no_additional_draws':'Do not add scenario seeds after observing outcomes.'},
 'code_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p)
    for p in list((ROOT/'src').glob('*.py'))+[ROOT/'scripts/run_v3_scenario_replications.py']},
 'v2_manifest_sha256':sha(ROOT/'audit/v2_manifest.json')}
target.write_text(json.dumps(protocol,indent=2)+'\n')
print(json.dumps({'freeze':str(target),'new_runs':12,'scenario_draws':[11,23]}))
