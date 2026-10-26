"""Run prespecified validation or sealed independent synthetic confirmation."""
from pathlib import Path
from dataclasses import replace
import argparse
import json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data import ROOT,load,prepare,REGIMES
from src.optimization import Settings
from src.simulation import simulate

POLICIES=('B0','M0','M1','S0','S1','B3','CV8','CV32','CV128',
          'CV32_SEAS','CV32_S11','CV32_S23','MARGIN','G_worst','ROBOX')
SEEDS=(314159,271828)

def settings(policy,margin):
    common=Settings()
    if policy in ('M0','M1'): return replace(common,capacity=0.,power=0.)
    if policy in ('CV32','CV32_SEAS','CV32_S11','CV32_S23','G_worst'):
        common=replace(common,scenario_count=32)
    if policy=='CV128': common=replace(common,scenario_count=128)
    if policy=='CV32_SEAS': common=replace(common,scenario_seasonal=True)
    if policy=='CV32_S11': common=replace(common,scenario_seed=11)
    if policy=='CV32_S23': common=replace(common,scenario_seed=23)
    if policy=='MARGIN': common=replace(common,margin=margin)
    return common

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('validation','confirmation'),required=True)
    parser.add_argument('--regime',choices=REGIMES,required=True)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--policies',nargs='+',choices=POLICIES,default=list(POLICIES))
    args=parser.parse_args()
    freeze=ROOT/'audit/V2_FREEZE.json'
    if args.phase=='confirmation' and not freeze.exists():
        raise SystemExit('Final confirmation requires a prospective V2 freeze')
    if args.phase=='confirmation':
        if args.seed not in SEEDS: raise ValueError('Seed not prespecified')
        source=ROOT/'data'/f'synthetic_seed_{args.seed}.csv.gz'
        if not source.exists():
            frame=prepare(seed=args.seed,save=False)
            frame.to_csv(source,index=False,compression='gzip')
        x=pd.read_csv(source)
        year,step=2025,4
        tag=f'confirmation_seed{args.seed}_{year}_{args.regime}'
    else:
        if args.seed is not None: raise ValueError('Validation uses only original development seed')
        source=ROOT/'data/benchmark.csv.gz'
        x=load();year,step=2023,7
        tag=f'validation_{year}_{args.regime}'
    starts=np.flatnonzero(x.timestamp_utc.str.startswith(str(year)))[::24][::step]
    margin=json.loads((ROOT/'audit/margin_calibration.json').read_text())['margin_kg_per_kwh']
    for policy in args.policies:
        cfg=settings(policy,margin)
        day=simulate(x,year,args.regime,policy,cfg,starts,tag,str(source.relative_to(ROOT)))
        print(json.dumps({'phase':args.phase,'regime':args.regime,'seed':args.seed,
            'policy':policy,'days':len(day),'delta_kg':round(day.delta_emissions.sum(),3),
            'positive_days':int((day.delta_emissions>1e-5).sum()),
            'cost':round(day.real_cost.sum(),2),'timeouts':int((day.status_code!=0).sum()),
            'fallbacks':int(day.fallback.sum()),
            'solver_s':round(day.runtime.sum(),2)}),flush=True)

if __name__=='__main__':main()
