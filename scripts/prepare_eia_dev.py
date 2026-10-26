"""Prepare 2022-2023 ERCOT development/validation inputs; never read reserved 2024 rows."""
from pathlib import Path
import hashlib
import json
import pandas as pd
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
CSV_COLS=['Balancing Authority','UTC Time at End of Hour','Demand Forecast (MW)',
    'Demand (MW)','Net Generation (MW)','Total Interchange (MW)',
    'Net Generation (MW) from Coal','Net Generation (MW) from Natural Gas',
    'Net Generation (MW) from Solar','Net Generation (MW) from Wind']
XLS_COLS=['UTC time','CO2 Factor: COL','CO2 Factor: NG','CO2 Factor: OIL',
    'CO2 Emissions: COL','CO2 Emissions: NG','CO2 Emissions: OIL',
    'CO2 Emissions Generated','CO2 Emissions Consumed']

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    parts=[]; raw=[]
    for year in (2022,2023):
        for half in ('Jan_Jun','Jul_Dec'):
            p=DATA/f'EIA930_BALANCE_{year}_{half}.csv'
            raw.append({'file':p.name,'bytes':p.stat().st_size,'sha256':digest(p),
                        'url':f'https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/{p.name}'})
            for block in pd.read_csv(p,usecols=CSV_COLS,chunksize=50000,low_memory=False):
                x=block.loc[block['Balancing Authority']=='ERCO'].copy()
                if len(x):parts.append(x)
    eia=pd.concat(parts,ignore_index=True)
    eia['utc_end']=pd.to_datetime(eia['UTC Time at End of Hour'],utc=True)
    assert len(eia)==17520 and eia.utc_end.is_unique
    eia=eia.sort_values('utc_end').reset_index(drop=True)
    wb=DATA/'EIA930_ERCO_hourly_2023_2025.xlsx'
    raw.append({'file':wb.name,'bytes':wb.stat().st_size,'sha256':digest(wb),
                'url':'https://www.eia.gov/electricity/gridmonitor/knownissues/xls/ERCO.xlsx'})
    sheet=load_workbook(wb,read_only=True,data_only=True)['Published Hourly Data']
    row_iter=sheet.iter_rows(values_only=True)
    headers=next(row_iter); idx={name:headers.index(name) for name in XLS_COLS}
    emission=[]
    for row in row_iter:
        stamp=row[idx['UTC time']]
        if stamp is None: continue
        year=stamp.year
        if year>=2024: break
        if year<2022: continue
        emission.append({key:row[pos] for key,pos in idx.items()})
    emissions=pd.DataFrame(emission)
    emissions['utc_end']=pd.to_datetime(emissions.pop('UTC time'),utc=True)
    assert emissions.utc_end.is_unique
    merged=eia.merge(emissions,on='utc_end',how='left',validate='one_to_one')
    report={'selected_ba':'ERCO','development_year':2022,'validation_year':2023,
        'row_count_eia_csv':len(eia),'row_count_emission_workbook':len(emissions),
        'joined_missing_emission':int(merged['CO2 Emissions Generated'].isna().sum()),
        'data_ranges':{c:[float(merged[c].min()),float(merged[c].max())]
            for c in ['Demand (MW)','Net Generation (MW) from Solar',
                      'Net Generation (MW) from Wind','CO2 Emissions Generated']},
        'raw':raw,'provenance':'EIA-930 reported BA data and EIA estimated hourly CO2; no measured participant PV/demand or observed intervention response.',
        'source_docs':['https://www.eia.gov/electricity/930-content/about.html',
                       'https://www.eia.gov/electricity/gridmonitor/']}
    assert report['joined_missing_emission']<100
    out=merged.rename(columns={'Demand (MW)':'demand_mw',
        'Net Generation (MW) from Coal':'coal_mw',
        'Net Generation (MW) from Natural Gas':'gas_mw',
        'Net Generation (MW) from Solar':'solar_mw',
        'Net Generation (MW) from Wind':'wind_mw',
        'CO2 Emissions Generated':'eia_estimated_co2'})[['utc_end','demand_mw','coal_mw',
            'gas_mw','solar_mw','wind_mw','eia_estimated_co2']]
    out.to_csv(DATA/'eia_erco_2022_2023.csv.gz',index=False)
    (ROOT/'audit/eia_provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('row_count_eia_csv','row_count_emission_workbook',
                                           'joined_missing_emission','data_ranges')},indent=2))

if __name__=='__main__':main()
