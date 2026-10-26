"""Correct display labels for a frozen 1.15 sensitivity multiplier."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
base=(ROOT/'results').resolve()
changes=[]
for source in sorted(base.glob('sensitivity_*_bias114')):
    target=source.with_name(source.name.removesuffix('bias114')+'bias115')
    if source.resolve().parent!=base or target.resolve().parent!=base:
        raise SystemExit('Refusing a move outside the result workspace')
    if target.exists():raise SystemExit(f'Already exists: {target}')
    cfg=list(source.glob('*_config.json'))
    if len(cfg)!=1:raise SystemExit(f'Unexpected sensitivity directory: {source}')
    factor=json.loads(cfg[0].read_text())['settings']['carbon_forecast_bias']
    if abs(factor-1.15)>1e-12:raise SystemExit(f'Not a 1.15 run: {source}')
    source.rename(target)
    changes.append({'from':source.name,'to':target.name,'stored_factor':factor})
(ROOT/'audit/SENSITIVITY_LABEL_CORRECTION.json').write_text(json.dumps({
    'reason':'Floating-point 1.15 * 100 truncated to 114 in run-directory display labels; settings and schedules always used 1.15.',
    'moves':changes},indent=2)+'\n')
print(f'Corrected {len(changes)} display labels after validating saved settings')
