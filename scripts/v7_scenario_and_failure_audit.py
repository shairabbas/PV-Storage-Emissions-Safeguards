"""Read-only audit of scenario-set overlap and stated failure dominance."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results'

def dates(path):
    return set(json.loads(path.read_text(encoding='utf-8'))['residual_dates_development_only']['None'])

def main():
    comparisons=[]
    for seed in (271828,314159):
        for regime in ('coal_first','gas_first','solar_rich'):
            base=RESULTS/f'confirmation_seed{seed}_2025_{regime}'
            for draw,p32,p128 in (
                ('default',base/'CV32_config.json',base/'CV128_config.json'),
                ('11',base/'CV32_S11_config.json',RESULTS/f'v3_cv128_seed{seed}_{regime}_draw11/CV128_config.json'),
                ('23',base/'CV32_S23_config.json',RESULTS/f'v3_cv128_seed{seed}_{regime}_draw23/CV128_config.json')):
                a,b=dates(p32),dates(p128)
                comparisons.append({'demand_seed':seed,'regime':regime,'draw':draw,
                    'CV32_scenarios':len(a),'CV128_scenarios':len(b),
                    'overlap_dates':len(a&b),'CV32_nested_in_CV128':a<=b,
                    'CV32_config_sha256':hashlib.sha256(p32.read_bytes()).hexdigest(),
                    'CV128_config_sha256':hashlib.sha256(p128.read_bytes()).hexdigest()})
    failure=pd.read_csv(ROOT/'tables/v3_failure_daily.csv')
    summary=[]
    for regime in ('coal_first','gas_first','solar_rich'):
        for policy in ('CV8','CV32','MARGIN'):
            x=failure[(failure.regime==regime)&(failure.policy==policy)&(failure.total_kg>1e-6)]
            summary.append({'regime':regime,'policy':policy,'violation_days':len(x),
                'factor_abs_gt_remainder_abs_fraction':float((x.factor_error_kg.abs()>x.response_remainder_kg.abs()).mean()),
                'factor_flip_days':int(x.forecast_flip.sum()),
                'response_flip_days':int(x.response_flip.sum())})
    report={'scenario_comparisons':comparisons,'failure_dominance':summary,
            'interpretation':'Same random seed and pool do not yield nested CV32/CV128 scenario sets. Evaluation dates are paired; scenario-set composition varies. Factor dominance is diagnostic on selected violation days only.'}
    (ROOT/'audit/v7_scenario_and_failure_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'pairs':len(comparisons),'scenario_overlap_counts':sorted(set(x['overlap_dates'] for x in comparisons)),
                      'all_nested':all(x['CV32_nested_in_CV128'] for x in comparisons),
                      'factor_dominance_min':min(x['factor_abs_gt_remainder_abs_fraction'] for x in summary)},indent=2))

if __name__=='__main__':main()
