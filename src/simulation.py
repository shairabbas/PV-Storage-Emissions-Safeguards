from dataclasses import asdict
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .data import ROOT, forecast, residual_blocks, dispatch
from .optimization import Settings, independent_bills, optimize
from .accounting import ledger, settlement

POLICIES=('B0','M0','M1','S0','S1','B3','CV8','CV32','CV128',
          'CV32_SEAS','CV32_S11','CV32_S23','MARGIN','G_worst','ROBOX')


def _validate_eia_factor_units(df):
    """Boundary check: scaled tonnes/MWh are numerically kg/kWh."""
    factor=df.aef_eia_erco.to_numpy(dtype=float)
    baseline=df.eia_baseline_kg.to_numpy(dtype=float)
    native=df.native.to_numpy(dtype=float)
    if (not np.isfinite(factor).all() or not np.isfinite(baseline).all()
            or not np.isfinite(native).all() or not ((native>0).all())
            or not ((factor>=0)&(factor<=1.5)).all()
            or not np.allclose(baseline/native,factor,rtol=1e-10,atol=1e-10)):
        raise ValueError('ERCOT-input average factor/baseline units inconsistent: require kg/kWh and kg/hour')


def _advance_idle_reference(df, first, last, regime, cfg, soc, carbon):
    """Model every intervening date: fixed tasks, no storage action or self-discharge."""
    if (last-first)%24:raise ValueError('Evaluation dates must be complete UTC days apart')
    count=0
    for start in range(first,last,24):
        day=df.iloc[start:start+24]
        if len(day)!=24:raise ValueError('Incomplete intervening UTC day')
        times=pd.to_datetime(day.timestamp_utc,utc=True)
        if not (times.diff().dropna()==pd.Timedelta(hours=1)).all():
            raise ValueError('Nonconsecutive intervening hours')
        if start and times.iloc[0]-pd.Timestamp(df.timestamp_utc.iloc[start-1])!=pd.Timedelta(hours=1):
            raise ValueError('Unmodelled calendar gap before an intervening day')
        fbase=np.array([day[f'flex0_{i}'].to_numpy() for i in range(3)])*cfg.demand_scale
        critical=np.array([day[f'critical_{i}'].to_numpy() for i in range(3)])*cfg.demand_scale
        critical+=fbase*(1-cfg.flex_scale)
        fixed=fbase*cfg.flex_scale
        pv=np.array([day[f'pv_{i}'].to_numpy() for i in range(3)])*cfg.pv_scale
        zero=np.zeros(24)
        acc,new_soc,new_carbon=ledger(critical+fixed,pv,zero,zero,
            day[f'aef_{regime}'].to_numpy(),soc,carbon,cfg.efficiency,cfg.auxiliary)
        if (abs(new_soc-soc)>1e-8 or abs(new_carbon-carbon)>1e-8
                or np.max(np.abs(acc['energy_residual']))>1e-8
                or np.max(np.abs(acc['carbon_residual']))>1e-8
                or max(acc['import'].max(),acc['export'].max())>cfg.grid_limit+1e-8):
            raise AssertionError('Intervening idle/reference operation is physically infeasible')
        soc,carbon=new_soc,new_carbon
        count+=1
    return soc,carbon,count


