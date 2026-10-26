"""One prespecified 90th-percentile validation-only margin; no final-year outcomes read."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data import ROOT,load,forecast
from src.optimization import Settings
from src.simulation import simulate

x=load()
days=np.flatnonzero(x.timestamp_utc.str.startswith('2023'))[::24]
starts=days[::7]
rows=[]
for regime in ('coal_first','gas_first','solar_rich'):
    simulate(x,2023,regime,'CV8',Settings(),starts,tag=f'calibration_{regime}')
    h=pd.read_csv(ROOT/'results'/f'calibration_{regime}'/'CV8_hourly.csv.gz')
    d=pd.read_csv(ROOT/'results'/f'calibration_{regime}'/'CV8_daily.csv')
    for j,start in enumerate(starts):
        segment=h.iloc[j*24:(j+1)*24]
        change=segment.q_proposed.to_numpy()-segment.q_reference.to_numpy()
        predicted=forecast(x,start,f'mef_{regime}')@change
        scale=np.abs(change).sum()
        error=float(d.delta_emissions.iloc[j]-predicted)
        rows.append({'regime':regime,'date':d.date.iloc[j],
            'year_half':'calibration' if pd.to_datetime(d.date.iloc[j]).month<=6 else 'diagnostic',
            'actual_delta_kg':float(d.delta_emissions.iloc[j]),'point_kg':float(predicted),
            'error_kg':error,'action_l1_kwh':float(scale),
            'positive_error_per_kwh':max(0.,error)/scale if scale>1e-6 else 0.})
out=pd.DataFrame(rows)
out.to_csv(ROOT/'tables/margin_calibration.csv',index=False)
train=out[out.year_half=='calibration'].positive_error_per_kwh.to_numpy()
margin=float(np.quantile(train,.9,method='higher'))
record={'rule':'Pooled 90th percentile of positive (actual model delta - point surrogate)/L1 intervention on sampled January-June 2023 CV8 schedules; zero-action days score zero.',
    'margin_kg_per_kwh':margin,'train_days':len(train),'diagnostic_days':int((out.year_half=='diagnostic').sum()),
    'diagnostic_coverage_of_fixed_cv8_schedules':float((out[out.year_half=='diagnostic'].positive_error_per_kwh<=margin+1e-10).mean()),
    'guarantee':'None out of sample. The new MARGIN schedule is different from the calibration CV8 schedule; dependence, model error and regime shift preclude a coverage theorem.'}
(ROOT/'audit/margin_calibration.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
