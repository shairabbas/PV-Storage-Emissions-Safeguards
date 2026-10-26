"""Run ERCOT input stress test; final period is gated by the V2 freeze."""
from pathlib import Path
import argparse
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data import ROOT
from src.simulation import simulate
from run_v2 import POLICIES,settings

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase',choices=['validation','confirmation'],required=True)
    ap.add_argument('--policies',nargs='+',choices=POLICIES,default=list(POLICIES))
    args=ap.parse_args()
    final=args.phase=='confirmation'
    if final and not (ROOT/'audit/V2_FREEZE.json').exists():
        raise SystemExit('Prospective freeze required before final ERCOT run')
    source=ROOT/'data'/f'eia_erco_2022_{"2024" if final else "2023"}_frame.csv.gz'
    df=pd.read_csv(source)
    year=2024 if final else 2023
    starts=np.flatnonzero(df.timestamp_utc.str.startswith(str(year)))[::24]
    if final:
        # Jan 1, 2024 was exposed by the earlier source-year/UTC mismatch.
        starts=np.array([s for s in starts if df.timestamp_utc.iloc[s]>='2024-02-01'])[::4]
    else:starts=starts[::7]
    margin=json.loads((ROOT/'audit/margin_calibration.json').read_text())['margin_kg_per_kwh']
    for policy in args.policies:
        cfg=settings(policy,margin)
        result=simulate(df,year,'eia_erco',policy,cfg,starts,
            f'eia_{args.phase}_{year}',str(source.relative_to(ROOT)))
        print(json.dumps({'phase':args.phase,'policy':policy,'days':len(result),
            'delta_kg':float(result.delta_emissions.sum()),
            'positive_days':int((result.delta_emissions>1e-5).sum()),
            'positive_kg':float(result.delta_emissions.clip(lower=0).sum()),
            'cost':float(result.real_cost.sum()),'runtime':float(result.runtime.sum())}),flush=True)

if __name__=='__main__':main()
