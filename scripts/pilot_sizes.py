"""Validation-year computational and scenario coverage pilot; no final test reads."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data import ROOT,load,forecast,residual_blocks
from src.optimization import Settings
from src.simulation import simulate

x=load()
days=np.flatnonzero(x.timestamp_utc.str.startswith('2023'))[::24]
starts=days[::40]
records=[]
for regime in ('coal_first','solar_rich'):
    for count in (8,32,64,128):
        cfg=Settings(scenario_count=count,scenario_seed=20261019,time_limit=10.)
        policy='CV8' if count==8 else 'CV32' if count==32 else 'CV64'
        y=simulate(x,2023,regime,policy,cfg,starts,tag=f'pilot_size_{regime}_{count}')
        coverage=[]
        for start in starts:
            blocks,_=residual_blocks(x,regime,count,cfg.scenario_seed,
                pool_years=('2021','2022') if count>8 else ('2022',))
            pred=forecast(x,start,f'mef_{regime}')
            scenario=np.clip(pred[None,:]+blocks,0,.95)
            truth=x[f'mef_{regime}'].iloc[start:start+24].to_numpy()
            inside=(truth>=scenario.min(axis=0)-1e-9)&(truth<=scenario.max(axis=0)+1e-9)
            coverage.append((inside.mean(),inside.all()))
        records.append({'regime':regime,'scenario_count':count,'days':len(y),
            'runtime_median_s':float(y.runtime.median()),'runtime_max_s':float(y.runtime.max()),
            'timeouts':int((y.status_code!=0).sum()),'fallbacks':int(y.fallback.sum()),
            'hourly_envelope_coverage':float(np.mean([v[0] for v in coverage])),
            'whole_day_envelope_coverage':float(np.mean([v[1] for v in coverage])),
            'mean_positive_excess_kg':float(y.delta_emissions.clip(lower=0).mean())})
out=pd.DataFrame(records)
out.to_csv(ROOT/'tables/scenario_size_pilot.csv',index=False)
print(out.to_string(index=False))
