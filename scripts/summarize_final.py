"""Aggregate frozen confirmation results; paired block intervals are descriptive."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
    s=pd.read_csv(ROOT/'tables/summary_v2.csv')
    final=s[s.run.str.startswith(('confirmation_','eia_confirmation_'))].copy()
    final['domain']=np.where(final.run.str.startswith('eia_'),'ERCOT-input hybrid','synthetic')
    grouped=final.groupby(['domain','regime','policy'],as_index=False).agg(
        runs=('run','nunique'),days=('days','sum'),cost=('cost','sum'),
        delta_kg=('delta_kg','sum'),positive_kg=('positive_kg','sum'),
        violations=('violating_days','sum'),solver_seconds=('solver_seconds','sum'),
        fallbacks=('fallbacks','sum'),nonoptimal=('nonoptimal_status','sum'),
        max_task_error=('task_error','max'),max_carbon_error=('carbon_error','max'),
        max_budget_error=('budget_error','max'))
    grouped['cost_per_day']=grouped.cost/grouped.days
    grouped['delta_kg_per_day']=grouped.delta_kg/grouped.days
    grouped['positive_kg_per_day']=grouped.positive_kg/grouped.days
    grouped['violation_fraction']=grouped.violations/grouped.days
    grouped.to_csv(ROOT/'tables/final_summary.csv',index=False)
    rows=[];rng=np.random.default_rng(91021)
    for regime in ('coal_first','gas_first','solar_rich'):
        for comparison in ('CV32','CV128','CV32_SEAS','MARGIN','G_worst','ROBOX'):
            arrays=[]
            for seed in (314159,271828):
                folder=ROOT/'results'/f'confirmation_seed{seed}_2025_{regime}'
                a=pd.read_csv(folder/'CV8_daily.csv')
                b=pd.read_csv(folder/f'{comparison}_daily.csv')
                assert np.array_equal(a.date,b.date)
                arrays.append(np.column_stack((b.delta_emissions.clip(lower=0)-a.delta_emissions.clip(lower=0),
                    b.real_cost-a.real_cost,(b.delta_emissions>1e-6).astype(int)-(a.delta_emissions>1e-6).astype(int))))
            observed=np.concatenate(arrays).mean(axis=0)
            reps=np.empty((2000,3))
            for z in range(2000):
                sampled=[]
                for values in arrays:
                    n=len(values);starts=rng.integers(0,n,size=int(np.ceil(n/7)))
                    indices=np.concatenate([(start+np.arange(7))%n for start in starts])[:n]
                    sampled.append(values[indices])
                reps[z]=np.concatenate(sampled).mean(axis=0)
            row={'regime':regime,'comparator':comparison,'reference':'CV8','days':sum(map(len,arrays))}
            for j,metric in enumerate(('positive_kg_per_day','cost_per_day','violation_fraction')):
                row[f'{metric}_difference']=observed[j]
                row[f'{metric}_ci_low'],row[f'{metric}_ci_high']=np.quantile(reps[:,j],[.025,.975])
            rows.append(row)
    pd.DataFrame(rows).to_csv(ROOT/'tables/paired_uncertainty.csv',index=False)
    c=pd.read_csv(ROOT/'tables/scenario_stress.csv')
    c=c[c.run.str.startswith(('confirmation_','eia_confirmation_'))]
    c.groupby(['run','regime','policy'],as_index=False).agg(
        hourly_coverage=('hour_coverage','mean'),whole_day_coverage=('whole_day_covered','mean'),
        scenario_max_exceedance_fraction=('actual_linear_above_scenario_max','mean'),
        mean_excess_kg=('linear_excess_over_max_kg','mean')).to_csv(ROOT/'tables/final_coverage.csv',index=False)
    sensitivity=[]
    for _,record in s[s.run.str.startswith('sensitivity_confirmation_')].iterrows():
        cfg=json.loads((ROOT/'results'/record.run/f'{record.policy}_config.json').read_text())['settings']
        if abs(cfg['carbon_forecast_bias']-1)>1e-10:
            variant=f'forecast_x{cfg["carbon_forecast_bias"]:.2f}'
        else:variant=f'residual_x{cfg["factor_error"]:.2f}'
        sensitivity.append({'run':record.run,'regime':record.regime,'policy':record.policy,
            'variant':variant,'days':record.days,'cost':record.cost,
            'positive_kg':record.positive_kg,'violations':record.violating_days})
    z=pd.DataFrame(sensitivity).groupby(['regime','policy','variant'],as_index=False).agg(
        runs=('run','nunique'),days=('days','sum'),cost=('cost','sum'),
        positive_kg=('positive_kg','sum'),violations=('violations','sum'))
    z['cost_per_day']=z.cost/z.days;z['positive_kg_per_day']=z.positive_kg/z.days
    z['violation_fraction']=z.violations/z.days
    z.to_csv(ROOT/'tables/factor_sensitivity.csv',index=False)
    print(json.dumps({'rows':len(grouped),'paired_intervals':len(rows),
        'sensitivity_variants':len(z),'max_task_error':grouped.max_task_error.max(),
        'fallbacks':int(grouped.fallbacks.sum())}))

if __name__=='__main__':main()
