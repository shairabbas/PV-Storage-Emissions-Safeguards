"""Paired 32-versus-128 severity analysis under the prospective V3 protocol."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
freeze=json.loads((ROOT/'audit/V3_REPLICATION_FREEZE.json').read_text())
assert freeze['new_runs']['scenario_draw_seeds']==[11,23]
rows=[]
for regime in ('coal_first','gas_first','solar_rich'):
    for demand_seed in (314159,271828):
        base=ROOT/'results'/f'confirmation_seed{demand_seed}_2025_{regime}'
        for draw,policy32 in (('default','CV32'),(11,'CV32_S11'),(23,'CV32_S23')):
            path128=(base/'CV128_daily.csv') if draw=='default' else (
                ROOT/'results'/f'v3_cv128_seed{demand_seed}_{regime}_draw{draw}'/'CV128_daily.csv')
            d32=pd.read_csv(base/f'{policy32}_daily.csv');d128=pd.read_csv(path128)
            assert len(d32)==len(d128)==92 and np.array_equal(d32.date,d128.date)
            for j in range(92):
                l32=max(float(d32.delta_emissions.iloc[j]),0)
                l128=max(float(d128.delta_emissions.iloc[j]),0)
                rows.append({'regime':regime,'demand_seed':demand_seed,'scenario_draw':str(draw),
                    'date':d32.date.iloc[j],'positive_32_kg':l32,'positive_128_kg':l128,
                    'paired_difference_kg':l128-l32,
                    'cost_difference_usd':float(d128.real_cost.iloc[j]-d32.real_cost.iloc[j]),
                    'violation_difference':int(l128>1e-6)-int(l32>1e-6)})
x=pd.DataFrame(rows);x.to_csv(ROOT/'tables/v3_cv32_128_paired_daily.csv',index=False)
summary=[];bootrows=[];rng=np.random.default_rng(31021)
for regime in ('coal_first','gas_first','solar_rich'):
    part=x[x.regime==regime]
    drawmeans=part.groupby('scenario_draw').paired_difference_kg.mean().to_dict()
    seedmeans=part.groupby('demand_seed').paired_difference_kg.mean().to_dict()
    # Same sampled calendar positions are resampled for every demand/draw
    # stratum, preserving the common-weather dependence across policies.
    arrays=[]
    for seed in (314159,271828):
        for draw in ('default','11','23'):
            frame=part[(part.demand_seed==seed)&(part.scenario_draw==draw)]
            arrays.append(frame[['paired_difference_kg','cost_difference_usd','violation_difference']].to_numpy())
    arr=np.stack(arrays)
    assert arr.shape==(6,92,3)
    observed=arr.mean(axis=(0,1))
    for block in (1,2,4,7):
        samples=np.empty((2000,3))
        for z in range(2000):
            starts=rng.integers(0,92,size=int(np.ceil(92/block)))
            ix=np.concatenate([(s+np.arange(block))%92 for s in starts])[:92]
            samples[z]=arr[:,ix,:].mean(axis=(0,1))
        lower=np.quantile(samples,.025,axis=0);upper=np.quantile(samples,.975,axis=0)
        bootrows.append({'regime':regime,'block_sampled_observations':block,
            'calendar_span_days':block*4,'resamples':2000,
            'positive_difference_mean_kg_per_day':observed[0],
            'positive_difference_ci_low':lower[0],'positive_difference_ci_high':upper[0],
            'cost_difference_mean_usd_per_day':observed[1],
            'cost_difference_ci_low':lower[1],'cost_difference_ci_high':upper[1],
            'violation_rate_difference':observed[2],
            'violation_rate_ci_low':lower[2],'violation_rate_ci_high':upper[2]})
    summary.append({'regime':regime,'paired_days':len(part),
        'CV32_positive_kg_per_day':part.positive_32_kg.mean(),
        'CV128_positive_kg_per_day':part.positive_128_kg.mean(),
        'difference_kg_per_day':observed[0],
        'draw_means_kg_per_day':json.dumps(drawmeans),
        'demand_seed_means_kg_per_day':json.dumps(seedmeans),
        'draw_mean_range_kg_per_day':max(drawmeans.values())-min(drawmeans.values()),
        'cost_difference_usd_per_day':observed[1]})
pd.DataFrame(summary).to_csv(ROOT/'tables/v3_cv32_128_summary.csv',index=False)
pd.DataFrame(bootrows).to_csv(ROOT/'tables/v3_cv32_128_bootstrap.csv',index=False)
print(pd.DataFrame(summary)[['regime','difference_kg_per_day','draw_mean_range_kg_per_day']].to_string(index=False))
