"""Audit state continuity and forecast origins across skipped reporting days."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
folders=[ROOT/'results'/f'confirmation_seed{seed}_2025_{regime}'
    for seed in (314159,271828)
    for regime in ('coal_first','gas_first','solar_rich')]
folders.append(ROOT/'results/eia_confirmation_2024')
folders.append(ROOT/'results/v3_eia_confirmation_2024')
rows=[]
source_cache={}
for folder in folders:
    for cfgpath in sorted(folder.glob('*_config.json')):
        cfg=json.loads(cfgpath.read_text());p=cfg['policy'];setting=cfg['settings']
        h=pd.read_csv(folder/f'{p}_hourly.csv.gz')
        d=pd.read_csv(folder/f'{p}_daily.csv')
        starts=h.iloc[::24].reset_index(drop=True)
        ends=h.iloc[23::24].reset_index(drop=True)
        assert len(starts)==len(ends)==len(d)
        dates=pd.to_datetime(d.date,utc=True)
        step=(dates.diff().dropna()/pd.Timedelta(days=1)).to_numpy()
        assert np.all(step==4)
        if cfg['source_file'] not in source_cache:
            source_cache[cfg['source_file']]=pd.read_csv(ROOT/cfg['source_file'],usecols=['timestamp_utc'])
        source=source_cache[cfg['source_file']]
        lookup={stamp:i for i,stamp in enumerate(source.timestamp_utc)}
        selected=np.array([lookup[stamp] for stamp in d.date])
        history_ok=all(i>=168 and i+24<=len(source) and
            (pd.to_datetime(source.timestamp_utc.iloc[i-168:i],utc=True).diff().dropna()==pd.Timedelta(hours=1)).all()
            for i in selected)
        assert history_ok
        soc_gap=float(np.max(np.abs(starts.soc_start.iloc[1:].to_numpy()-ends.soc_end.iloc[:-1].to_numpy())))
        carbon_gap=float(np.max(np.abs(starts.carbon_start.iloc[1:].to_numpy()-ends.carbon_end.iloc[:-1].to_numpy())))
        initial_soc=float(starts.soc_start.iloc[0]);initial_carbon=float(starts.carbon_start.iloc[0])
        end_state=float(np.max(np.abs(ends.soc_end.to_numpy()-setting['capacity']/2)))
        assert soc_gap<1e-6 and carbon_gap<1e-6 and end_state<1e-6
        assert abs(initial_soc-setting['capacity']/2)<1e-6
        assert abs(initial_carbon-.6*initial_soc)<1e-6
        carbon_vs_reset=np.abs(starts.carbon_start.to_numpy()-.6*initial_soc)
        rows.append({'run':folder.name,'policy':p,'days':len(d),'calendar_spacing_days':4,
            'history_contiguous_7days':history_ok,'initial_soc_kwh':initial_soc,
            'initial_carbon_kg':initial_carbon,'max_soc_gap_kwh':soc_gap,
            'max_carbon_gap_kg':carbon_gap,'max_daily_terminal_energy_error_kwh':end_state,
            'max_carbon_departure_from_episode_reset_kg':float(carbon_vs_reset.max()),
            'mean_carbon_departure_from_episode_reset_kg':float(carbon_vs_reset.mean())})
out=pd.DataFrame(rows);out.to_csv(ROOT/'tables/v3_state_audit.csv',index=False)
report={'model':'Schedules are computed only for every fourth day, with full chronological historical observations used for forecasts. The solver does not optimize the three intervening days.',
    'equivalent_skipped_day_embedding':'Under the declared no-self-discharge battery model, skipped days may be embedded as idle storage and reference flexible tasks. This preserves the terminal SOC and carried carbon inventory. It is an assumption, not simulated intervening operation.',
    'classification':'Periodically active sampled-day evaluation with carried attributional state; neither full continuous optimized dispatch nor independent reset episodes.',
    'initial_state':'SOC = capacity/2 and attributed carbon = 0.6 kg/kWh times opening SOC at first selected day; battery SOC returns to capacity/2 daily; carbon inventory is carried to next selected day.',
    'causal_forecast':'The preceding 168 hourly rows are used at each selected-day issue time, including observations from skipped evaluation days.',
    'effect_on_outputs':'Changing the carbon inventory reset convention would affect attributional ledger fields; optimizer, physical meter exchange, real expense and consequential emissions do not use opening carbon inventory. No cost/emission conclusion changes under an idle skipped-day embedding.',
    'runs_checked':len(out),'max_state_gap':float(max(out.max_soc_gap_kwh.max(),out.max_carbon_gap_kg.max())),
    'max_carbon_departure_from_independent_reset':float(out.max_carbon_departure_from_episode_reset_kg.max()),
    'legacy_ercot_max_departure_kg':float(out[out.run=='eia_confirmation_2024'].max_carbon_departure_from_episode_reset_kg.max()),
    'corrected_ercot_max_departure_kg':float(out[out.run=='v3_eia_confirmation_2024'].max_carbon_departure_from_episode_reset_kg.max())}
(ROOT/'audit/v3_state_protocol.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('classification','runs_checked','max_state_gap','max_carbon_departure_from_independent_reset')}))
