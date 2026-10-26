"""Reconstruct point/forecast/response terms and protection-operation tradeoffs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
POLICIES=('B0','M0','M1','S0','S1','B3','CV8','CV32','CV128',
          'CV32_SEAS','CV32_S11','CV32_S23','MARGIN','G_worst','ROBOX')
FOLDERS=[ROOT/'results'/f'confirmation_seed{seed}_2025_{regime}'
    for seed in (314159,271828) for regime in ('coal_first','gas_first','solar_rich')]
FOLDERS.append(ROOT/'results/v3_eia_confirmation_2024')
daily_rows=[];summary=[]
for folder in FOLDERS:
    if not folder.exists():raise SystemExit(f'Incomplete corrected outcome: {folder}')
    config=json.loads((folder/'CV8_config.json').read_text())
    regime=config['regime'];domain='ERCOT-input hybrid' if regime=='eia_erco' else 'synthetic'
    source=pd.read_csv(ROOT/config['source_file'])
    lookup={stamp:i for i,stamp in enumerate(source.timestamp_utc)}
    ref=pd.read_csv(folder/'ROBOX_daily.csv')
    dates=ref.date.to_numpy();n=len(dates)
    starts=np.array([lookup[stamp] for stamp in dates])
    actual=np.array([source[f'mef_{regime}'].iloc[i:i+24].to_numpy() for i in starts])
    predicted=np.array([.6*source[f'mef_{regime}'].iloc[i-24:i].to_numpy()+
        .4*source[f'mef_{regime}'].iloc[i-168:i].to_numpy().reshape(7,24).mean(axis=0)
        for i in starts])
    for policy in POLICIES:
        path=folder/f'{policy}_daily.csv'
        if not path.exists():raise SystemExit(f'Missing policy: {path}')
        d=pd.read_csv(path)
        h=pd.read_csv(folder/f'{policy}_hourly.csv.gz')
        cfg=json.loads((folder/f'{policy}_config.json').read_text())['settings']
        assert len(d)==n and np.array_equal(d.date.to_numpy(),dates)
        intervention=(h.q_proposed.to_numpy()-h.q_reference.to_numpy()).reshape(n,24)
        hat=np.clip(predicted*cfg['carbon_forecast_bias'],0,.95)
        point=(hat*intervention).sum(axis=1)
        factor=((actual-hat)*intervention).sum(axis=1)
        linear=(actual*intervention).sum(axis=1)
        response=d.delta_emissions.to_numpy()-linear
        truth=d.delta_emissions.to_numpy()
        assert np.max(np.abs(point+factor+response-truth))<1e-7
        L=np.maximum(truth,0)
        magnitude=np.abs(intervention).sum(axis=1)
        throughput=(h.charge.to_numpy()+h.discharge.to_numpy()).reshape(n,24).sum(axis=1)
        flex=np.abs(h[[f'flexible_{i}' for i in range(3)]].to_numpy()-
                    h[[f'flex0_{i}' for i in range(3)]].to_numpy()).reshape(n,24,3).sum(axis=(1,2))
        cost=d.real_cost.to_numpy();refcost=ref.real_cost.to_numpy()
        for j,date in enumerate(dates):
            daily_rows.append({'run':folder.name,'domain':domain,'regime':regime,'policy':policy,
                'date':date,'point_kg':point[j],'factor_error_kg':factor[j],
                'response_remainder_kg':response[j],'total_kg':truth[j],
                'positive_kg':L[j],'real_cost_usd':cost[j],
                'expense_vs_ROBOX_usd':cost[j]-refcost[j],
                'intervention_l1_kwh':magnitude[j],'battery_throughput_kwh':throughput[j],
                'flexible_shift_l1_kwh':flex[j],
                'idle_intervention':int(magnitude[j]<=1e-6),
                'idle_battery':int(throughput[j]<=1e-6),
                'forecast_flip':int(point[j]<=1e-6 and linear[j]>1e-6 and truth[j]>1e-6),
                'response_flip':int(linear[j]<=1e-6 and truth[j]>1e-6),
                'opposing_error_signs':int(factor[j]*response[j]<-1e-8)})
x=pd.DataFrame(daily_rows)
x.to_csv(ROOT/'tables/v3_failure_daily.csv',index=False)
for (domain,regime,policy),g in x.groupby(['domain','regime','policy']):
    positive=g[g.positive_kg>1e-6]
    summary.append({'domain':domain,'regime':regime,'policy':policy,'days':len(g),
        'cost_usd_per_day':g.real_cost_usd.mean(),
        'expense_vs_ROBOX_usd_per_day':g.expense_vs_ROBOX_usd.mean(),
        'mean_total_kg_per_day':g.total_kg.mean(),
        'positive_kg_per_day':g.positive_kg.mean(),
        'violation_fraction':len(positive)/len(g),
        'mean_kg_given_violation':positive.positive_kg.mean() if len(positive) else 0.,
        'p95_kg_given_violation':positive.positive_kg.quantile(.95) if len(positive) else 0.,
        'max_positive_kg':g.positive_kg.max(),
        'intervention_l1_kwh_per_day':g.intervention_l1_kwh.mean(),
        'battery_throughput_kwh_per_day':g.battery_throughput_kwh.mean(),
        'flexible_shift_l1_kwh_per_day':g.flexible_shift_l1_kwh.mean(),
        'idle_intervention_fraction':g.idle_intervention.mean(),
        'idle_battery_fraction':g.idle_battery.mean(),
        'mean_point_kg_on_violation':positive.point_kg.mean() if len(positive) else 0.,
        'mean_factor_error_kg_on_violation':positive.factor_error_kg.mean() if len(positive) else 0.,
        'mean_response_kg_on_violation':positive.response_remainder_kg.mean() if len(positive) else 0.,
        'mean_abs_factor_error_kg_on_violation':positive.factor_error_kg.abs().mean() if len(positive) else 0.,
        'mean_abs_response_kg_on_violation':positive.response_remainder_kg.abs().mean() if len(positive) else 0.,
        'forecast_flip_days':int(positive.forecast_flip.sum()),
        'response_flip_days':int(positive.response_flip.sum()),
        'opposing_error_sign_days':int(positive.opposing_error_signs.sum())})
s=pd.DataFrame(summary);s.to_csv(ROOT/'tables/v3_failure_tradeoff_summary.csv',index=False)
guards=('B3','CV8','CV32','CV128','CV32_SEAS','CV32_S11','CV32_S23','MARGIN','G_worst','ROBOX')
dominated=[]
for (domain,regime),group in s[s.policy.isin(guards)].groupby(['domain','regime']):
    for _,b in group.iterrows():
        for _,a in group.iterrows():
            if a.policy==b.policy:continue
            if (a.cost_usd_per_day<=b.cost_usd_per_day+1e-8 and
                a.positive_kg_per_day<=b.positive_kg_per_day+1e-8 and
                (a.cost_usd_per_day<b.cost_usd_per_day-1e-8 or
                 a.positive_kg_per_day<b.positive_kg_per_day-1e-8)):
                dominated.append({'domain':domain,'regime':regime,'dominated':b.policy,
                    'dominating':a.policy,'cost_advantage_usd_per_day':b.cost_usd_per_day-a.cost_usd_per_day,
                    'positive_advantage_kg_per_day':b.positive_kg_per_day-a.positive_kg_per_day})
pd.DataFrame(dominated).to_csv(ROOT/'tables/v3_tested_case_dominance.csv',index=False)
margin=x[(x.domain=='ERCOT-input hybrid')&(x.policy=='MARGIN')]
idle={'tolerance_kwh_per_day':1e-6,'days':len(margin),
      'max_l1_intervention_kwh_per_day':float(margin.intervention_l1_kwh.max()),
      'max_battery_throughput_kwh_per_day':float(margin.battery_throughput_kwh.max()),
      'idle_days':int(margin.idle_intervention.sum())}
(ROOT/'audit/v3_margin_idle_check.json').write_text(json.dumps(idle,indent=2)+'\n')
print(json.dumps({'daily_rows':len(x),'summary_rows':len(s),
    'dominance_pairs':len(dominated),'corrected_eia_margin_idle_days':idle['idle_days']}))
