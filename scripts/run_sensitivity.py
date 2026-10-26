"""Prespecified carbon-factor stress tests on validation and independent seeds."""
from dataclasses import replace
from pathlib import Path
import argparse
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data import ROOT,load,prepare,REGIMES
from src.simulation import simulate
from run_v2 import settings,SEEDS

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase',choices=['validation','confirmation'],required=True)
    ap.add_argument('--regime',choices=REGIMES,required=True)
    ap.add_argument('--seed',type=int)
    args=ap.parse_args()
    if args.phase=='confirmation' and not (ROOT/'audit/V2_FREEZE.json').exists():
        raise SystemExit('Sensitivity confirmation requires prospective freeze')
    if args.phase=='confirmation':
        if args.seed not in SEEDS:raise ValueError('Seed not prespecified')
        source=ROOT/'data'/f'synthetic_seed_{args.seed}.csv.gz'
        if not source.exists():prepare(args.seed,False).to_csv(source,index=False,compression='gzip')
        df=pd.read_csv(source);year,step=2025,4
    else:
        if args.seed is not None:raise ValueError('No extra development seed')
        source=ROOT/'data/benchmark.csv.gz';df=load();year,step=2023,7
    starts=np.flatnonzero(df.timestamp_utc.str.startswith(str(year)))[::24][::step]
    margin=json.loads((ROOT/'audit/margin_calibration.json').read_text())['margin_kg_per_kwh']
    for policy in ('CV8','CV32','MARGIN'):
        for bias in (.85,1.15):
            cfg=replace(settings(policy,margin),carbon_forecast_bias=bias)
            label=f'{policy}_bias{int(bias*100)}'
            tag=f'sensitivity_{args.phase}_{args.seed or 0}_{args.regime}_{label}'
            result=simulate(df,year,args.regime,policy,cfg,starts,tag,
                str(source.relative_to(ROOT)))
            print(json.dumps({'tag':tag,'days':len(result),
                'positive_kg':float(result.delta_emissions.clip(lower=0).sum()),
                'cost':float(result.real_cost.sum()),'violations':int((result.delta_emissions>1e-6).sum())}),flush=True)
    for scale in (.5,1.5):
        for policy in ('CV8','CV32'):
            cfg=replace(settings(policy,margin),factor_error=scale)
            label=f'{policy}_scale{int(scale*100)}'
            tag=f'sensitivity_{args.phase}_{args.seed or 0}_{args.regime}_{label}'
            result=simulate(df,year,args.regime,policy,cfg,starts,tag,
                str(source.relative_to(ROOT)))
            print(json.dumps({'tag':tag,'days':len(result),
                'positive_kg':float(result.delta_emissions.clip(lower=0).sum()),
                'cost':float(result.real_cost.sum()),'violations':int((result.delta_emissions>1e-6).sum())}),flush=True)

if __name__=='__main__':main()
