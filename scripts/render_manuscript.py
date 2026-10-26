"""Generate manuscript tables and figure only from verified result CSVs."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def row(lines,items):lines.append(' & '.join(map(str,items))+r' \\')
def table(lines,columns,caption,label,header,body):
    lines.extend([r'\begin{table}[H]',r'\centering',r'\small',
        r'\caption{'+caption+'}',r'\label{'+label+'}',
        r'\begin{tabular}{'+columns+'}',r'\toprule'])
    row(lines,header);lines.append(r'\midrule')
    for cells in body:row(lines,cells)
    lines.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}'])

def main():
    s=pd.read_csv(ROOT/'tables/final_summary.csv')
    i=pd.read_csv(ROOT/'tables/isolation.csv')
    u=pd.read_csv(ROOT/'tables/paired_uncertainty.csv')
    c=pd.read_csv(ROOT/'tables/final_coverage.csv')
    d=pd.read_csv(ROOT/'tables/error_decomposition_v2.csv')
    sensitivity=pd.read_csv(ROOT/'tables/factor_sensitivity.csv')
    lines=[]
    syn=s[s.domain=='synthetic']; ext=s[s.domain=='ERCOT-input hybrid']
    lines.append(r'\subsection{Isolation and economic attribution}')
    lines.append('The matched cases isolate the shared-meter saving before flexibility or battery operation is credited. Table~\\ref{tab:isolation} reports savings per sampled day against the indicated adjacent case. Negative entries mean the added capability increased expense. The interaction is the change in flexibility savings when storage is available.')
    body=[]
    for regime in ('coal_first','gas_first','solar_rich'):
        x=i[i.run.str.startswith('confirmation_') & i.run.str.endswith(regime)]
        if len(x)!=2:raise ValueError('Expected two independent synthetic seeds')
        vals={key:(x[key]/x.days).mean() for key in ('independent_bill_to_shared_meter_savings',
            'flex_savings_without_storage','storage_savings_with_fixed_demand',
            'storage_savings_with_flex','interaction')}
        body.append([regime.replace('_',' '),*[f'{vals[key]:.2f}' for key in vals]])
    table(lines,'lrrrrr','Mean operational-expense savings (synthetic USD per sampled day) over two independent synthetic seeds. The reference in each column is the matched adjacent case.','tab:isolation',
        ['Regime','Meter','Flex $|$ no storage','Storage $|$ fixed','Storage $|$ flex','Interaction'],body)
    lines.append(r'\subsection{Scenario guards and the calibrated comparator}')
    body=[]
    selected=('B3','CV8','CV32','CV128','MARGIN','G_worst','ROBOX')
    for regime in ('coal_first','gas_first','solar_rich'):
        for policy in selected:
            x=syn[(syn.regime==regime)&(syn.policy==policy)].iloc[0]
            body.append([regime.replace('_',' '),policy.replace('_',r'\_'),
                f'{x.cost_per_day:.1f}',f'{x.delta_kg_per_day:.1f}',
                f'{x.positive_kg_per_day:.1f}',f'{100*x.violation_fraction:.1f}'])
    table(lines,'llrrrr','Independent 2025 synthetic confirmation, averaged over 184 paired days per regime (two seeds, 92 days each). Positive mass sums only upward daily changes; mean change can be negative while violations persist.','tab:synthetic',
        ['Regime','Policy','Cost/day','Mean $\Delta E$/day','Positive kg/day','Violating \%'],body)
    lines.append('Increasing the set from 8 to 32 scenarios improves positive-severity outcomes in all three regimes, although the number of violating days remains nonzero. Expanding from 32 to 128 is not uniformly beneficial: gas-first positive severity rises slightly. The margin is not uniformly superior to the established worst-scenario guard on every metric; its cost is higher and it still violates the consequential reference on some synthetic days. ROBOX has zero intervention by construction and therefore zero reference-relative emissions change.')
    body=[]
    for regime in ('coal_first','gas_first','solar_rich'):
        for policy in ('CV32','MARGIN'):
            x=u[(u.regime==regime)&(u.comparator==policy)].iloc[0]
            body.append([regime.replace('_',' '),policy,
                f'{x.positive_kg_per_day_difference:.1f}',
                f'[{x.positive_kg_per_day_ci_low:.1f}, {x.positive_kg_per_day_ci_high:.1f}]',
                f'{x.cost_per_day_difference:.1f}',
                f'[{x.cost_per_day_ci_low:.1f}, {x.cost_per_day_ci_high:.1f}]'])
    table(lines,'llrrrr','Paired comparator minus CV8, with 95\% circular seven-sampled-day block intervals within each seed. These intervals describe selected synthetic sequences, not uncertainty over real electricity systems.','tab:uncertainty',
        ['Regime','Comparator','$\Delta$positive kg/day','95\% interval','$\Delta$cost/day','95\% interval'],body)
    lines.append(r'\subsection{Forecast coverage and response mismatch}')
    coverage=c[c.run.str.startswith('confirmation_')].groupby(['regime','policy'],as_index=False).mean(numeric_only=True)
    body=[]
    for regime in ('coal_first','gas_first','solar_rich'):
        for policy in ('CV8','CV32','CV128'):
            x=coverage[(coverage.regime==regime)&(coverage.policy==policy)].iloc[0]
            body.append([regime.replace('_',' '),policy,f'{100*x.hourly_coverage:.1f}',
                f'{100*x.whole_day_coverage:.1f}',f'{100*x.scenario_max_exceedance_fraction:.1f}'])
    table(lines,'llrrr','Realised marginal-factor coverage by development-sampled scenario envelopes on independent synthetic days. The last column is the fraction of realised linear intervention losses exceeding the largest sampled linear loss.','tab:coverage',
        ['Regime','Policy','Hourly covered \%','Whole-day covered \%','Loss above max \%'],body)
    dd=d[d.run.str.startswith('confirmation_') & d.policy.isin(('CV8','CV32'))].copy()
    err=dd.groupby(['regime','policy']).agg(forecast_mae=('forecast_mae_kg_per_kwh','mean'),
        abs_forecast=('forecast_component_kg',lambda z:np.mean(np.abs(z))),
        abs_response=('response_component_kg',lambda z:np.mean(np.abs(z)))).reset_index()
    body=[]
    for _,x in err.iterrows():body.append([x.regime.replace('_',' '),x.policy,
        f'{x.forecast_mae:.3f}',f'{x.abs_forecast:.1f}',f'{x.abs_response:.1f}'])
    table(lines,'llrrr','Exact decomposition of independently replayed synthetic changes, averaged per sampled day. Absolute components are reported because signed errors can cancel.','tab:errors',
        ['Regime','Policy','Factor MAE','Forecast error kg','Response error kg'],body)
    lines.append('Higher envelope coverage chiefly addresses forecast error. It cannot by itself bound the response term in Eq.~\\eqref{eq:decomp}; the signed components can cancel, so aggregate annual emissions alone are an inadequate guard diagnostic. Figure~\\ref{fig:tradeoff} shows the paired severity--expense tradeoff.')
    body=[]
    for regime in ('coal_first','gas_first','solar_rich'):
        cells=[regime.replace('_',' ')]
        for policy in ('CV8','CV32','MARGIN'):
            base=syn[(syn.regime==regime)&(syn.policy==policy)].positive_kg_per_day.iloc[0]
            subset=sensitivity[(sensitivity.regime==regime)&(sensitivity.policy==policy)]
            cells.append(f'{base:.1f} [{subset.positive_kg_per_day.min():.1f}, {subset.positive_kg_per_day.max():.1f}]')
        body.append(cells)
    table(lines,'llll','Positive consequential change (kg/day): nominal result followed by the range across prespecified forecast-factor multipliers 0.85/1.15 and, where applicable, residual-spread multipliers 0.5/1.5. All variants use the same two independent synthetic seeds. Full cost and violation results appear in the accompanying CSV.','tab:sensitivity',
        ['Regime','CV8 nominal [range]','CV32 nominal [range]','Margin nominal [range]'],body)
    lines.append('Across the paired factor-error variants in Table~\\ref{tab:sensitivity}, CV32 retains lower positive change than CV8, but the size of the improvement varies substantially; no tested guard yields zero violations in all regimes. The margin remains weaker than CV32 in the solar-rich regime.')
    lines.append(r'\begin{figure}[H]')
    lines.append(r'\centering\includegraphics[width=.95\linewidth]{guard_tradeoff.pdf}')
    lines.append(r'\caption{Cost and positive emission change on independent synthetic days, from saved and replayed outputs. Each point aggregates both new seeds within a regime.}')
    lines.append(r'\label{fig:tradeoff}\end{figure}')
    lines.append(r'\subsection{Regional-input check and feasibility}')
    body=[]
    for policy in ('M0','M1','S0','S1','CV8','CV32','CV128','MARGIN','G_worst','ROBOX'):
        x=ext[ext.policy==policy].iloc[0]
        body.append([policy.replace('_',r'\_'),f'{x.cost_per_day:.1f}',
            f'{x.delta_kg_per_day:.2f}',f'{x.positive_kg_per_day:.2f}',
            f'{100*x.violation_fraction:.1f}'])
    table(lines,'lrrrr','ERCOT-input February--December 2024 check on 84 regularly sampled days. Demand/renewable inputs are public regional reports; intervention emissions are an associational model response.','tab:eia',
        ['Policy','Cost/day','Mean $\Delta E$/day','Positive kg/day','Violating \%'],body)
    mae=pd.read_json(ROOT/'audit/eia_response_model.json',typ='series')['validation_level_mae_tonnes_per_hour']
    max_task=s.max_task_error.max();max_carbon=s.max_carbon_error.max();max_budget=s.max_budget_error.max()
    lines.append(f'The 2022-fitted EIA emissions-level model had a 2023 held-out MAE of {mae:.0f} metric tonnes per hour; this is predictive error for EIA estimates, not causal marginal-factor validation. Across the reported runs, maximum task, carbon-ledger and settlement residuals were {max_task:.2e}, {max_carbon:.2e} and {max_budget:.2e}, respectively. The table-generating CSV records every solver status, fallback and runtime. The public-input margin chose no intervention on these days, demonstrating a material opportunity-cost limit rather than external validation of a universal guard.')
    (ROOT/'manuscript/results_generated.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fig,ax=plt.subplots(figsize=(7.2,4.5))
    symbols={'CV8':'o','CV32':'s','CV128':'^','MARGIN':'D','G_worst':'x','ROBOX':'P'}
    colors={'coal_first':'#ad3f36','gas_first':'#317c7b','solar_rich':'#6a4c93'}
    for regime in ('coal_first','gas_first','solar_rich'):
        for policy,marker in symbols.items():
            x=syn[(syn.regime==regime)&(syn.policy==policy)].iloc[0]
            ax.scatter(x.cost_per_day,x.positive_kg_per_day,color=colors[regime],marker=marker,s=53)
            if policy in ('CV8','CV32','MARGIN'):
                ax.annotate(policy.replace('_',' '),(x.cost_per_day,x.positive_kg_per_day),
                    xytext=(3,3),textcoords='offset points',fontsize=7,color=colors[regime])
    from matplotlib.lines import Line2D
    ax.legend([Line2D([0],[0],marker='o',linestyle='',color=color) for color in colors.values()],
        [x.replace('_',' ') for x in colors],loc='upper right',frameon=False)
    ax.set_xlabel('Operational expense (synthetic USD/day)')
    ax.set_ylabel('Positive consequential change (kg CO$_2$/day)')
    ax.grid(alpha=.2);fig.tight_layout();fig.savefig(ROOT/'figures/guard_tradeoff.pdf');plt.close(fig)
    print({'tables':6,'figure':'guard_tradeoff.pdf','synthetic_days':int(syn.days.max()),
           'eia_days':int(ext.days.max())})

if __name__=='__main__':main()