def simulate(df, year, regime, policy, cfg=None, starts=None, tag=None, source_file=None):
    cfg=cfg or Settings()
    if regime=='eia_erco':_validate_eia_factor_units(df)
    if policy in ('M0','M1') and (cfg.capacity!=0 or cfg.power!=0):
        raise ValueError('Matched no-storage baselines require zero storage capacity and power')
    seasons=range(4) if cfg.scenario_seasonal else (None,)
    block_map={season:residual_blocks(df,regime,cfg.scenario_count,
        cfg.scenario_seed,season,('2021','2022') if cfg.scenario_count>8 or cfg.scenario_seasonal else ('2022',))
        for season in seasons}
    if cfg.shuffle_residual_hours:
        block_map={key:(blocks[:,np.random.default_rng(8103).permutation(24)],dates)
            for key,(blocks,dates) in block_map.items()}
    mask=df.timestamp_utc.str.startswith(str(year))
    if starts is None: starts=np.flatnonzero(mask)[::24]
    static=float(df.loc[df.timestamp_utc.str.startswith(('2021','2022')),f'aef_{regime}'].mean())
    soc=cfg.capacity/2; carbon=soc*.6
    daily=[]; hourly=[]; previous_end=None; intervening_idle_days=0
    for start in starts:
        if previous_end is not None:
            soc,carbon,added=_advance_idle_reference(df,previous_end,int(start),
                regime,cfg,soc,carbon)
            intervening_idle_days+=added
        day=df.iloc[start:start+24]
        assert len(day)==24
        critical=np.array([day[f'critical_{i}'] for i in range(3)])*cfg.demand_scale
        f0=np.array([day[f'flex0_{i}'] for i in range(3)])*cfg.demand_scale*cfg.flex_scale
        # Changing flex_scale reallocates service to critical rather than removing it.
        critical += np.array([day[f'flex0_{i}'] for i in range(3)])*cfg.demand_scale*(1-cfg.flex_scale)
        pv=np.array([day[f'pv_{i}'] for i in range(3)])*cfg.pv_scale
        buy=day.price_buy.to_numpy(); sell=day.price_sell.to_numpy()
        aef=day[f'aef_{regime}'].to_numpy()
        mef=day[f'mef_{regime}'].to_numpy()
        season=(pd.to_datetime(day.timestamp_utc.iloc[0],utc=True).month-1)//3 if cfg.scenario_seasonal else None
        blocks,block_dates=block_map[season]
        if policy in ('B0','M0','ROBOX'):
            schedule={'charge':np.zeros(24),'discharge':np.zeros(24),'flexible':f0.copy(),
                'status':'reference; no solve','status_code':0,'fallback':False,'runtime':0.,
                'gap':0.,'dual_bound':None,'objective':None,'surrogate_cvar':0.,
                'surrogate_mean':0.,'surrogate_worst':0.,'guard':'none'}
        else:
            if policy=='B5': cp,pp,af,mf=critical,pv,aef,mef
            else:
                cp=np.array([forecast(df,start,f'critical_{i}') for i in range(3)])*cfg.demand_scale
                cp*=cfg.critical_forecast_bias
                # Nonflexible task fraction is calendar-known at issue time.
                cp+=np.array([day[f'flex0_{i}'] for i in range(3)])*cfg.demand_scale*(1-cfg.flex_scale)
                pp=np.array([forecast(df,start,f'pv_{i}') for i in range(3)])*cfg.pv_scale
                pp*=cfg.pv_forecast_bias
                af=forecast(df,start,f'aef_{regime}')
                mf=forecast(df,start,f'mef_{regime}')
                mf=np.clip(mf*cfg.carbon_forecast_bias,0,.95)
            if policy=='B2': af=np.full(24,static)
            schedule=optimize(cp,f0,pp,buy,sell,af,mf,blocks,policy,cfg,soc)
        c,d,f=schedule['charge'],schedule['discharge'],schedule['flexible']
        # Realised critical loads and renewable availability affect only meter balancing.
        load=critical+f
        acc,soc,carbon=ledger(load,pv,c,d,aef,soc,carbon,cfg.efficiency,cfg.auxiliary)
        billed_import=acc['import'].copy(); billed_export=acc['export'].copy()
        if policy=='B0':
            individual_q=critical+f0-pv
            # Independent billing does not change the common physical/carbon boundary.
            billed_import=np.maximum(individual_q,0).sum(axis=0)
            billed_export=np.maximum(-individual_q,0).sum(axis=0)
        bills0=independent_bills(critical,f0,pv,buy,sell)
        bill=billed_import*buy-billed_export*sell
        depreciation=cfg.degradation*(c+d)
        discomfort=cfg.discomfort*np.abs(f-f0).sum(axis=0)
        real=bill+depreciation+discomfort
        q=load.sum(axis=0)-pv.sum(axis=0)+(1+cfg.auxiliary)*c-(1-cfg.auxiliary)*d
        q0=(critical+f0-pv).sum(axis=0)
        if regime=='eia_erco':
            reference=day.eia_baseline_kg.to_numpy()
            v=q-q0
            delta=day.mef_eia_erco.to_numpy()*v+day.eia_curvature.to_numpy()*v*v
            emitted=reference+delta
        else:
            back=day[f'background_{regime}'].to_numpy()
            emitted,_=dispatch(back+q,regime); reference,_=dispatch(back+q0,regime)
            delta=emitted-reference
        settled=settlement(bills0,float(real.sum()))
        record={'year':year,'regime':regime,'policy':policy,'date':day.timestamp_utc.iloc[0],
            'real_cost':float(real.sum()),'reference_cost':float(bills0.sum()),
            'grid_bill':float(bill.sum()),'degradation':float(depreciation.sum()),
            'discomfort':float(discomfort.sum()),'delta_emissions':float(delta.sum()),
            'system_emissions':float(emitted.sum()),'reference_emissions':float(reference.sum()),
            'attributed_imports':float(acc['source_carbon'].sum()),
            'attributed_load':float(acc['load_carbon'].sum()),
            'attributed_losses':float(acc['loss_carbon'].sum()),
            'attributed_aux':float(acc['aux_carbon'].sum()),
            'attributed_exports':float(acc['export_carbon'].sum()),
            'carbon_inventory_change':float(acc['carbon_end'][-1]-acc['carbon_start'][0]),
            'throughput':float((c+d).sum()),'pv_available':float(pv.sum()),
            'imports':float(acc['import'].sum()),'exports':float(acc['export'].sum()),
            'critical_energy':float(critical.sum()),'flexible_energy':float(f.sum()),
            'task_error':float(np.max(np.abs(f.sum(axis=1)-f0.sum(axis=1)))),
            'carbon_error':float(np.max(np.abs(acc['carbon_residual']))),
            'energy_error':float(np.max(np.abs(acc['energy_residual']))),
            'end_energy_error':float(soc-cfg.capacity/2),
            'operator_margin':settled['operator_margin'],'budget_error':settled['budget_residual'],
            'minimum_benefit':float(settled['benefits'].min()),'unserved_energy':0.,
            'renewable_curtailment':0.,'max_meter_power':float(max(acc['import'].max(),acc['export'].max()))}
        for key in ('status','status_code','fallback','runtime','gap','dual_bound','objective',
                    'surrogate_cvar','surrogate_mean','surrogate_worst','guard'):
            record[key]=schedule[key]
        for i in range(3):
            record[f'participant_{i}_bill']=float(settled['charges'][i])
            record[f'participant_{i}_benefit']=float(settled['benefits'][i])
            record[f'participant_{i}_carbon']=float(acc['participant_carbon'][i].sum())
        daily.append(record)
        h=pd.DataFrame({k:v for k,v in acc.items() if k!='participant_carbon'})
        h['timestamp_utc']=day.timestamp_utc.to_numpy(); h['charge']=c; h['discharge']=d
        h['real_cost']=real; h['delta_emissions']=delta; h['q_reference']=q0; h['q_proposed']=q
        h['aef']=aef; h['pv_total']=pv.sum(axis=0); h['load_total']=load.sum(axis=0)
        for i in range(3):
            h[f'critical_{i}']=critical[i]; h[f'flexible_{i}']=f[i]; h[f'flex0_{i}']=f0[i]; h[f'pv_{i}']=pv[i]
        hourly.append(h)
        previous_end=int(start)+24
    result=pd.DataFrame(daily); detail=pd.concat(hourly,ignore_index=True)
    if np.max(np.abs(detail.carbon_residual))>1e-6 or np.max(np.abs(detail.energy_residual))>1e-6:
        raise AssertionError('Ledger conservation failed')
    if result.max_meter_power.max()>cfg.grid_limit+1e-5:
        raise AssertionError('Actual grid limit violated: no claim of feasibility permitted')
    if result.task_error.max()>1e-4 or abs(result.end_energy_error).max()>1e-4:
        raise AssertionError('Service/terminal boundary mismatch')
    directory=ROOT/'results'/(tag or f'{year}_{regime}')
    directory.mkdir(parents=True,exist_ok=True)
    result.to_csv(directory/f'{policy}_daily.csv',index=False)
    detail.to_csv(directory/f'{policy}_hourly.csv.gz',index=False,compression='gzip')
    (directory/f'{policy}_config.json').write_text(json.dumps({'settings':asdict(cfg),
        'residual_dates_development_only':{str(k):dates for k,(_,dates) in block_map.items()},
        'year':year,'regime':regime,'source_file':source_file or 'data/benchmark.csv.gz',
        'policy':policy,'hours':len(detail),'days':len(result),
        'intervening_idle_days_modelled':intervening_idle_days},indent=2))
    return result
