"""Independent saved-schedule replay; does not import optimizer or ledger."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def replay(directory,policy,source):
    config=json.loads((directory/f'{policy}_config.json').read_text())
    cfg=config['settings']; regime=config['regime']
    h=pd.read_csv(directory/f'{policy}_hourly.csv.gz')
    daily=pd.read_csv(directory/f'{policy}_daily.csv')
    base=source.set_index('timestamp_utc').loc[h.timestamp_utc]
    c=h.charge.to_numpy(); d=h.discharge.to_numpy(); eta=cfg['efficiency']; aux=cfg['auxiliary']
    starting=cfg['capacity']/2
    state=starting+np.cumsum(eta*c-d/eta)
    errs={'stored_energy':float(np.max(np.abs(state-h.soc_end))),
        'state_continuity':float(np.max(np.abs(h.soc_start.iloc[1:].to_numpy()-h.soc_end.iloc[:-1].to_numpy()))) if len(h)>1 else 0,
        'simultaneous_battery':float(np.max(np.minimum(c,d))),
        'lower_storage':float(max(0,-state.min())),
        'upper_storage':float(max(0,state.max()-cfg['capacity'])),
        'charge_limit':float(max(0,c.max()-cfg['power'])),
        'discharge_limit':float(max(0,d.max()-cfg['power']))}
    f=h[[f'flexible_{i}' for i in range(3)]].to_numpy()
    f0=h[[f'flex0_{i}' for i in range(3)]].to_numpy()
    crit=h[[f'critical_{i}' for i in range(3)]].to_numpy()
    pv=h[[f'pv_{i}' for i in range(3)]].to_numpy()
    raw_crit=base[[f'critical_{i}' for i in range(3)]].to_numpy()
    raw_flex=base[[f'flex0_{i}' for i in range(3)]].to_numpy()
    raw_pv=base[[f'pv_{i}' for i in range(3)]].to_numpy()
    expected_crit=(raw_crit+raw_flex*(1-cfg['flex_scale']))*cfg['demand_scale']
    errs['exogenous_critical']=float(np.max(np.abs(crit-expected_crit)))
    errs['exogenous_tasks']=float(np.max(np.abs(f0-raw_flex*cfg['flex_scale']*cfg['demand_scale'])))
    errs['exogenous_pv']=float(np.max(np.abs(pv-raw_pv*cfg['pv_scale'])))
    errs['nonnegative_carbon']=float(max(0,-h.carbon_end.min()))
    if policy in ('M0','M1'):
        errs['no_storage']=float(np.max(np.abs(np.r_[c,d,h.soc_end.to_numpy()])))
    if policy=='ROBOX':
        errs['idle_storage']=float(np.max(np.abs(np.r_[c,d])))
    if policy in ('M0','S0','ROBOX'):
        errs['fixed_tasks']=float(np.max(np.abs(f-f0)))
    q=(crit+f-pv).sum(axis=1)+c-d+aux*(c+d)
    q0=(crit+f0-pv).sum(axis=1)
    if len(h):
        gi=np.maximum(q,0); ge=np.maximum(-q,0)
        errs['simultaneous_grid']=float(np.max(np.minimum(gi,ge)))
        Q=.6*starting; S=starting; carbon_error=0.; balance_error=0.
        for t in range(len(h)):
            previous=Q
            intensity=Q/S if S>1e-9 else 0.
            supply=gi[t]+pv[t].sum()+d[t]
            mix=(gi[t]*h.aef.iloc[t]+d[t]*intensity)/supply if supply>1e-10 else 0.
            Q+=eta*c[t]*mix-d[t]*intensity/eta
            S+=eta*c[t]-d[t]/eta
            carbon_error=max(carbon_error,abs(Q-h.carbon_end.iloc[t]))
            allocated=(crit[t]+f[t]).sum()*mix+ge[t]*mix+(1-eta)*c[t]*mix
            allocated+=(1/eta-1)*d[t]*intensity+aux*(c[t]+d[t])*mix
            balance_error=max(balance_error,abs(gi[t]*h.aef.iloc[t]+previous-Q-allocated))
    errs['carbon_inventory']=float(carbon_error); errs['carbon_identity']=float(balance_error)
    errs['meter_import']=float(np.max(np.abs(gi-h['import'])))
    errs['meter_export']=float(np.max(np.abs(ge-h['export'])))
    errs['connection']=float(max(0,max(gi.max(),ge.max())-cfg['grid_limit']))
    errs['tasks']=float(np.max(np.abs(f.reshape(-1,24,3).sum(axis=1)-f0.reshape(-1,24,3).sum(axis=1))))
    # Separately implement the merit-order evaluator as clipped closed-form blocks.
    if regime=='eia_erco':
        intervention=q-q0
        delta=base.mef_eia_erco.to_numpy()*intervention+base.eia_curvature.to_numpy()*intervention**2
    else:
        ef=(.4,.95,.75) if regime=='gas_first' else (.95,.4,.75)
        def emission(x):
            return ef[0]*np.clip(x,0,6000)+ef[1]*np.clip(x-6000,0,6000)+ef[2]*np.clip(x-12000,0,8000)
        back=base[f'background_{regime}'].to_numpy()
        delta=emission(back+q)-emission(back+q0)
    errs['counterfactual']=float(np.max(np.abs(delta-h.delta_emissions)))
    cost=gi*base.price_buy.to_numpy()-ge*base.price_sell.to_numpy()
    if policy=='B0':
        cost=np.maximum(crit+f-pv,0).sum(axis=1)*base.price_buy.to_numpy()
        cost-=np.maximum(pv-crit-f,0).sum(axis=1)*base.price_sell.to_numpy()
    cost+=cfg['degradation']*(c+d)+cfg['discomfort']*np.abs(f-f0).sum(axis=1)
    errs['real_cost']=float(np.max(np.abs(cost-h.real_cost)))
    errs['daily_cost_totals']=float(np.max(np.abs(cost.reshape(-1,24).sum(axis=1)-daily.real_cost)))
    errs['daily_emission_totals']=float(np.max(np.abs(delta.reshape(-1,24).sum(axis=1)-daily.delta_emissions)))
    # Reconstruct each participant's disagreement bill and the contractual split.
    buy=base.price_buy.to_numpy(); sell=base.price_sell.to_numpy()
    independent=np.maximum(crit+f0-pv,0)*buy[:,None]-np.maximum(pv-crit-f0,0)*sell[:,None]
    baseline_bills=independent.reshape(-1,24,3).sum(axis=1)
    surplus=baseline_bills.sum(axis=1)-cost.reshape(-1,24).sum(axis=1)
    benefits=.8*np.maximum(surplus,0)/3
    charges=baseline_bills-benefits[:,None]
    reported=daily[[f'participant_{i}_bill' for i in range(3)]].to_numpy()
    margin=np.where(surplus>=0,.2*surplus,surplus)
    errs['participant_settlement']=float(np.max(np.abs(charges-reported)))
    errs['operator_settlement']=float(np.max(np.abs(margin-daily.operator_margin)))
    errs['settlement_budget']=float(np.max(np.abs(reported.sum(axis=1)-daily.real_cost-daily.operator_margin)))
    errs['individual_participation']=float(max(0,np.max(reported-baseline_bills)))
    # Independently reconstruct empirical risk constraints, using only historical
    # factor rows and recorded development-block issue dates.
    if policy.startswith('CV') or policy.startswith('G_') or policy=='MARGIN':
        def history_prediction(start):
            history=source[f'mef_{regime}'].iloc[start-168:start].to_numpy().reshape(7,24)
            return .6*history[-1]+.4*history.mean(axis=0)
        dated={date:i for i,date in enumerate(source.timestamp_utc)}
        residual_maps={}
        for season,dates in config['residual_dates_development_only'].items():
            residuals=[]
            for date in dates:
                index=dated[date]
                assert date.startswith(('2021','2022'))
                residuals.append(source[f'mef_{regime}'].iloc[index:index+24].to_numpy()-history_prediction(index))
            residuals=np.array(residuals)
            if cfg.get('shuffle_residual_hours',False):
                residuals=residuals[:,np.random.default_rng(8103).permutation(24)]
            residual_maps[season]=residuals
        maximum=-np.inf; agreement=0.
        for j,date in enumerate(daily.date):
            start=dated[date]
            predicted=np.clip(history_prediction(start)*cfg.get('carbon_forecast_bias',1.),0,.95)
            season=str((pd.to_datetime(date,utc=True).month-1)//3) if cfg['scenario_seasonal'] else 'None'
            residuals=residual_maps[season]
            scenario=np.clip(predicted[None,:]+cfg['factor_error']*residuals,0,.95)
            intervention=(q-q0)[j*24:(j+1)*24]
            losses=scenario@intervention
            candidates=np.r_[losses,0.]
            alpha=cfg['alpha']
            cvar=min(z+np.maximum(losses-z,0).mean()/(1-alpha) for z in candidates)
            if policy=='MARGIN': risk=float(predicted@intervention+cfg['margin']*np.abs(intervention).sum())
            elif policy=='G_point': risk=float(predicted@intervention)
            elif policy=='G_mean': risk=float(losses.mean())
            elif policy=='G_worst': risk=float(losses.max())
            else: risk=float(cvar)
            maximum=max(maximum,risk)
            agreement=max(agreement,abs(cvar-daily.surrogate_cvar.iloc[j]))
        errs['surrogate_constraint']=float(max(0,maximum))
        errs['surrogate_reconstruction']=float(agreement)
    errors=max(errs.values())
    assert errors<1e-4, (str(directory),policy,errs)
    assert (daily.status_code.isin([0,1]) | daily.fallback).all()
    return {'directory':directory.name,'policy':policy,'hours':len(h),'max_error':errors,'errors':errs}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--directory')
    args=parser.parse_args()
    source_cache={}
    dirs=[ROOT/'results'/args.directory] if args.directory else sorted((ROOT/'results').iterdir())
    records=[]
    for directory in dirs:
        if not directory.is_dir(): continue
        for path in sorted(directory.glob('*_config.json')):
            policy=path.name.removesuffix('_config.json')
            config=json.loads(path.read_text())
            source_file=config['source_file']
            if source_file not in source_cache:
                source_cache[source_file]=pd.read_csv(ROOT/source_file)
            source=source_cache[source_file]
            record=replay(directory,policy,source); records.append(record)
            print(f'{directory.name}/{policy}: {record["hours"]} hours; error {record["max_error"]:.2e}',flush=True)
    (ROOT/'audit'/'independent_replay.json').write_text(json.dumps(records,indent=2))


if __name__=='__main__': main()
