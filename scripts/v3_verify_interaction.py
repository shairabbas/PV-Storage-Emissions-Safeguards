"""Reconstruct the four-cost interaction directly from saved daily expenses."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
POLICIES=('B0','M0','M1','S0','S1')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

rows=[];inputs=[]
for seed in (314159,271828):
    for regime in ('coal_first','gas_first','solar_rich'):
        folder=ROOT/'results'/f'confirmation_seed{seed}_2025_{regime}'
        saved={}
        for policy in POLICIES:
            path=folder/f'{policy}_daily.csv'
            saved[policy]=pd.read_csv(path)
            inputs.append({'file':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':digest(path)})
        dates=saved['M0'].date.to_numpy()
        assert len(dates)==92
        assert all(np.array_equal(x.date.to_numpy(),dates) for x in saved.values())
        c={p:float(saved[p].real_cost.sum()) for p in POLICIES}
        meter=(c['B0']-c['M0'])/92
        flex=(c['M0']-c['M1'])/92
        storage_fixed=(c['M0']-c['S0'])/92
        storage_flex=(c['M1']-c['S1'])/92
        interaction=storage_flex-storage_fixed
        dual=(c['S0']-c['S1']-c['M0']+c['M1'])/92
        assert abs(interaction-dual)<1e-10
        rows.append({'demand_seed':seed,'regime':regime,'days':92,
            **{f'C_{p}_total':c[p] for p in POLICIES},
            'meter_saving_per_day':meter,'flex_saving_no_storage_per_day':flex,
            'storage_saving_fixed_per_day':storage_fixed,
            'storage_saving_flex_per_day':storage_flex,
            'interaction_per_day':interaction,'dual_expression_per_day':dual})
out=pd.DataFrame(rows)
out.to_csv(ROOT/'tables/v3_isolation_verified.csv',index=False)
report={'definition':'(C_M1-C_S1)-(C_M0-C_S0), divided by 92 sampled days per seed',
    'equivalent_definition':'(C_S0-C_S1)-(C_M0-C_M1), divided by 92',
    'mean_interaction_usd_per_day':float(out.interaction_per_day.mean()),
    'min_per_seed':float(out.interaction_per_day.min()),
    'max_per_seed':float(out.interaction_per_day.max()),
    'version_2_error':'Version-2 Table 1 printed the opposite sign, (C_M0-C_M1)-(C_S0-C_S1). Costs and other savings were correct.',
    'sources':inputs}
(ROOT/'audit/v3_interaction_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('mean_interaction_usd_per_day','min_per_seed','max_per_seed')}))
