"""Compare active-day and fully completed intermittent-policy expense boundaries."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
x=pd.read_csv(ROOT/'tables/final_timeline_completion.csv')
rows=[]
for run,g in x.groupby('run'):
    if not (run.startswith('confirmation_seed') or run=='v3_eia_confirmation_2024'):
        continue
    a=g.set_index('policy')
    costs=a.full_window_expense_usd
    days=int(a.selected_days.iloc[0]+a.explicit_skipped_days.iloc[0])
    selected=int(a.selected_days.iloc[0])
    assert (a.selected_days==selected).all()
    assert (a.explicit_skipped_days==days-selected).all()
    interaction=(costs.M1-costs.S1)-(costs.M0-costs.S0)
    active={p:float(pd.read_csv(ROOT/'results'/run/f'{p}_daily.csv').real_cost.sum())
            for p in ('M0','M1','S0','S1')}
    active_interaction=(active['M1']-active['S1'])-(active['M0']-active['S0'])
    assert np.isclose(interaction,active_interaction,atol=1e-7)
    rows.append({'run':run,'calendar_days_first_to_last_selected':days,
        'selected_days':selected,'skipped_idle_days':days-selected,
        'B0_full_usd':costs.B0,'M0_full_usd':costs.M0,
        'M1_full_usd':costs.M1,'S0_full_usd':costs.S0,'S1_full_usd':costs.S1,
        'meter_aggregation_saving_full_usd':costs.B0-costs.M0,
        'meter_aggregation_saving_full_usd_per_calendar_day':(costs.B0-costs.M0)/days,
        'flexibility_saving_full_usd':costs.M0-costs.M1,
        'storage_fixed_saving_full_usd':costs.M0-costs.S0,
        'storage_flexible_saving_full_usd':costs.M1-costs.S1,
        'interaction_full_usd':interaction,
        'interaction_usd_per_selected_day':interaction/selected})
out=pd.DataFrame(rows)
out.to_csv(ROOT/'tables/final_full_window_isolation.csv',index=False)
print(out[['run','calendar_days_first_to_last_selected',
    'meter_aggregation_saving_full_usd_per_calendar_day',
    'interaction_usd_per_selected_day']].to_string(index=False))
