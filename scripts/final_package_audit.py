"""Validate final candidate lineage, science tables, boundaries and delivered files."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.simulation import _validate_eia_factor_units

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent/'Carbon_Storage_Study_v3_20261021'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def audit(name):return json.loads((ROOT/'audit'/name).read_text())

v3path=PARENT/'audit/v3_manifest.json'
v3=json.loads(v3path.read_text())
assert sha(v3path)==sha(ROOT/'audit/v3_manifest.json')
for item in v3['files']:
    p=PARENT/item['path']
    assert p.is_file() and sha(p)==item['sha256'],p

unit=audit('final_eia_unit_dependency.json')
assert len(unit['representative_source_reconstructions'])==2
assert unit['largest_non_target_frame_roundtrip_difference']<4e-15
for year in (2023,2024):
    good=pd.read_csv(ROOT/'data'/f'eia_erco_2022_{year}_frame_corrected.csv.gz')
    old=pd.read_csv(ROOT/'data'/f'eia_erco_2022_{year}_frame.csv.gz')
    _validate_eia_factor_units(good)
    try:_validate_eia_factor_units(old)
    except ValueError:pass
    else:raise AssertionError('Legacy 1000-fold error passed unit boundary')

timeline=audit('final_timeline_completion.json')
assert timeline['runs']==117 and timeline['completed_skipped_days']==31581
assert timeline['max_state_gap']<1e-8 and timeline['max_conservation_error']<1e-8
assert timeline['max_reference_exchange_error']<1e-8
assert timeline['max_skipped_meter_kw']<2000
smoke=audit('final_timeline_amendment_smoke.json')
assert len(smoke)==2 and max(x['maximum_saved_hourly_difference'] for x in smoke)<1e-7
full=pd.read_csv(ROOT/'tables/final_full_window_isolation.csv')
assert len(full)==7
assert np.isclose(full[full.run.str.startswith('confirmation_seed')].interaction_usd_per_selected_day.mean(),
                  -2.603633209310118,atol=1e-8)
interaction=audit('v3_interaction_audit.json')['mean_interaction_usd_per_day']
assert math.isclose(interaction,-2.603633209310118,abs_tol=1e-10)
pair=pd.read_csv(ROOT/'tables/v3_cv32_128_summary.csv').set_index('regime')
boot=pd.read_csv(ROOT/'tables/v3_cv32_128_bootstrap.csv')
gas=boot[(boot.regime=='gas_first')&(boot.block_sampled_observations==4)].iloc[0]
assert gas.positive_difference_ci_low<0<gas.positive_difference_ci_high
assert pair.loc['gas_first','difference_kg_per_day']>0
assert (boot.calendar_span_days==4*boot.block_sampled_observations).all()
idle=audit('v3_margin_idle_check.json')
assert idle['days']==idle['idle_days']==84
assert idle['max_l1_intervention_kwh_per_day']<idle['tolerance_kwh_per_day']

folders=[ROOT/'results'/f'confirmation_seed{seed}_2025_{regime}'
         for seed in (314159,271828)
         for regime in ('coal_first','gas_first','solar_rich')]
folders.append(ROOT/'results/v3_eia_confirmation_2024')
folders += [ROOT/'results'/f'v3_cv128_seed{seed}_{regime}_draw{draw}'
            for seed in (314159,271828)
            for regime in ('coal_first','gas_first','solar_rich')
            for draw in (11,23)]
run_count=0;selected_days=0;max_service=0.;max_energy=0.;max_carbon=0.
max_budget=0.;max_meter=0.;nonzero_status=0;fallbacks=0
for folder in folders:
    daily_paths=sorted(folder.glob('*_daily.csv'))
    if folder.name.startswith('v3_cv128_'):assert len(daily_paths)==1
    else:assert len(daily_paths)==15
    ref_dates=None;ref_emissions=None;ref_bills=None
    for path in daily_paths:
        p=path.name.removesuffix('_daily.csv')
        d=pd.read_csv(path)
        config=json.loads((folder/f'{p}_config.json').read_text())
        assert len(d)==config['days']
        if ref_dates is None:
            ref_dates=d.date.to_numpy();ref_emissions=d.reference_emissions.to_numpy()
            ref_bills=d.reference_cost.to_numpy()
        else:
            assert np.array_equal(d.date.to_numpy(),ref_dates)
            assert np.allclose(d.reference_emissions,ref_emissions,atol=1e-7,rtol=0)
            assert np.allclose(d.reference_cost,ref_bills,atol=1e-7,rtol=0)
        run_count+=1;selected_days+=len(d)
        max_service=max(max_service,float(d.task_error.abs().max()))
        max_energy=max(max_energy,float(d.energy_error.abs().max()),
                       float(d.end_energy_error.abs().max()))
        max_carbon=max(max_carbon,float(d.carbon_error.abs().max()))
        max_budget=max(max_budget,float(d.budget_error.abs().max()))
        max_meter=max(max_meter,float(d.max_meter_power.max()))
        nonzero_status+=int((d.status_code!=0).sum())
        fallbacks+=int(d.fallback.astype(str).str.lower().eq('true').sum())
        assert d.unserved_energy.abs().max()<1e-10
        assert d.renewable_curtailment.abs().max()<1e-10
        assert d.max_meter_power.max()<=config['settings']['grid_limit']+1e-5
assert run_count==117
assert max_service<1e-4 and max_energy<1e-4 and max_carbon<1e-6 and max_budget<1e-6
assert nonzero_status==0 and fallbacks==0

replay=audit('independent_replay.json')
hours=sum(x['hours'] for x in replay);maximum=max(x['max_error'] for x in replay)
assert len(replay)==317 and hours==561864 and maximum<1.1e-8
for relative in ('manuscript/main.tex','manuscript/main.pdf',
    'manuscript/supplement.tex','manuscript/supplement.pdf',
    'HIGHLIGHTS.txt','Highlights.docx','COVER_LETTER_DRAFT.md',
    'DATA_CODE_AVAILABILITY.md','AUTHOR_DECLARATION_CHECKLIST.md',
    'JOURNAL_GUIDANCE_AUDIT.md','FINAL_DECISION.md'):
    assert (ROOT/relative).is_file(),relative
highlights=[s for s in (ROOT/'HIGHLIGHTS.txt').read_text().splitlines() if s.strip()]
assert 3<=len(highlights)<=5 and all(len(s)<=85 for s in highlights)
report={'candidate':'Carbon_Storage_Study_final_candidate_20261021',
    'parent_v3_manifest_sha256':sha(v3path),'parent_v3_files_verified':len(v3['files']),
    'final_comparison_runs':run_count,'final_selected_policy_days':selected_days,
    'explicit_intervening_policy_days':timeline['completed_skipped_days'],
    'timeline_max_state_gap':timeline['max_state_gap'],
    'maximum_task_error':max_service,'maximum_energy_or_terminal_error':max_energy,
    'maximum_carbon_error':max_carbon,'maximum_budget_error':max_budget,
    'maximum_selected_meter_kw':max_meter,'nonzero_solver_status_days':nonzero_status,
    'fallback_days':fallbacks,'independent_replay_runs':len(replay),
    'independent_replay_hours':hours,'independent_replay_max_error':maximum,
    'scope':'Internal numerical and provenance consistency; not proof of novelty, causality or external validity.'}
(ROOT/'audit/final_package_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
