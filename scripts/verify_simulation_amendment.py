"""Re-execute representative saved policies under explicit idle-day simulation."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.optimization import Settings
from src.simulation import simulate

ROOT=Path(__file__).resolve().parents[1]
cases=[('confirmation_seed314159_2025_coal_first','ROBOX','final_timeline_smoke_synthetic'),
       ('v3_eia_confirmation_2024','B3','final_timeline_smoke_eia')]
records=[]
for original,policy,tag in cases:
    src=ROOT/'results'/original
    config=json.loads((src/f'{policy}_config.json').read_text())
    frame=pd.read_csv(ROOT/config['source_file'].replace('\\','/'))
    old=pd.read_csv(src/f'{policy}_daily.csv')
    mapping={date:i for i,date in enumerate(frame.timestamp_utc)}
    starts=np.array([mapping[date] for date in old.date])
    if (ROOT/'results'/tag).exists():raise SystemExit(f'Smoke output exists: {tag}')
    new=simulate(frame,config['year'],config['regime'],policy,
                 Settings(**config['settings']),starts,tag,config['source_file'])
    old_h=pd.read_csv(src/f'{policy}_hourly.csv.gz')
    new_h=pd.read_csv(ROOT/'results'/tag/f'{policy}_hourly.csv.gz')
    cols=['charge','discharge','q_proposed','q_reference','soc_start','soc_end',
          'carbon_start','carbon_end','real_cost','delta_emissions']
    max_error=float(np.abs(old_h[cols].to_numpy()-new_h[cols].to_numpy()).max())
    assert max_error<1e-7,(original,policy,max_error)
    assert np.allclose(old.real_cost,new.real_cost,rtol=0,atol=1e-7)
    assert np.allclose(old.delta_emissions,new.delta_emissions,rtol=0,atol=1e-7)
    new_config=json.loads((ROOT/'results'/tag/f'{policy}_config.json').read_text())
    records.append({'original_run':original,'policy':policy,'selected_days':len(old),
        'intervening_idle_days_modelled':new_config['intervening_idle_days_modelled'],
        'maximum_saved_hourly_difference':max_error})
(ROOT/'audit/final_timeline_amendment_smoke.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
