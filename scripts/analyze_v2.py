"""Rebuild paper tables from saved schedules and exogenous inputs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def forecast(x,i,column):
    past=x[column].iloc[i-168:i].to_numpy().reshape(7,24)
    return .6*past[-1]+.4*past.mean(axis=0)

def analyze():
    summaries=[]; decomposition=[]; coverage=[]; isolation=[]
    sources={}
    for directory in sorted((ROOT/'results').iterdir()):
        if not directory.is_dir() or not (directory.name.startswith(('validation_','confirmation_','eia_','sensitivity_'))):continue
        daily_map={}
        for config_path in sorted(directory.glob('*_config.json')):
            policy=config_path.name.removesuffix('_config.json')
            cfg=json.loads(config_path.read_text());regime=cfg['regime'];source_file=cfg['source_file']
            if source_file not in sources:sources[source_file]=pd.read_csv(ROOT/source_file)
            source=sources[source_file];lookup={s:i for i,s in enumerate(source.timestamp_utc)}
            daily=pd.read_csv(directory/f'{policy}_daily.csv')
            h=pd.read_csv(directory/f'{policy}_hourly.csv.gz')
            daily_map[policy]=daily
            positive=daily.delta_emissions.clip(lower=0)
            summaries.append({'run':directory.name,'regime':regime,'policy':policy,'days':len(daily),
                'cost':daily.real_cost.sum(),'cost_per_day':daily.real_cost.mean(),
                'delta_kg':daily.delta_emissions.sum(),'delta_kg_per_day':daily.delta_emissions.mean(),
                'violating_days':int((daily.delta_emissions>1e-6).sum()),
                'positive_kg':positive.sum(),'mean_positive_kg':positive[positive>1e-6].mean() if (positive>1e-6).any() else 0,
                'p95_daily_kg':daily.delta_emissions.quantile(.95),
                'max_daily_kg':daily.delta_emissions.max(),
                'task_error':daily.task_error.max(),'carbon_error':daily.carbon_error.max(),
                'energy_error':daily.energy_error.max(),'budget_error':daily.budget_error.abs().max(),
                'fallbacks':int(daily.fallback.sum()),'nonoptimal_status':int((daily.status_code!=0).sum()),
                'solver_seconds':daily.runtime.sum(),'median_seconds':daily.runtime.median()})
            if policy in ('B0','M0','ROBOX'):continue
            blocks={}
            for season,dates in cfg['residual_dates_development_only'].items():
                blocks[season]=np.array([source[f'mef_{regime}'].iloc[lookup[d]:lookup[d]+24].to_numpy()-
                    forecast(source,lookup[d],f'mef_{regime}') for d in dates])
            for k,date in enumerate(daily.date):
                i=lookup[date];y=h.iloc[k*24:(k+1)*24]
                hat=np.clip(forecast(source,i,f'mef_{regime}')*cfg['settings']['carbon_forecast_bias'],0,.95)
                actual=source[f'mef_{regime}'].iloc[i:i+24].to_numpy()
                v=y.q_proposed.to_numpy()-y.q_reference.to_numpy()
                point=float(hat@v);linear=float(actual@v);truth=float(daily.delta_emissions.iloc[k])
                decomposition.append({'run':directory.name,'regime':regime,'policy':policy,'date':date,
                    'actual_kg':truth,'point_kg':point,'forecast_component_kg':linear-point,
                    'response_component_kg':truth-linear,'forecast_mae_kg_per_kwh':np.mean(np.abs(actual-hat)),
                    'forecast_bias_kg_per_kwh':np.mean(actual-hat),'intervention_l1_kwh':np.abs(v).sum()})
                if policy.startswith('CV') or policy=='G_worst':
                    season=str((pd.to_datetime(date,utc=True).month-1)//3) if cfg['settings']['scenario_seasonal'] else 'None'
                    scenario=np.clip(hat[None,:]+cfg['settings']['factor_error']*blocks[season],0,.95)
                    inside=(actual>=scenario.min(axis=0))&(actual<=scenario.max(axis=0))
                    loss=scenario@v
                    coverage.append({'run':directory.name,'regime':regime,'policy':policy,'date':date,
                        'hour_coverage':inside.mean(),'whole_day_covered':int(inside.all()),
                        'actual_linear_above_scenario_max':int(linear>loss.max()+1e-6),
                        'scenario_width_mean':np.mean(scenario.max(axis=0)-scenario.min(axis=0)),
                        'linear_excess_over_max_kg':max(0,linear-loss.max())})
        if all(x in daily_map for x in ('B0','M0','M1','S0','S1')):
            c={p:daily_map[p].real_cost.sum() for p in ('B0','M0','M1','S0','S1')}
            isolation.append({'run':directory.name,'days':len(daily_map['B0']),
                'independent_bill_to_shared_meter_savings':c['B0']-c['M0'],
                'flex_savings_without_storage':c['M0']-c['M1'],
                'storage_savings_with_fixed_demand':c['M0']-c['S0'],
                'storage_savings_with_flex':c['M1']-c['S1'],
                'flex_savings_with_storage':c['S0']-c['S1'],
                'interaction':(c['M1']-c['S1'])-(c['M0']-c['S0'])})
    tables=ROOT/'tables';tables.mkdir(exist_ok=True)
    for name,records in [('summary_v2',summaries),('error_decomposition_v2',decomposition),
                         ('scenario_stress',coverage),('isolation',isolation)]:
        pd.DataFrame(records).to_csv(tables/f'{name}.csv',index=False)
    print(json.dumps({'runs':len(set(r['run'] for r in summaries)),
        'policy_summaries':len(summaries),'decomposition_days':len(decomposition),
        'coverage_days':len(coverage),'isolation_runs':len(isolation)}))

if __name__=='__main__':analyze()
