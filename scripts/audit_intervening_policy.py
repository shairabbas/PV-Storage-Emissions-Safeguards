"""Complete saved selected-day policies with explicit idle/reference skipped days."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.accounting import ledger
from src.optimization import independent_bills

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results'
folders=[RESULTS/f'confirmation_seed{seed}_2025_{regime}'
         for seed in (314159,271828)
         for regime in ('coal_first','gas_first','solar_rich')]
folders += [RESULTS/'v3_eia_confirmation_2024']
folders += [RESULTS/f'v3_cv128_seed{seed}_{regime}_draw{draw}'
            for seed in (314159,271828)
            for regime in ('coal_first','gas_first','solar_rich')
            for draw in (11,23)]
cache={};rows=[]
for folder in folders:
    for config_path in sorted(folder.glob('*_config.json')):
        cfg_record=json.loads(config_path.read_text())
        policy=cfg_record['policy'];cfg=cfg_record['settings'];regime=cfg_record['regime']
        source=cfg_record['source_file'].replace('\\','/')
        if source not in cache:
            frame=pd.read_csv(ROOT/source)
            cache[source]=(frame,{s:i for i,s in enumerate(frame.timestamp_utc)})
        frame,lookup=cache[source]
        d=pd.read_csv(folder/f'{policy}_daily.csv')
        h=pd.read_csv(folder/f'{policy}_hourly.csv.gz')
        starts=[lookup[t] for t in d.date]
        assert len(h)==24*len(d)==cfg_record['hours']
        assert len(set(np.diff(starts)))==1
        soc=cfg['capacity']/2;carbon=soc*.6
        skipped=0;max_state=0.;max_meter=0.;max_conservation=0.;max_service=0.
        max_reference_exchange_error=0.
        skipped_shared_expense=0.;skipped_independent_expense=0.
        first_stamp=pd.Timestamp(d.date.iloc[0]);last_stamp=pd.Timestamp(d.date.iloc[-1])
        for j,start in enumerate(starts):
            if j:
                previous=starts[j-1]
                for mid in range(previous+24,start,24):
                    day=frame.iloc[mid:mid+24]
                    assert len(day)==24
                    times=pd.to_datetime(day.timestamp_utc,utc=True)
                    assert (times.diff().dropna()==pd.Timedelta(hours=1)).all()
                    assert pd.Timestamp(day.timestamp_utc.iloc[0])-pd.Timestamp(frame.timestamp_utc.iloc[mid-24])==pd.Timedelta(days=1)
                    flex0=np.array([day[f'flex0_{i}'].to_numpy() for i in range(3)])*cfg['demand_scale']*cfg['flex_scale']
                    critical=np.array([day[f'critical_{i}'].to_numpy() for i in range(3)])*cfg['demand_scale']
                    critical += np.array([day[f'flex0_{i}'].to_numpy() for i in range(3)])*cfg['demand_scale']*(1-cfg['flex_scale'])
                    pv=np.array([day[f'pv_{i}'].to_numpy() for i in range(3)])*cfg['pv_scale']
                    zero=np.zeros(24);loads=critical+flex0
                    acc,soc2,carbon2=ledger(loads,pv,zero,zero,day[f'aef_{regime}'].to_numpy(),
                        soc,carbon,cfg['efficiency'],cfg['auxiliary'])
                    max_state=max(max_state,abs(soc2-soc),abs(carbon2-carbon))
                    max_conservation=max(max_conservation,float(np.abs(acc['energy_residual']).max()),
                                         float(np.abs(acc['carbon_residual']).max()))
                    max_meter=max(max_meter,float(max(acc['import'].max(),acc['export'].max())))
                    max_service=max(max_service,float(np.abs(loads-critical-flex0).max()))
                    q0=loads.sum(axis=0)-pv.sum(axis=0)
                    max_reference_exchange_error=max(max_reference_exchange_error,
                        float(np.abs(acc['import']-acc['export']-q0).max()))
                    buy=day.price_buy.to_numpy();sell=day.price_sell.to_numpy()
                    skipped_shared_expense+=float(acc['import']@buy-acc['export']@sell)
                    skipped_independent_expense+=float(independent_bills(critical,flex0,pv,buy,sell).sum())
                    soc,carbon=soc2,carbon2;skipped+=1
            seg=h.iloc[24*j:24*(j+1)]
            max_state=max(max_state,abs(seg.soc_start.iloc[0]-soc),
                          abs(seg.carbon_start.iloc[0]-carbon))
            soc=float(seg.soc_end.iloc[-1]);carbon=float(seg.carbon_end.iloc[-1])
        assert max_state<1e-7,(folder,policy,max_state)
        assert max_conservation<1e-7,(folder,policy,max_conservation)
        assert max_meter<=cfg['grid_limit']+1e-7,(folder,policy,max_meter)
        assert max_service<1e-7
        assert max_reference_exchange_error<1e-7
        assert skipped==starts[-1]//24-starts[0]//24+1-len(starts)
        rows.append({'run':folder.name,'policy':policy,'source_file':source,
            'first_selected':str(first_stamp),'last_selected':str(last_stamp),
            'selected_days':len(starts),'explicit_skipped_days':skipped,
            'max_state_gap':max_state,'max_conservation_error':max_conservation,
            'max_skipped_meter_kw':max_meter,'max_service_error':max_service,
            'max_reference_exchange_error':max_reference_exchange_error,
            'skipped_shared_expense_usd':skipped_shared_expense,
            'skipped_independent_expense_usd':skipped_independent_expense,
            'full_window_expense_usd':float(d.real_cost.sum())+
                (skipped_independent_expense if policy=='B0' else skipped_shared_expense)})
out=pd.DataFrame(rows)
out.to_csv(ROOT/'tables/final_timeline_completion.csv',index=False)
report={'classification':'Explicit intermittent policy: idle storage and fixed reference tasks on every intervening day; selected-day schedules and all exogenous 168-hour forecasts retained.',
    'model_assumptions':'No self-discharge; auxiliary use is proportional to charge/discharge and thus zero while idle. Battery energy and attributed carbon stay constant on skipped days. No unmodelled storage action is permitted.',
    'runs':len(out),'selected_days':int(out.selected_days.sum()),
    'completed_skipped_days':int(out.explicit_skipped_days.sum()),
    'max_state_gap':float(out.max_state_gap.max()),
    'max_conservation_error':float(out.max_conservation_error.max()),
    'max_skipped_meter_kw':float(out.max_skipped_meter_kw.max()),
    'max_service_error':float(out.max_service_error.max()),
    'max_reference_exchange_error':float(out.max_reference_exchange_error.max()),
    'calendar_note':'Full-window expense includes reference operation on skipped dates; paper outcomes are per selected active day. All compared policies use identical selected and skipped calendars within each realization.'}
(ROOT/'audit/final_timeline_completion.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
