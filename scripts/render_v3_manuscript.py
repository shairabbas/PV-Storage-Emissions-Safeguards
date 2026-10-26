"""Render V3 paper/supplement tables and figure from verified machine outputs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
TABLES=ROOT/'tables';MANUSCRIPT=ROOT/'manuscript'
REGIMES=('coal_first','gas_first','solar_rich')

def row(cells):return ' & '.join(map(str,cells))+r' \\'
def main_table(lines,label,caption,columns,header,body):
    lines.extend([r'\begin{table}[H]',r'\centering',r'\small',
       r'\caption{'+caption+'}',r'\label{'+label+'}',
       r'\resizebox{\linewidth}{!}{%',r'\begin{tabular}{'+columns+'}',r'\toprule',row(header),r'\midrule'])
    lines.extend(row(r) for r in body)
    lines.extend([r'\bottomrule',r'\end{tabular}}',r'\end{table}'])
def fmt(x,dec=1):return f'{x:.{dec}f}'
def policy(x):return str(x).replace('_',r'\_')
def regime(x):return x.replace('_',' ')

def main():
    iso=pd.read_csv(TABLES/'v3_isolation_verified.csv')
    trade=pd.read_csv(TABLES/'v3_failure_tradeoff_summary.csv')
    pairs=pd.read_csv(TABLES/'v3_cv32_128_summary.csv')
    boots=pd.read_csv(TABLES/'v3_cv32_128_bootstrap.csv')
    daily=pd.read_csv(TABLES/'v3_cv32_128_paired_daily.csv')
    state=json.loads((ROOT/'audit/v3_state_protocol.json').read_text())
    unit=json.loads((ROOT/'audit/v3_eia_unit_correction.json').read_text())
    timeline=json.loads((ROOT/'audit/final_timeline_completion.json').read_text())
    full=pd.read_csv(TABLES/'final_full_window_isolation.csv')
    unit_dep=json.loads((ROOT/'audit/final_eia_unit_dependency.json').read_text())
    lines=[]
    lines.append(r'\subsection{Matched economic isolation}')
    lines.append('The four matched costs give $I=(C_{M1}-C_{S1})-(C_{M0}-C_{S0})=-2.60$ synthetic USD per sampled day after averaging both demand seeds. Table~\\ref{tab:isolation} retains unrounded calculations in the source CSV. The negative sign means storage saves less when demand is already flexible. The operating-regime label does not change these tariff-only costs.')
    body=[]
    for rg in REGIMES:
        x=iso[iso.regime==rg]
        body.append([regime(rg),fmt(x.meter_saving_per_day.mean(),2),
            fmt(x.flex_saving_no_storage_per_day.mean(),2),
            fmt(x.storage_saving_fixed_per_day.mean(),2),
            fmt(x.storage_saving_flex_per_day.mean(),2),
            fmt(x.interaction_per_day.mean(),2)])
    main_table(lines,'tab:isolation','Matched operational savings (synthetic USD per sampled day) across two demand seeds. $I$ is the incremental storage saving with flexible demand minus that with fixed demand.',
        'lrrrrr',['Regime','Meter','Flex, no storage','Storage, fixed','Storage, flex','$I$'],body)
    synthetic_full=full[full.run.str.startswith('confirmation_seed')]
    lines.append(f'Explicit reference operation on the intervening dates yields a mean B0--M0 aggregation saving of ${synthetic_full.meter_aggregation_saving_full_usd_per_calendar_day.mean():.2f}$ per calendar day over each 365-day synthetic window. The interaction remains ${synthetic_full.interaction_usd_per_selected_day.mean():.2f}$ per active day because M0, M1, S0 and S1 share identical reference operation on skipped dates. Table~\\ref{{tab:isolation}} refers only to selected active days; full-window expenses are in the Supplement.')
    lines.append(r'The ordering of the four savings columns is informative. Under the specified tariff and tasks, demand flexibility without storage saves more than storage with fixed tasks, while combined operation produces the largest gross operational saving. Yet the storage increment after flexibility is smaller than the increment before it, producing a negative interaction. This is a diminishing marginal value under one constructed tariff schedule, not evidence that flexible tasks and batteries are technically incompatible. Since the three emissions regimes share the same community loads, tariffs and economic constraints, their isolation rows coincide by design; regime-dependent emission outcomes arise only when the upstream response is evaluated. The full-window aggregation value differs from the sampled-day value because meter aggregation also saves expense on intervening reference days.')
    lines.append(r'\subsection{Safeguard failure and cost of conservatism}')
    lines.append('Table~\\ref{tab:tradeoff} reports expense saving relative to idle-storage, fixed-task ROBOX operation ($713.71$ synthetic USD per sampled day in each regime). Positive severity $L_d=\max(\Delta E_d,0)$ is reported both unconditionally and among violating days. The 95th percentile is conditional on a positive daily change. The $\ell_1$ intervention is $\sum_t|q_t-q_t^0|$; idle means this quantity is at most $10^{-6}$~kWh per day.')
    body=[]
    for rg in REGIMES:
        for pp in ('B3','CV8','CV32','CV128','MARGIN','G_worst','ROBOX'):
            x=trade[(trade.regime==rg)&(trade.policy==pp)].iloc[0]
            body.append([regime(rg),policy(pp),fmt(-x.expense_vs_ROBOX_usd_per_day),
                fmt(x.positive_kg_per_day),fmt(100*x.violation_fraction),
                fmt(x.mean_kg_given_violation),fmt(x.p95_kg_given_violation),
                fmt(x.intervention_l1_kwh_per_day,0),fmt(100*x.idle_intervention_fraction,0)])
    main_table(lines,'tab:tradeoff','Two synthetic load/PV realisations with shared weather: 184 paired sampled days per regime. Expense and intervention are operational; the emissions response is model-generated.',
        'llrrrrrrr',['Regime','Policy','Save/day','Positive kg/day','Viol. \%','Mean+ kg','P95+ kg','$\|v\|_1$','Idle \%'],body)
    lines.append(r'The tested CV32 configuration has lower positive severity than CV8 in each regime while retaining useful operation (Fig.~\ref{fig:tradeoff}). Because their historical residual pools also differ, this contrast cannot isolate the effect of scenario count. Protection is incomplete: in the solar-rich case, CV32 still violates the reference on 29.3\% of sampled days. MARGIN reduces severity in coal-first and gas-first relative to CV8 but costs more; in solar-rich it is dominated on the tested cost--positive-severity plane by CV32 and the worst-scenario guard. These are finite-case mean comparisons, not universal policy rankings.')
    lines.append(r'The frequency, unconditional severity and conditional-tail columns are deliberately shown together. For example, the coal-first CV128 configuration has fewer violation days than CV32, yet its mean severity conditional on violation is higher; a count-only comparison would miss that trade-off. The worst-scenario guard also does not simply rank between finite-scenario CVaR guards across all three regimes. The cost axis of Fig.~\ref{fig:tradeoff} displays savings relative to the same fixed-task, idle-storage operation, so moving left means less operating benefit. It does not include storage capital expenditure. Points on this plot are mean outcomes of the tested cases; apparent dominance is specific to the two displayed metrics and does not establish a policy ordering under a different tariff, weather year or emissions response.')
    lines.extend([r'\begin{figure}[H]',
      r'\centering\includegraphics[width=.93\linewidth]{v3_guard_tradeoff.pdf}',
      r'\caption{Expense saving versus positive consequential change for six selected safeguards (CV8, CV32, CV128, MARGIN, G-worst and ROBOX) in three synthetic regimes. Mean outcomes across two load seeds sharing weather; colour denotes regime and marker denotes policy. The emissions response is model-generated.}',
      r'\label{fig:tradeoff}\end{figure}'])
    body=[]
    for rg in REGIMES:
        for pp in ('CV8','CV32','MARGIN'):
            x=trade[(trade.regime==rg)&(trade.policy==pp)].iloc[0]
            body.append([regime(rg),policy(pp),fmt(x.mean_point_kg_on_violation),
                fmt(x.mean_factor_error_kg_on_violation),
                fmt(x.mean_response_kg_on_violation),
                fmt(x.mean_kg_given_violation),str(int(x.forecast_flip_days)),
                str(int(x.response_flip_days))])
    main_table(lines,'tab:decomp','Mean signed decomposition on positive-change days, in kg per violating day. Flip counts classify a sign change from point to realised-linear loss or from realised-linear to full response. Terms can cancel and are not percentage contributions.',
        'llrrrrrr',['Regime','Policy','Point','Factor error','Response','Total','Factor flips','Response flips'],body)
    lines.append(r'Forecast-factor error exceeds the nonlinear remainder in absolute magnitude on 92.9--100\% of violating synthetic days across the nine regime--policy groups in Table~\ref{tab:decomp} (Fig.~\ref{fig:decomp}). For CV32 in gas-first operation, the mean point term is $-123.7$~kg, the factor-error term $+146.9$~kg and the nonlinear remainder $+11.1$~kg, yielding $+34.3$~kg per violating day. The corresponding coal-first remainder is negative on average; cancellation therefore matters. A few gas-first days change sign only after the nonlinear response term. These are explanatory diagnostics made with realised future factors, not decision-time warning signals. The empirical CVaR constraint targets sampled linear losses, whereas the reported violation uses the separately replayed consequential response.')
    lines.extend([r'\begin{figure}[H]',
      r'\centering\includegraphics[width=\linewidth]{v6_signed_failure_decomposition.pdf}',
      r'\caption{Signed decomposition of mean consequential change on violating selected days for three tested safeguards. Bars show the point surrogate, realised factor-forecast error and nonlinear response remainder; the white diamond shows their sum. Means condition on violating days separately for each policy, so the policy samples differ. All terms come from model-generated counterfactual replay, not observed grid interventions.}',
      r'\label{fig:decomp}\end{figure}'])
    lines.append(r'\subsection{Comparison of sampled 32- and 128-scenario configurations}')
    body=[]
    for rg in REGIMES:
        x=pairs[pairs.regime==rg].iloc[0]
        ci=boots[(boots.regime==rg)&(boots.block_sampled_observations==4)].iloc[0]
        means=json.loads(x.draw_means_kg_per_day)
        body.append([regime(rg),fmt(x.CV32_positive_kg_per_day,2),fmt(x.CV128_positive_kg_per_day,2),
            fmt(x.difference_kg_per_day,2),
            f'[{fmt(ci.positive_difference_ci_low,2)}, {fmt(ci.positive_difference_ci_high,2)}]',
            f'[{fmt(min(means.values()),2)}, {fmt(max(means.values()),2)}]',
            fmt(x.cost_difference_usd_per_day,2)])
    main_table(lines,'tab:scenario','Day-paired $L_{128}-L_{32}$ for non-nested scenario sets over three fixed draw seeds and two synthetic load seeds (552 paired sampled days per regime). Scenario composition changes with count. Intervals resample four adjacent sampled observations, spanning 16 calendar days, and are conditional on the available draws and weather. The draw range is the range of three draw-specific means, not a confidence interval.',
        'lrrrrrr',['Regime','CV32 kg/day','CV128 kg/day','Difference','95\% interval','Draw means range','$\Delta$cost/day'],body)
    lines.append(r'For gas-first operation, the point estimate is $+0.53$~kg/day, its conditional interval crosses zero, and draw-specific mean differences change sign (Fig.~\ref{fig:paired}). Thus the earlier $7.8$ versus $8.4$~kg/day contrast does not establish that the tested 128-scenario configuration performs worse generally. The two additional 128-scenario draws were fixed before their outcomes were examined, but the 2025 calendar and the original result had already been inspected; this is an exploratory replication. One, two and seven sampled-observation block lengths give the same qualitative conclusion (Supplement).')
    lines.append(r'Figure~\ref{fig:paired} separates draw variability from the pooled temporal interval. Coal-first draw means are consistently negative in the three saved draws, but their shared weather and common modeled fleet preclude a universal improvement claim. Solar-rich draw means are likewise negative, while its descriptive interval includes zero because the day-to-day paired differences vary. Gas-first illustrates sensitivity to the sampled configuration: one of three draw means is negative and two are positive. Because the 32- and 128-date sets are non-nested, the differences combine count and composition effects. This experiment cannot establish a reliably ordered count effect, even before considering computational cost or calibration of the response model.')
    lines.extend([r'\begin{figure}[H]',
      r'\centering\includegraphics[width=.90\linewidth]{v6_paired_scenario_contrast.pdf}',
      r'\caption{Day-paired CV128--CV32 difference in unconditional positive emissions-change severity, across 552 selected-day comparisons per regime. The controller scenario sets are separately sampled and non-nested, so differences do not isolate count. Diamonds are pooled means; open markers are means from the three fixed draw seeds. Bars are descriptive 95\% circular-block intervals using four adjacent sampled observations (16 calendar days), conditional on shared weather and the tested seeds. Crossing zero is not a probability guarantee.}',
      r'\label{fig:paired}\end{figure}'])
    lines.append(r'\subsection{Corrected ERCOT-input check}')
    lines.append('The EIA-930 balancing-area response check uses public demand/renewable patterns and EIA-estimated production CO$_2$. Its participant profiles and intervention response remain model-generated. The unit audit corrected the scaled average factor and baseline: $1$ tonne/MWh equals $1$ kg/kWh numerically. The original ERCOT-input factor and scaled baseline were 1000 times too large; all 15 policies were rerun for both the 2023 diagnostic and 2024 check. The fitted marginal derivative was already in kg/kWh and was unchanged.')
    body=[]
    for pp in ('B3','CV8','CV32','CV128','MARGIN','G_worst','ROBOX'):
        x=trade[(trade.regime=='eia_erco')&(trade.policy==pp)].iloc[0]
        body.append([policy(pp),fmt(x.cost_usd_per_day),fmt(-x.expense_vs_ROBOX_usd_per_day),
            fmt(x.positive_kg_per_day,3),fmt(100*x.violation_fraction,1),
            fmt(x.intervention_l1_kwh_per_day,0),fmt(100*x.idle_intervention_fraction,0)])
    main_table(lines,'tab:eia','Corrected ERCOT-input February--December 2024 check on 84 sampled days. Savings are relative to fixed-task idle-storage ROBOX. Consequential responses are observational-model counterfactuals, not measured battery effects.',
        'lrrrrrr',['Policy','Cost/day','Save/day','Positive kg/day','Viol. \%','$\|v\|_1$','Idle \%'],body)
    idle=json.loads((ROOT/'audit/v3_margin_idle_check.json').read_text())
    lines.append(f'The MARGIN schedule is inactive on all 84 ERCOT-input sampled days at the declared $10^{{-6}}$~kWh/day tolerance: its maximum daily $\\ell_1$ exchange change is {idle["max_l1_intervention_kwh_per_day"]:.2e}~kWh. This is verified from hourly actions, not inferred from rounded expense. CV32 saves $30.3$ synthetic USD/day relative to ROBOX while retaining $0.112$~kg/day of positive modeled change. The margin trades away those operational savings to eliminate reference-relative change in this fitted response. No measured intervention is available to validate its real emissions effect.')
    lines.append(r'This idle outcome illustrates a different failure mode from a positive emissions change: a conservative margin may meet its reference-relative target by selecting the reference itself. Such a controller can appear perfectly safe on violation frequency while supplying none of the operating benefit sought from flexibility or storage. The finding depends on the corrected average factor in the objective and on the fitted response, and should not be read as a general claim that ERCOT batteries ought to remain idle.')
    (MANUSCRIPT/'results_generated.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    # Supplementary machine-generated tables.
    supp=[]
    supp.append(r'\section{Complete tested-policy outcomes}')
    supp.append('All values are computed from the saved daily/hourly schedules. Positive change is evaluated against the same fixed-demand, no-storage physical reference. Expense savings use the matching ROBOX operation on each sampled date.')
    supp.extend([r'\small',r'\begin{longtable}{llrrrrrr}',
      r'\caption{All corrected final-policy outcomes. Synthetic rows aggregate 184 sampled days per regime; ERCOT-input rows use 84 sampled days. Mean+ and P95+ condition on a positive daily change.}\label{tab:sfull}\\',
      r'\toprule',row(['Regime','Policy','Save/day','L kg/day','Viol. \%','Mean+','P95+','Idle \%']),r'\midrule',r'\endfirsthead',
      r'\toprule',row(['Regime','Policy','Save/day','L kg/day','Viol. \%','Mean+','P95+','Idle \%']),r'\midrule',r'\endhead'])
    for _,z in trade.sort_values(['regime','policy']).iterrows():
        supp.append(row([regime(z.regime),policy(z.policy),fmt(-z.expense_vs_ROBOX_usd_per_day),
          fmt(z.positive_kg_per_day,2),fmt(100*z.violation_fraction,1),
          fmt(z.mean_kg_given_violation,1),fmt(z.p95_kg_given_violation,1),
          fmt(100*z.idle_intervention_fraction,0)]))
    supp.extend([r'\bottomrule',r'\end{longtable}',r'\normalsize'])
    supp.append(r'\section{Scenario-sampling and temporal uncertainty}')
    supp.append('The selected 2025 observations are four calendar days apart. One, two, four and seven adjacent sampled observations span 4, 8, 16 and 28 calendar days, respectively. Circular resampling uses the same calendar-index draw for all load/scenario strata to retain shared-weather dependence. The intervals quantify temporal variability conditional on two load realisations, three scenario draws and the synthetic model. The number of draws is too small for a population interval over scenario generation.')
    supp.extend([r'\small',r'\begin{longtable}{lrrrrr}',
      r'\caption{Block-length sensitivity for the paired CV128--CV32 positive-severity difference (kg/day).}\label{tab:sbootstrap}\\',r'\toprule',
      row(['Regime','Sampled block','Calendar span','Mean','Lower 95\%','Upper 95\%']),r'\midrule',r'\endfirsthead',
      r'\toprule',row(['Regime','Sampled block','Calendar span','Mean','Lower 95\%','Upper 95\%']),r'\midrule',r'\endhead'])
    for _,z in boots.iterrows():
        supp.append(row([regime(z.regime),int(z.block_sampled_observations),int(z.calendar_span_days),
          fmt(z.positive_difference_mean_kg_per_day,2),fmt(z.positive_difference_ci_low,2),fmt(z.positive_difference_ci_high,2)]))
    supp.extend([r'\bottomrule',r'\end{longtable}',r'\normalsize'])
    draw=daily.groupby(['regime','scenario_draw','demand_seed'],as_index=False).agg(
        difference=('paired_difference_kg','mean'),cost_difference=('cost_difference_usd','mean'))
    supp.extend([r'\small',r'\begin{longtable}{llrrr}',
      r'\caption{Mean paired CV128--CV32 difference by scenario draw and load seed.}\label{tab:sdraw}\\',r'\toprule',
      row(['Regime','Draw','Demand seed','$\Delta L$ kg/day','$\Delta$cost/day']),r'\midrule',r'\endfirsthead',
      r'\toprule',row(['Regime','Draw','Demand seed','$\Delta L$ kg/day','$\Delta$cost/day']),r'\midrule',r'\endhead'])
    for _,z in draw.iterrows():supp.append(row([regime(z.regime),z.scenario_draw,int(z.demand_seed),
        fmt(z.difference,2),fmt(z.cost_difference,2)]))
    supp.extend([r'\bottomrule',r'\end{longtable}',r'\normalsize'])
    supp.append(r'\section{State and source-unit audits}')
    supp.append('The evaluation implements an intermittent policy on a continuous calendar: the optimiser acts on every fourth day only, while intervening days run fixed reference tasks, idle storage and the ordinary attributional ledger. The past 168 hourly observations used at each active decision include intervening dates. Daily terminal battery energy equals opening energy. The model assumes no self-discharge; auxiliaries are proportional to charge/discharge and therefore zero while idle. Carbon inventory is carried through every date. The paper reports outcomes on selected active dates; full-window operational expense includes reference operation on intervening dates. Independent episode resets would change attributional allocations and are not used.')
    supp.append(f'The explicit completion checked {timeline["runs"]} final-comparison runs and {timeline["completed_skipped_days"]:,} intervening policy-days. Maximum state gap was {timeline["max_state_gap"]:.1e}, conservation error {timeline["max_conservation_error"]:.2e}, and skipped-day meter demand {timeline["max_skipped_meter_kw"]:.1f}~kW against a 2000~kW limit. Representative original schedules were re-executed under the corrected simulator with zero hourly difference. The completion leaves all selected-day costs and emission changes unchanged under the declared model.')
    supp.extend([r'\small',r'\begin{longtable}{lrrrr}',
      r'\caption{Matched full-window expense across first-to-last-selected dates. Values average the two synthetic load seeds within each regime; the regional-input row is one fitted system. The interaction is divided by selected active days.}\label{tab:swindow}\\',r'\toprule',
      row(['Regime','Calendar days','Active days','Meter saving/day','$I$/active day']),r'\midrule',r'\endfirsthead',
      r'\toprule',row(['Regime','Calendar days','Active days','Meter saving/day','$I$/active day']),r'\midrule',r'\endhead'])
    for rg in REGIMES:
        z=full[full.run.str.endswith('_'+rg)]
        supp.append(row([regime(rg),int(z.calendar_days_first_to_last_selected.mean()),
            int(z.selected_days.mean()),fmt(z.meter_aggregation_saving_full_usd_per_calendar_day.mean(),2),
            fmt(z.interaction_usd_per_selected_day.mean(),2)]))
    z=full[full.run=='v3_eia_confirmation_2024'].iloc[0]
    supp.append(row(['eia erco',int(z.calendar_days_first_to_last_selected),int(z.selected_days),
        fmt(z.meter_aggregation_saving_full_usd_per_calendar_day,2),fmt(z.interaction_usd_per_selected_day,2)]))
    supp.extend([r'\bottomrule',r'\end{longtable}',r'\normalsize'])
    supp.append(f'The state audit checked {state["runs_checked"]} saved policy runs and found a maximum cross-sampled-day state gap of {state["max_state_gap"]:.2e}. The legacy ERCOT-input attributional inventory departed by up to {state["legacy_ercot_max_departure_kg"]:.1f}~kg from an independent-reset value under the 1000-fold factor error; the corrected ERCOT-input maximum was {state["corrected_ercot_max_departure_kg"]:.1f}~kg. These are attributional states, not consequential emission changes.')
    supp.append('The unit correction altered only the ERCOT-input scaled baseline and average-factor columns, apart from floating-point CSV round-trip changes below $4\\times10^{-15}$ in two flexible-load inputs. The average factor enters forecasts, the carbon-priced objective and the attributional ledger; the baseline enters absolute system/reference emissions. Corrected decisions changed for carbon-priced policies, so all 15 regional-input policies were rerun in both years. The 2022-fitted marginal response derivative, curvature, scenario residuals, synthetic margin calibration, tariffs and selected dates were unchanged. S1 has no direct factor dependency but a numerically degenerate optimum changed under tiny CSV round-trip perturbations; its corrected outcome is retained. Original erroneous outputs remain in the audit archive.')
    supp.append(r'\section{Exploratory failure-condition decomposition}')
    supp.append('The following table conditions on violating days. Signed terms sum to mean positive severity. Opposing signs are retained; no percentage attribution is computed when cancellation is possible. Factor and response flips are defined in the main text. These diagnostics use realised future data and cannot be used as causal decision-time warnings.')
    supp.extend([r'\small',r'\begin{longtable}{llrrrrr}',
      r'\caption{Complete signed decomposition on positive-change days (kg/day), including all matched policies.}\label{tab:sdecomp}\\',r'\toprule',
      row(['Regime','Policy','Viol. days','Point','Factor error','Response','Total']),r'\midrule',r'\endfirsthead',
      r'\toprule',row(['Regime','Policy','Viol. days','Point','Factor error','Response','Total']),r'\midrule',r'\endhead'])
    for _,z in trade.sort_values(['regime','policy']).iterrows():
        supp.append(row([regime(z.regime),policy(z.policy),int(round(z.violation_fraction*z.days)),
          fmt(z.mean_point_kg_on_violation,2),fmt(z.mean_factor_error_kg_on_violation,2),
          fmt(z.mean_response_kg_on_violation,2),fmt(z.mean_kg_given_violation,2)]))
    supp.extend([r'\bottomrule',r'\end{longtable}',r'\normalsize'])
    dom=pd.read_csv(TABLES/'v3_tested_case_dominance.csv')
    supp.append(r'\section{Two-metric dominance within tested cases}')
    supp.append('A listed policy has no higher mean expense and no higher mean positive emissions change than the dominated policy, with at least one strict improvement. This comparison ignores other objectives and uncertainty; it does not establish general superiority.')
    supp.extend([r'\small',r'\begin{longtable}{lllr}',
      r'\caption{Selected tested-case dominance relationships. The full machine-readable CSV retains all pairs.}\label{tab:sdominance}\\',r'\toprule',
      row(['Regime','Dominated','Dominating','Cost advantage/day']),r'\midrule',r'\endfirsthead',
      r'\toprule',row(['Regime','Dominated','Dominating','Cost advantage/day']),r'\midrule',r'\endhead'])
    for _,z in dom.iterrows():supp.append(row([regime(z.regime),policy(z.dominated),policy(z.dominating),
        fmt(z.cost_advantage_usd_per_day,2)]))
    supp.extend([r'\bottomrule',r'\end{longtable}',r'\normalsize'])
    (MANUSCRIPT/'supplement_generated.tex').write_text('\n'.join(supp)+'\n',encoding='utf-8')
    fig,ax=plt.subplots(figsize=(7.3,4.5))
    colors={'coal_first':'#ad3f36','gas_first':'#317c7b','solar_rich':'#6a4c93'}
    marks={'CV8':'o','CV32':'s','CV128':'^','MARGIN':'D','G_worst':'x','ROBOX':'P'}
    for rg in REGIMES:
        for pp,marker in marks.items():
            z=trade[(trade.regime==rg)&(trade.policy==pp)].iloc[0]
            ax.scatter(-z.expense_vs_ROBOX_usd_per_day,z.positive_kg_per_day,
                       color=colors[rg],marker=marker,s=55)
    from matplotlib.lines import Line2D
    from matplotlib.legend import Legend
    regime_legend=ax.legend([Line2D([0],[0],marker='o',linestyle='',color=colors[rg]) for rg in REGIMES],
        [regime(rg) for rg in REGIMES],title='Regime (colour)',frameon=False,
        loc='upper left',bbox_to_anchor=(1.02,1.0),borderaxespad=0)
    ax.add_artist(regime_legend)
    ax.legend([Line2D([0],[0],marker=marks[pp],linestyle='',color='black') for pp in marks],
        [pp.replace('_','-') for pp in marks],title='Policy (marker)',frameon=False,
        loc='upper left',bbox_to_anchor=(1.02,.67),borderaxespad=0,fontsize=8)
    ax.set_xlabel('Operational saving relative to no intervention (synthetic USD/day)')
    ax.set_ylabel('Positive consequential change (kg CO$_2$/day)')
    ax.set_ylim(-1,38)
    ax.grid(alpha=.2);fig.subplots_adjust(left=.13,right=.72,bottom=.15,top=.96)
    fig.savefig(ROOT/'figures/v3_guard_tradeoff.pdf');plt.close(fig)
    print(json.dumps({'main_tables':5,'supplement_tables':6,'figure':'v3_guard_tradeoff.pdf'}))

if __name__=='__main__':main()
