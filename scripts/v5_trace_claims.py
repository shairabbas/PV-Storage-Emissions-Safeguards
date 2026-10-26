"""Build a traceability index for manuscript numerical claims; no simulations."""
from pathlib import Path
import csv
import json
import hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'tables'
rows=[]

def add(claim,location,table,saved,script,audit):
    rows.append(dict(claim=claim,manuscript_location=location,source_table=table,
                    saved_output=saved,generating_script=script,audit_evidence=audit,
                    interpretation_status='verified internally; model validity conditional'))

for _,x in pd.read_csv(T/'v3_isolation_verified.csv').iterrows():
    add(f'{x.demand_seed}/{x.regime}: meter {x.meter_saving_per_day:.9g}, flex {x.flex_saving_no_storage_per_day:.9g}, storage fixed {x.storage_saving_fixed_per_day:.9g}, storage flex {x.storage_saving_flex_per_day:.9g}, interaction {x.interaction_per_day:.9g} synthetic USD/active day',
        'main Results Table 1; supplement Table 4', 'tables/v3_isolation_verified.csv',
        f'results/confirmation_seed{x.demand_seed}_2025_{x.regime}/{{B0,M0,M1,S0,S1}}_daily.csv',
        'scripts/v3_verify_interaction.py','audit/v3_interaction_audit.json; audit/final_package_audit.json')
for _,x in pd.read_csv(T/'v3_failure_tradeoff_summary.csv').iterrows():
    if x.regime not in ('coal_first','gas_first','solar_rich','eia_erco'): continue
    run=('v3_eia_confirmation_2024' if x.regime=='eia_erco' else 'confirmation_seed{271828,314159}_2025_'+x.regime)
    add(f'{x.regime}/{x.policy}: cost {x.cost_usd_per_day:.9g}, L {x.positive_kg_per_day:.9g}, violation {x.violation_fraction:.9g}, conditional mean {x.mean_kg_given_violation:.9g}, conditional P95 {x.p95_kg_given_violation:.9g}, intervention {x.intervention_l1_kwh_per_day:.9g}',
        'main Results Tables 2, 3, 5; supplement Tables 1, 5', 'tables/v3_failure_tradeoff_summary.csv',
        f'results/{run}/{x.policy}_{{daily,hourly}}.csv.gz',
        'scripts/v3_failure_and_tradeoff.py; scripts/render_v3_manuscript.py',
        'audit/final_package_audit.json; audit/independent_replay.json')
for _,x in pd.read_csv(T/'v3_cv32_128_summary.csv').iterrows():
    add(f'{x.regime}: paired CV128-CV32 L {x.difference_kg_per_day:.9g} kg/day, 552 comparisons, cost difference {x.cost_difference_usd_per_day:.9g}',
        'main abstract and Table 4; supplement Tables 2-3',
        'tables/v3_cv32_128_summary.csv; tables/v3_cv32_128_bootstrap.csv',
        f'results/confirmation_seed[271828|314159]_2025_{x.regime}/CV[32|128|32_S11|32_S23]_daily.csv; results/v3_cv128_seed[271828|314159]_{x.regime}_draw[11|23]/CV128_daily.csv',
        'scripts/v3_cv32_128_analysis.py','audit/V3_REPLICATION_FREEZE.json; audit/final_package_audit.json')
for _,x in pd.read_csv(T/'v3_cv32_128_bootstrap.csv').iterrows():
    add(f'{x.regime}: {int(x.calendar_span_days)}-calendar-day paired block interval [{x.positive_difference_ci_low:.9g},{x.positive_difference_ci_high:.9g}] kg/day',
        'main Results Table 4; supplement Table 2', 'tables/v3_cv32_128_bootstrap.csv',
        'tables/v3_cv32_128_paired_daily.csv', 'scripts/v3_cv32_128_analysis.py',
        'audit/V3_REPLICATION_FREEZE.json')
for _,x in pd.read_csv(T/'final_full_window_isolation.csv').iterrows():
    add(f'{x.run}: {x.calendar_days_first_to_last_selected} calendar days, {x.selected_days} active days, meter saving {x.meter_aggregation_saving_full_usd_per_calendar_day:.9g} USD/calendar-day',
        'main Results paragraph; supplement Table 4', 'tables/final_full_window_isolation.csv',
        f'results/{x.run}/{{B0,M0,M1,S0,S1}}_daily.csv',
        'scripts/summarize_full_window.py', 'audit/final_timeline_completion.json')
