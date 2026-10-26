"""Machine-readable final completeness, freeze and provenance audit."""
from pathlib import Path
import hashlib
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()

def main():
    freeze=json.loads((ROOT/'audit/V2_FREEZE.json').read_text())
    amendment=json.loads((ROOT/'audit/POST_FREEZE_PARSER_AMENDMENT.json').read_text())
    changed={name:{'frozen':h,'current':sha(ROOT/name)}
        for name,h in freeze['code_sha256'].items() if sha(ROOT/name)!=h}
    assert list(changed)==['scripts/build_eia_frame.py']
    assert changed['scripts/build_eia_frame.py']['current']==amendment['second_correction']['new_sha256']
    summary=pd.read_csv(ROOT/'tables/summary_v2.csv')
    final=pd.read_csv(ROOT/'tables/final_summary.csv')
    replay=json.loads((ROOT/'audit/independent_replay.json').read_text())
    assert len(replay)==273 and max(r['max_error'] for r in replay)<1e-6
    expected=set(freeze['policies'])
    for name in [f'confirmation_seed{seed}_2025_{regime}'
                 for seed in (314159,271828)
                 for regime in ('coal_first','gas_first','solar_rich')]+['eia_confirmation_2024']:
        rows=summary[summary.run==name]
        assert set(rows.policy)==expected,(name,set(rows.policy)^expected)
        assert rows.days.nunique()==1
        assert rows.days.iloc[0]==(84 if name.startswith('eia') else 92)
        assert (rows.fallbacks==0).all() and (rows.nonoptimal_status==0).all()
    eia=pd.read_csv(ROOT/'results/eia_confirmation_2024/CV8_daily.csv')
    assert eia.date.min()>='2024-02-01'
    assert len(summary[summary.run.str.startswith('sensitivity_confirmation_')])==60
    assert len(final)==60 and final.fallbacks.sum()==0
    assert final.max_task_error.max()<1e-6 and final.max_carbon_error.max()<1e-6
    assert final.max_budget_error.max()<1e-6
    raw=[]
    for name in ('EIA930_BALANCE_2024_Jan_Jun.csv','EIA930_BALANCE_2024_Jul_Dec.csv',
                 'EIA930_ERCO_hourly_2023_2025.xlsx'):
        path=ROOT/'data'/name
        raw.append({'file':str(path.relative_to(ROOT)).replace('\\','/'),
            'bytes':path.stat().st_size,'sha256':sha(path)})
    report={'freeze_utc':freeze['timestamp_utc'],
        'frozen_code_files':len(freeze['code_sha256']),
        'post_freeze_modified_frozen_code':changed,
        'amendment':amendment,
        'core_final_runs':7,'core_final_policy_runs':105,
        'final_sampled_days_per_synthetic_run':92,'final_eia_days':84,
        'sensitivity_policy_runs':60,
        'all_saved_independent_replay_runs':len(replay),
        'all_saved_independent_replay_hours':sum(r['hours'] for r in replay),
        'independent_replay_max_error':max(r['max_error'] for r in replay),
        'final_fallbacks':int(final.fallbacks.sum()),
        'final_nonoptimal_statuses':int(final.nonoptimal.sum()),
        'final_solver_seconds':float(final.solver_seconds.sum()),
        'max_task_error':float(final.max_task_error.max()),
        'max_carbon_error':float(final.max_carbon_error.max()),
        'max_budget_error':float(final.max_budget_error.max()),
        'raw_final_inputs':raw,
        'independent_validation_boundary':'Public ERCOT inputs and EIA-estimated CO2; scaled participants and associational response are model-generated, not measured intervention effects.',
        'version_one_audit':json.loads((ROOT/'audit/v1_implementation_audit.json').read_text())}
    (ROOT/'audit/v2_final_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('core_final_policy_runs',
        'sensitivity_policy_runs','all_saved_independent_replay_runs',
        'all_saved_independent_replay_hours','independent_replay_max_error',
        'final_fallbacks','final_nonoptimal_statuses','final_solver_seconds')},indent=2))

if __name__=='__main__':main()
