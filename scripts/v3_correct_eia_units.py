"""Correct EIA average-factor and baseline units without overwriting V2 inputs."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
records=[]
for year in (2023,2024):
    old=ROOT/'data'/f'eia_erco_2022_{year}_frame.csv.gz'
    new=ROOT/'data'/f'eia_erco_2022_{year}_frame_corrected.csv.gz'
    if new.exists():raise SystemExit(f'Corrected frame already exists: {new}')
    frame=pd.read_csv(old)
    old_avg=frame.aef_eia_erco.to_numpy().copy()
    old_base=frame.eia_baseline_kg.to_numpy().copy()
    frame['aef_eia_erco']/=1000.
    frame['eia_baseline_kg']/=1000.
    assert np.allclose(frame.eia_baseline_kg/frame.native,frame.aef_eia_erco,rtol=1e-10)
    for column in frame.columns:
        if column not in ('aef_eia_erco','eia_baseline_kg'):
            assert np.array_equal(frame[column].to_numpy(),pd.read_csv(old,usecols=[column])[column].to_numpy())
    frame.to_csv(new,index=False,compression='gzip')
    records.append({'year':year,'source':str(old.relative_to(ROOT)),
       'source_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
       'corrected':str(new.relative_to(ROOT)),
       'corrected_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),
       'rows':len(frame),'old_avg_range':[float(old_avg.min()),float(old_avg.max())],
       'corrected_avg_range':[float(frame.aef_eia_erco.min()),float(frame.aef_eia_erco.max())],
       'old_baseline_mean_kg':float(old_base.mean()),
       'corrected_baseline_mean_kg':float(frame.eia_baseline_kg.mean())})
report={'unit_identity':'metric tonnes/MWh = kg/kWh numerically; 0.2 kW per regional MW implies 0.2 kg per reported tonne in the scaled baseline.',
        'error':'V2 used 1000*CO2_tonnes/demand_MW for average intensity and 0.2*1000*CO2_tonnes for scaled baseline, inflating both 1000-fold. The associational marginal derivative and curvature were already in kg/kWh and remain unchanged.',
        'affected':'ERCOT-input carbon attribution and all carbon-priced controller schedules; original V2 results remain preserved for audit.',
        'frames':records}
(ROOT/'audit/v3_eia_unit_correction.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{'year':r['year'],'rows':r['rows'],'avg_range':r['corrected_avg_range']} for r in records]))
