"""Render two explanatory vector figures from frozen V3 summary CSVs."""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'figures'
TABLES=ROOT/'tables'
REGIMES=[('coal_first','Coal-first'),('gas_first','Gas-first'),('solar_rich','Solar-rich')]
POLICIES=['CV8','CV32','MARGIN']


def audit_inputs():
    trade=pd.read_csv(TABLES/'v3_failure_tradeoff_summary.csv')
    selected=trade[(trade.regime.isin([r for r,_ in REGIMES]))&trade.policy.isin(POLICIES)]
    residual=(selected.mean_point_kg_on_violation+selected.mean_factor_error_kg_on_violation+
              selected.mean_response_kg_on_violation-selected.mean_kg_given_violation).abs()
    summary=pd.read_csv(TABLES/'v3_cv32_128_summary.csv')
    pooled=[]
    for _,row in summary.iterrows():
        assert int(row.paired_days)==552
        draw_means=json.loads(row.draw_means_kg_per_day)
        pooled.append(abs(np.mean(list(draw_means.values()))-row.difference_kg_per_day))
    assert residual.max()<1e-7 and max(pooled)<1e-7
    inputs=['v3_failure_tradeoff_summary.csv','v3_cv32_128_summary.csv','v3_cv32_128_bootstrap.csv']
    report={'source_sha256':{name:hashlib.sha256((TABLES/name).read_bytes()).hexdigest() for name in inputs},
            'decomposition_rows':len(selected),'max_signed_sum_error_kg':float(residual.max()),
            'max_draw_pool_mean_error_kg':float(max(pooled)),
            'simulations_executed':0}
    (ROOT/'audit/v6_figure_data_audit.json').write_text(json.dumps(report,indent=2)+'\n')


def decomposition():
    data=pd.read_csv(TABLES/'v3_failure_tradeoff_summary.csv')
    fig,axes=plt.subplots(3,1,figsize=(7.2,6.0),sharex=True,sharey=True)
    palette={'Point surrogate':'#276C9B','Factor forecast error':'#D47E20',
             'Nonlinear remainder':'#258477'}
    fields={'Point surrogate':'mean_point_kg_on_violation',
            'Factor forecast error':'mean_factor_error_kg_on_violation',
            'Nonlinear remainder':'mean_response_kg_on_violation'}
    offsets={'Point surrogate':-.24,'Factor forecast error':0.,'Nonlinear remainder':.24}
    for ax,(regime,title) in zip(axes,REGIMES):
        subset=data[(data.regime==regime)&data.policy.isin(POLICIES)].set_index('policy')
        y=np.arange(3)
        for label,column in fields.items():
            values=np.array([subset.loc[p,column] for p in POLICIES])
            ax.barh(y+offsets[label],values,height=.20,color=palette[label],
                    label=label,zorder=3)
        totals=np.array([subset.loc[p,'mean_kg_given_violation'] for p in POLICIES])
        ax.scatter(totals,y,marker='D',s=35,facecolors='white',edgecolors='#222222',
                   linewidths=1.3,label='Total change',zorder=5)
        ax.axvline(0,color='#444444',lw=.8,zorder=2)
        ax.set(xlim=(-270,270),yticks=y,yticklabels=POLICIES)
        ax.set_title(title,loc='left',fontsize=10,fontweight='semibold',pad=3)
        ax.invert_yaxis()
        ax.grid(axis='x',alpha=.18,zorder=0)
        ax.tick_params(labelsize=8)
    fig.supxlabel('Signed kg CO$_2$ per violating selected day',y=.07,fontsize=10)
    handles=[plt.Rectangle((0,0),1,1,color=palette[k]) for k in fields]
    handles.append(Line2D([0],[0],marker='D',linestyle='',markersize=6,
                          markerfacecolor='white',markeredgecolor='#222222'))
    fig.legend(handles,[*fields,'Total change'],loc='lower center',ncol=4,
               bbox_to_anchor=(.5,-.005),frameon=False,fontsize=8)
    fig.tight_layout(rect=(0,.14,1,1),h_pad=.65)
    fig.savefig(FIG/'v6_signed_failure_decomposition.pdf',bbox_inches='tight')
    plt.close(fig)


def paired_scenarios():
    summary=pd.read_csv(TABLES/'v3_cv32_128_summary.csv').set_index('regime')
    blocks=pd.read_csv(TABLES/'v3_cv32_128_bootstrap.csv')
    blocks=blocks[blocks.block_sampled_observations==4].set_index('regime')
    fig,ax=plt.subplots(figsize=(7.35,3.35))
    colors={'coal_first':'#276C9B','gas_first':'#D47E20','solar_rich':'#258477'}
    draw_symbols={'default':'o','11':'s','23':'^'}
    for i,(regime,label) in enumerate(REGIMES):
        row=summary.loc[regime]; ci=blocks.loc[regime]
        lo=ci.positive_difference_ci_low;hi=ci.positive_difference_ci_high
        mean=row.difference_kg_per_day
        ax.plot([lo,hi],[i,i],lw=3.2,color=colors[regime],solid_capstyle='round',zorder=2)
        ax.plot([lo,lo],[i-.075,i+.075],color=colors[regime],lw=1.2)
        ax.plot([hi,hi],[i-.075,i+.075],color=colors[regime],lw=1.2)
        ax.scatter([mean],[i],marker='D',s=62,color=colors[regime],edgecolors='white',zorder=4)
        draws=json.loads(row.draw_means_kg_per_day)
        for j,key in enumerate(('default','11','23')):
            ax.scatter([draws[key]],[i+(.16 if j==0 else -.16 if j==1 else .30)],
                       marker=draw_symbols[key],s=32,facecolors='white',
                       edgecolors=colors[regime],linewidths=1.3,zorder=5)
    ax.axvline(0,color='#333333',ls='--',lw=1)
    ax.set(xlim=(-3.5,2.6),ylim=(-.5,2.55),yticks=range(3),
           yticklabels=[x[1] for x in REGIMES],
           xlabel='CV128 minus CV32 mean positive severity (kg CO$_2$/selected day)')
    ax.invert_yaxis()
    ax.grid(axis='x',alpha=.17)
    handles=[Line2D([0],[0],marker='D',linestyle='',color='#333333',markersize=6,label='Pooled mean'),
             Line2D([0],[0],marker='o',linestyle='',markerfacecolor='white',
                    markeredgecolor='#333333',label='Default draw'),
             Line2D([0],[0],marker='s',linestyle='',markerfacecolor='white',
                    markeredgecolor='#333333',label='Draw 11'),
             Line2D([0],[0],marker='^',linestyle='',markerfacecolor='white',
                    markeredgecolor='#333333',label='Draw 23')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,-.02),
               ncol=4,fontsize=8,frameon=False)
    fig.tight_layout(rect=(0,.11,1,1))
    fig.savefig(FIG/'v6_paired_scenario_contrast.pdf',bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':
    audit_inputs()
    decomposition()
    paired_scenarios()
    print('Rendered two vector PDFs from frozen summary tables.')