for claim,table,saved,script,audit,location in [
 ('117 runs, 31,581 intervening policy-days, zero state/reference gap','tables/final_timeline_completion.csv','results/*/*_daily.csv; results/*/*_hourly.csv.gz','scripts/audit_intervening_policy.py','audit/final_timeline_completion.json','main Methods; supplement State audits'),
 ('independent replay 317 runs, 561,864 hours, max residual 1.024e-8','tables/final_summary.csv','results/*/*_hourly.csv.gz','scripts/replay_v2.py','audit/independent_replay.json; audit/final_package_audit.json','supplement reproducibility; external report'),
 ('ERCOT-input MARGIN idle 84/84 days, maximum daily L1 1.32e-11 kWh','tables/v3_failure_tradeoff_summary.csv','results/v3_eia_confirmation_2024/MARGIN_hourly.csv.gz','scripts/v3_failure_and_tradeoff.py','audit/v3_margin_idle_check.json','main Results Table 5'),
 ('ERCO 2023 level MAE 830.254 tonnes/hour, 4.7587% of mean, bias +343.746','audit/v5_eia_level_diagnostics.json','data/eia_erco_2022_2023.csv.gz','scripts/v5_source_and_eia_audit.py; scripts/fit_eia_response.py','audit/eia_response_model.json; audit/v5_eia_level_diagnostics.json','main Methods; supplement Additional interpretation'),
 ('ERCO 2023 quarterly MAE 1300.49, 577.67, 700.62, 749.72 tonnes/hour','audit/v5_eia_level_diagnostics.json','data/eia_erco_2022_2023.csv.gz','scripts/v5_source_and_eia_audit.py','audit/v5_eia_level_diagnostics.json','supplement Additional interpretation'),
 ('EIA factor and scaled baseline corrected by 1000; 30 dependent regional cases rerun','tables/final_eia_legacy_vs_corrected_actions.csv','data/*frame_corrected.csv.gz; results/v3_eia_*','scripts/audit_eia_unit_dependencies.py; scripts/v3_rerun_eia.py','audit/final_eia_unit_dependency.json','main Methods and Results; supplement State audits'),
 ('battery 600 kWh, 150 kW, efficiency 0.95, auxiliary 0.003, meter 2000 kW','configuration: src/optimization.py','results/*/*_config.json','src/optimization.py; src/simulation.py','audit/final_package_audit.json','main Methods'),
 ('MARGIN calibration lambda 0.06845 kg/kWh','tables/margin_calibration.csv','results/calibration_*','scripts/calibrate_margin.py','audit/margin_calibration.json','main Methods'),
 ('CV8 pool 2022; CV32/CV128 pool 2021-2022','configuration: src/simulation.py','data/benchmark.csv.gz','src/simulation.py; src/data.py','audit/V3_REPLICATION_FREEZE.json','main Abstract, Methods, Discussion; supplement Additional interpretation'),
]: add(claim,location,table,saved,script,audit)

add('Signed point + factor error + nonlinear remainder equals conditional mean positive change for each of nine plotted synthetic policy/regime rows',
    'main Figure 2', 'tables/v3_failure_tradeoff_summary.csv',
    'results/confirmation_seed[271828|314159]_2025_[regime]/[policy]_hourly.csv.gz',
    'scripts/v3_failure_and_tradeoff.py; scripts/v6_figures.py',
    'audit/v6_figure_data_audit.json; audit/independent_replay.json')
add('Three draw means, pooled CV128-CV32 difference and 16-calendar-day descriptive interval for each regime',
    'main Figure 3', 'tables/v3_cv32_128_summary.csv; tables/v3_cv32_128_bootstrap.csv',
    'tables/v3_cv32_128_paired_daily.csv',
    'scripts/v3_cv32_128_analysis.py; scripts/v6_figures.py',
    'audit/v6_figure_data_audit.json; audit/V3_REPLICATION_FREEZE.json')

with (ROOT/'CLAIM_EVIDENCE_MATRIX.csv').open('w',newline='',encoding='utf-8') as out:
    writer=csv.DictWriter(out,fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
print(json.dumps({'claims':len(rows),'sha256':hashlib.sha256((ROOT/'CLAIM_EVIDENCE_MATRIX.csv').read_bytes()).hexdigest()}))
