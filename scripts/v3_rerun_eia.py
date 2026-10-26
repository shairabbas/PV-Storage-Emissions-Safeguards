"""Rerun every affected ERCOT-input policy with corrected average-factor units."""
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
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=('validation','confirmation'),required=True)
    args=ap.parse_args()
    final=args.phase=='confirmation';year=2024 if final else 2023
    source=ROOT/'data'/f'eia_erco_2022_{year}_frame_corrected.csv.gz'
    frame=pd.read_csv(source)
    starts=np.flatnonzero(frame.timestamp_utc.str.startswith(str(year)))[::24]
    if final:starts=np.array([s for s in starts if frame.timestamp_utc.iloc[s]>='2024-02-01'])[::4]
    else:starts=starts[::7]
    assert len(starts)==(84 if final else 53)
    margin=json.loads((ROOT/'audit/margin_calibration.json').read_text())['margin_kg_per_kwh']
    tag=f'v3_eia_{args.phase}_{year}'
    if (ROOT/'results'/tag).exists():raise SystemExit(f'Corrected result exists: {tag}')
    for policy in POLICIES:
        out=simulate(frame,year,'eia_erco',policy,settings(policy,margin),starts,tag,
                     str(source.relative_to(ROOT)))
        print(json.dumps({'policy':policy,'days':len(out),
          'positive_kg':float(out.delta_emissions.clip(lower=0).sum()),
          'cost':float(out.real_cost.sum()),'status_nonzero':int((out.status_code!=0).sum())}),flush=True)

if __name__=='__main__':main()
