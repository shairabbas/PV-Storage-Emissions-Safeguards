"""Assert V3 scientific-output lineage and numerical identities; write audit report."""
from pathlib import Path
import hashlib
import json
import math
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent/'Carbon_Storage_Study_v2_20261021'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def read(name):return json.loads((ROOT/'audit'/name).read_text())

parent_manifest=PARENT/'audit/v2_manifest.json'
freeze=read('V3_REPLICATION_FREEZE.json')
assert sha(parent_manifest)==freeze['v2_manifest_sha256']
parent=json.loads(parent_manifest.read_text())
for item in parent['files']:
    path=PARENT/item['path']
    assert path.exists() and sha(path)==item['sha256'],path
for name,digest in freeze['code_sha256'].items():
    assert sha(ROOT/name)==digest,name

interaction=read('v3_interaction_audit.json')['mean_interaction_usd_per_day']
assert math.isclose(interaction,-2.603633209310118,abs_tol=1e-10)
isolation=pd.read_csv(ROOT/'tables/v3_isolation_verified.csv')
assert 'interaction' in ' '.join(isolation.columns).lower()

units=read('v3_eia_unit_correction.json')
for frame in units['frames']:
    old=ROOT/frame['source'];new=ROOT/frame['corrected']
    assert sha(old)==frame['source_sha256'] and sha(new)==frame['corrected_sha256']
    x=pd.read_csv(new)
    assert (x['aef_eia_erco'].between(0,1)).all()
    assert (x['eia_baseline_kg']/x['native']-x['aef_eia_erco']).abs().max()<1e-10

for phase,days in [('validation_2023',53),('confirmation_2024',84)]:
    files=list((ROOT/'results'/f'v3_eia_{phase}').glob('*_daily.csv'))
    assert len(files)==15,(phase,len(files))
    assert all(len(pd.read_csv(p))==days for p in files)
for regime in ('coal_first','gas_first','solar_rich'):
    for seed in (314159,271828):
        for draw in (11,23):
            path=ROOT/'results'/f'v3_cv128_seed{seed}_{regime}_draw{draw}'/'CV128_daily.csv'
            assert path.exists() and len(pd.read_csv(path))==92,path

paired=pd.read_csv(ROOT/'tables/v3_cv32_128_summary.csv').set_index('regime')
assert len(paired)==3 and (paired.paired_days==552).all()
assert paired.loc['coal_first','difference_kg_per_day']<0
assert paired.loc['gas_first','difference_kg_per_day']>0
bootstrap=pd.read_csv(ROOT/'tables/v3_cv32_128_bootstrap.csv')
assert set(bootstrap.block_sampled_observations)=={1,2,4,7}
assert (bootstrap.calendar_span_days==4*bootstrap.block_sampled_observations).all()
gas=bootstrap[(bootstrap.regime=='gas_first') & (bootstrap.block_sampled_observations==4)].iloc[0]
assert gas.positive_difference_ci_low<0<gas.positive_difference_ci_high

idle=read('v3_margin_idle_check.json')
assert idle['idle_days']==idle['days']==84
assert idle['max_l1_intervention_kwh_per_day']<idle['tolerance_kwh_per_day']
state=read('v3_state_protocol.json')
assert state['runs_checked']==120 and state['max_state_gap']==0
replay=read('independent_replay.json')
assert len(replay)==315
hours=sum(row['hours'] for row in replay)
max_residual=max(row['max_error'] for row in replay)
assert hours==557640 and max_residual<1.1e-8
for name in ('main.tex','main.pdf','supplement.tex','supplement.pdf','results_generated.tex','supplement_generated.tex'):
    assert (ROOT/'manuscript'/name).is_file()
report={'version':'3','parent_manifest_sha256':sha(parent_manifest),
        'parent_manifest_files_verified':len(parent['files']),
        'frozen_code_files_verified':len(freeze['code_sha256']),
        'interaction_usd_per_sampled_day':interaction,
        'corrected_eia_policy_runs':30,'new_cv128_runs':12,
        'paired_days_per_regime':552,'margin_idle_days':84,
        'independent_replay_runs':len(replay),'independent_replay_hours':hours,
        'independent_replay_max_residual':max_residual,
        'scope':'Numerical/source-lineage audit, not causal or external validity proof.'}
(ROOT/'audit/v3_final_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
