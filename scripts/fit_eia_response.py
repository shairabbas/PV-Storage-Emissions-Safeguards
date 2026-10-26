"""Fit an observational ERCOT emissions-response proxy on 2022; assess 2023 only."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/eia_erco_2022_2023.csv.gz'

def features(data):
    date=pd.to_datetime(data.utc_end,utc=True)
    r=(data.demand_mw-data.solar_mw-data.wind_mw).to_numpy()/10000.
    h=date.dt.hour.to_numpy();d=date.dt.dayofyear.to_numpy()
    return np.column_stack((np.ones(len(data)),r,r*r,
        np.sin(2*np.pi*h/24),np.cos(2*np.pi*h/24),
        np.sin(2*np.pi*d/365.25),np.cos(2*np.pi*d/365.25)))

def marginal(data,coef):
    r=(data.demand_mw-data.solar_mw-data.wind_mw).to_numpy()/10000.
    return np.clip((coef[1]+2*coef[2]*r)/10000,0,1.5)

def main():
    x=pd.read_csv(SOURCE)
    year=pd.to_datetime(x.utc_end,utc=True).dt.year
    train=x[(year==2022)&x.eia_estimated_co2.notna()].copy()
    val=x[(year==2023)&x.eia_estimated_co2.notna()].copy()
    X=features(train);y=train.eia_estimated_co2.to_numpy()
    coef=np.linalg.lstsq(X,y,rcond=None)[0]
    pred=features(val)@coef
    mef=marginal(val,coef)
    mae=float(np.mean(np.abs(pred-val.eia_estimated_co2.to_numpy())))
    bias=float(np.mean(pred-val.eia_estimated_co2.to_numpy()))
    report={'training':'EIA-930 ERCOT 2022 hourly estimated production CO2 (metric tons) vs reported demand minus reported wind/solar (MW), with daily/annual Fourier controls. Ordinary least squares.',
        'validation':'2023 held out for model assessment; no 2024 record read or inspected.',
        'coefficients':coef.tolist(),'feature_order':['intercept','residual_load_div_10000',
            'residual_load_div_10000_squared','sin_hour','cos_hour','sin_day','cos_day'],
        'training_hours':len(train),'validation_hours':len(val),'validation_level_mae_tonnes_per_hour':mae,
        'validation_level_bias_tonnes_per_hour':bias,
        'validation_marginal_proxy_kg_per_kwh_quantiles':np.quantile(mef,[0,.1,.5,.9,1]).tolist(),
        'response':'Partial derivative of fitted associational CO2-level model with respect to residual load, clipped to [0,1.5] kg/kWh. No causal marginal identification or observed intervention response.',
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    (ROOT/'audit/eia_response_model.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('training_hours','validation_hours',
        'validation_level_mae_tonnes_per_hour','validation_level_bias_tonnes_per_hour',
        'validation_marginal_proxy_kg_per_kwh_quantiles')},indent=2))

if __name__=='__main__':main()
