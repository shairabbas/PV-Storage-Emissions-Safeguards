"""Prospectively fixed extra CV128 draws to pair with saved CV32 draws."""
from pathlib import Path
from dataclasses import replace
import argparse
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data import ROOT,REGIMES
from src.optimization import Settings
from src.simulation import simulate

LOAD_SEEDS=(314159,271828)
SCENARIO_SEEDS=(11,23)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--demand-seed',type=int,choices=LOAD_SEEDS,required=True)
    ap.add_argument('--regime',choices=REGIMES,required=True)
    args=ap.parse_args()
    if not (ROOT/'audit/V3_REPLICATION_FREEZE.json').exists():
        raise SystemExit('Prospective V3 replication freeze is required')
    source=ROOT/'data'/f'synthetic_seed_{args.demand_seed}.csv.gz'
    x=pd.read_csv(source)
    starts=np.flatnonzero(x.timestamp_utc.str.startswith('2025'))[::24][::4]
    assert len(starts)==92
    for draw in SCENARIO_SEEDS:
        cfg=replace(Settings(),scenario_count=128,scenario_seed=draw)
        tag=f'v3_cv128_seed{args.demand_seed}_{args.regime}_draw{draw}'
        if (ROOT/'results'/tag).exists():raise SystemExit(f'Already exists: {tag}')
        out=simulate(x,2025,args.regime,'CV128',cfg,starts,tag,str(source.relative_to(ROOT)))
        print(json.dumps({'run':tag,'days':len(out),'positive_kg':float(out.delta_emissions.clip(lower=0).sum()),
                          'cost':float(out.real_cost.sum()),'status_nonzero':int((out.status_code!=0).sum())}),flush=True)

if __name__=='__main__':main()
