from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
P=Path(__file__).resolve().parents[1];D=P/'plotting_data';O=P/'figures'
O.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7.5,'axes.labelsize':7.5,'axes.titlesize':8,'legend.fontsize':6.5,'xtick.labelsize':7,'ytick.labelsize':7,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none','lines.linewidth':1.2})
navy='#19364B';teal='#247C8A';orange='#CD7447';purple='#8067A5';gray='#657582';colors=[teal,orange,purple];regs=['coal_first','gas_first','solar_rich'];rnames=['Coal-first','Gas-first','Solar-rich'];pols=['CV8','CV32','CV128','MARGIN','G_worst'];names=['CV8','CV32','CV128','MARGIN','G-worst'];marks=['o','s','^','D','X']
T=pd.read_csv(D/'v3_failure_tradeoff_summary.csv');B=pd.read_csv(D/'v3_cv32_128_bootstrap.csv');S=pd.read_csv(D/'v3_cv32_128_summary.csv');pairs=pd.read_csv(D/'v3_cv32_128_paired_daily.csv')
def row(r,p):
 z=T[(T.regime==r)&(T.policy==p)];assert len(z)==1;return z.iloc[0]
def title(ax,s):ax.set_title(s,loc='left',weight='bold',pad=9,color=navy);ax.grid(alpha=.15,lw=.5);ax.set_axisbelow(True)
def save(fig,n):
 for ext in ['pdf','svg','png']:fig.savefig(O/f'{n}.{ext}',dpi=600 if ext=='png' else 300,bbox_inches='tight',facecolor='white')
 plt.close(fig)
# 1. Conceptual diagram at publication scale.
fig,ax=plt.subplots(figsize=(7.2,6.9));fig.subplots_adjust(left=.01,right=.99,bottom=.01,top=.99);ax.set(xlim=(0,100),ylim=(0,100));ax.axis('off')
def box(x,y,w,h,t,b='',c=teal):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.25,rounding_size=1',fc='#F1F6F7' if c==teal else '#F5F1F8' if c==purple else '#FAF1EB',ec=c,lw=.8))
 ax.text(x+w/2,y+h-(2.8 if b else h/2),t,ha='center',va='center',weight='bold',fontsize=7.5,color=navy)
 if b:ax.text(x+w/2,y+(h-3.5)/2,b,ha='center',va='center',fontsize=7,color=gray,linespacing=1.3)
def ar(a,b,c=teal,style='-|>'):ax.add_patch(FancyArrowPatch(a,b,arrowstyle=style,color=c,lw=.9,mutation_scale=8))
ax.text(1,97,'(a) Shared physical system and matched cases',weight='bold',fontsize=9,color=navy)
for i,x in enumerate([1,35,69]):
 box(x,79,29,12,f'Participant {i+1}','Critical demand + PV\nDaily flexible task');ar((x+14.5,79),(x+14.5,74),style='<->')
ax.plot([15.5,83.5],[74,74],color=teal,lw=1.8)
box(1,55,29,12,'Shared battery','600 kWh / 150 kW\nEfficiency: 0.95 per direction');ar((15.5,74),(15.5,67),style='<->')
box(35,55,29,12,'Common meter','Net import / export\nAction-related auxiliaries');ar((49.5,74),(49.5,67),style='<->')
box(69,55,29,12,'Upstream response','Three synthetic merit orders\nSeparate ERCOT-input check',c=orange);ar((64,61),(69,61),c=orange,style='<->')
ax.text(1,50,'B0 → M0: aggregate billing     M0 → M1: task flexibility without storage',fontsize=7.3,color=gray)
ax.text(1,46,'M0 → S0: storage with fixed tasks     M1 → S1: storage after flexibility',fontsize=7.3,color=gray)
ax.text(1,40,'(b) Decision-time information and realised-future replay',weight='bold',fontsize=9,color=navy)
box(1,27,29,9,'Historical information','Seven completed days\nHistorical factor residuals')
box(35,27,29,9,'Forecasts + commitments','Load / PV / factors\nKnown task energy and tariffs');ar((30,31.5),(35,31.5))
box(69,27,29,9,'24-hour scheduling','Selected emissions guard\nBattery + flexible tasks');ar((64,31.5),(69,31.5))
ax.plot([1,98],[23,23],ls='--',color=orange,lw=.8);ax.text(1,24,'Decisions fixed before realised-future diagnostics',color=orange,fontsize=7)
box(69,10,29,9,'Saved realised operation','Every fourth day active\nReference operation between',c=orange);ar((83.5,27),(83.5,19),c=orange)
box(35,10,29,9,'Common response replay','Controlled E(B + q)\nReference E(B + q⁰)',c=purple);ar((69,14.5),(64,14.5),c=orange)
box(1,10,29,9,'Signed change + diagnostics','Point + factor error\n+ nonlinear remainder',c=orange);ar((35,14.5),(30,14.5),c=purple)
ax.text(1,3,'Reference: fixed tasks + idle battery, with the same realised load and PV. Replay is model-generated.',fontsize=7,color=gray)
save(fig,'Figure_1_Framework')
# 2. Four-panel performance.
fig,axs=plt.subplots(2,2,figsize=(7.2,6.25));fig.subplots_adjust(left=.10,right=.98,top=.89,bottom=.13,hspace=.64,wspace=.36)
ax=axs[0,0];title(ax,'(a) Savings and positive-change severity')
for i,r in enumerate(regs):
 for j,p in enumerate(pols):v=row(r,p);ax.scatter(-v.expense_vs_ROBOX_usd_per_day,v.positive_kg_per_day,c=colors[i],marker=marks[j],s=23,edgecolor='white',lw=.3,zorder=3)
ax.scatter(0,0,c=navy,marker='P',s=22);ax.set(xlabel='Saving (synthetic USD / active day)',ylabel='Mean positive change\n(kg CO$_2$ / active day)',xlim=(-5,144),ylim=(-1.5,37))
ax=axs[0,1];title(ax,'(b) Positive-change days (%)');freq=np.array([[100*row(r,p).violation_fraction for p in pols] for r in regs]);ax.imshow(freq,vmin=0,vmax=60,cmap='YlOrRd',aspect='auto');ax.grid(False);ax.set_xticks(range(5),names,rotation=25,ha='right');ax.set_yticks(range(3),rnames);ax.tick_params(length=0)
for i in range(3):
 for j in range(5):ax.text(j,i,f'{freq[i,j]:.1f}',ha='center',va='center',fontsize=7,color='white' if freq[i,j]>38 else navy,weight='bold')
ax=axs[1,0];title(ax,'(c) Severity among violating days');x=np.arange(5)
for i,r in enumerate(regs):ax.bar(x+(i-1)*.24,[row(r,p).p95_kg_given_violation for p in pols],width=.22,color=colors[i])
ax.set_xticks(x,names,rotation=25,ha='right');ax.set(ylabel='Conditional P95\n(kg CO$_2$ / violating day)',ylim=(0,415))
ax=axs[1,1];title(ax,'(d) CV128 − CV32: three draws')
for i,r in enumerate(regs):
 b=B[(B.regime==r)&(B.block_sampled_observations==4)].iloc[0];s=S[S.regime==r].iloc[0];m=b.positive_difference_mean_kg_per_day;y=2-i
 ax.errorbar(m,y,xerr=[[m-b.positive_difference_ci_low],[b.positive_difference_ci_high-m]],fmt='D',color=colors[i],ms=4,capsize=2,lw=1.2)
 for j,d in enumerate(['default','11','23']):ax.scatter(json.loads(s.draw_means_kg_per_day)[d],y+.17,marker=['o','s','^'][j],facecolors='white',edgecolors=colors[i],s=14,lw=.7,zorder=3)
ax.axvline(0,c=gray,ls='--',lw=.7);ax.set_yticks([2,1,0],rnames);ax.set(xlim=(-3.6,2.3),ylim=(-.4,2.5),xlabel='Positive-severity difference\n(kg CO$_2$ / active day)')
handles=[Line2D([],[],color=c,lw=3,label=r) for c,r in zip(colors,rnames)]
fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.53,.995),ncol=3,frameon=False)
fig.legend(handles=[Line2D([],[],ls='',marker=m,color=navy,label=n,ms=4) for m,n in zip(marks,names)],loc='upper center',bbox_to_anchor=(.53,.953),ncol=5,frameon=False,columnspacing=1.2)
save(fig,'Figure_2_Performance')
# 3. Mechanisms + regional input, full precision.
fig,axs=plt.subplots(1,2,figsize=(7.2,4.6),gridspec_kw={'width_ratios':[1.2,1]});fig.subplots_adjust(left=.10,right=.98,top=.88,bottom=.22,wspace=.38)
ax=axs[0];title(ax,'(a) Signed failure decomposition');ys=[10,9,8,6,5,4,2,1,0];tc=['#517C9B','#E49B46',purple]
for i,r in enumerate(regs):
 for j,p in enumerate(['CV8','CV32','MARGIN']):
  v=row(r,p);y=ys[i*3+j];pos=neg=0
  for k,key in enumerate(['mean_point_kg_on_violation','mean_factor_error_kg_on_violation','mean_response_kg_on_violation']):
   val=v[key];ax.barh(y,val,left=pos if val>=0 else neg,height=.6,color=tc[k]);pos+=max(val,0);neg+=min(val,0)
  ax.scatter(v.mean_kg_given_violation,y,marker='D',s=16,facecolor='white',edgecolor=navy,lw=.7,zorder=3)
 ax.text(-225,11-i*4,rnames[i],color=gray,fontsize=7,weight='bold')
ax.set_yticks(ys,['CV8','CV32','MARGIN']*3);ax.set(xlim=(-230,285),ylim=(-.7,11.7),xlabel='kg CO$_2$ / violating active day');ax.axvline(0,c=gray,lw=.6)
fig.legend(handles=[Line2D([],[],lw=4,color=c,label=n) for c,n in zip(tc,['Point surrogate','Factor-forecast error','Nonlinear remainder'])]+[Line2D([],[],ls='',marker='D',mfc='white',mec=navy,ms=4,label='Total change')],loc='lower left',bbox_to_anchor=(.07,.015),ncol=2,frameon=False,fontsize=6.5)
ax=axs[1];title(ax,'(b) ERCOT-input trade-off')
for j,p in enumerate(['B3']+pols):
 v=row('eia_erco',p);xx=-v.expense_vs_ROBOX_usd_per_day;yy=v.positive_kg_per_day;ax.scatter(xx,yy,marker=['o','o','s','^','D','X'][j],s=28,c=orange if p=='B3' else teal,edgecolor='white',lw=.3,zorder=3)
 off={'B3':(-8,6),'CV8':(5,3),'CV32':(5,4),'CV128':(4,-13),'MARGIN':(5,7),'G_worst':(-33,-13)}[p];ax.annotate(p.replace('_','-'),(xx,yy),off,textcoords='offset points',fontsize=6.5)
ax.set_yscale('symlog',linthresh=.1,linscale=1);ax.set_yticks([0,.1,1,10,30],['0','0.1','1','10','30']);ax.set(xlim=(-5,83),ylim=(-.015,65),xlabel='Saving (synthetic USD / active day)',ylabel='Mean positive change\n(kg CO$_2$ / active day)');ax.text(.04,.72,'MARGIN:\n100% idle days',transform=ax.transAxes,color=teal,fontsize=7,bbox={'fc':'#EAF3F3','ec':'none','pad':4})
save(fig,'Figure_3_Mechanisms')
# 4. Hourly case, use checked source CSV.
d=pd.read_csv(D/'Figure_5_Selected_Day_Full_Precision.csv');h=np.arange(24)
fig,axs=plt.subplots(2,2,figsize=(7.2,6.0));fig.subplots_adjust(left=.10,right=.98,top=.92,bottom=.12,hspace=.62,wspace=.37)
for ax in axs.flat:ax.set_xlim(-.5,23.5);ax.set_xticks([0,6,12,18,23])
ax=axs[0,0];title(ax,'(a) Marginal emissions factor');ax.step(h,d.forecast_mef_kg_per_kwh,where='mid',c=teal,label='Forecast');ax.step(h,d.realized_reference_mef_kg_per_kwh,where='mid',c=orange,label='Realised');ax.fill_between(h,d.forecast_mef_kg_per_kwh,d.realized_reference_mef_kg_per_kwh,step='mid',color=orange,alpha=.12);ax.set(ylabel='kg CO$_2$ / kWh',ylim=(.3,1));ax.legend(frameon=False,loc='lower left')
ax=axs[0,1];title(ax,'(b) Battery and task actions');ax.bar(h,d.charge,color=teal,width=.8,label='Charge');ax.bar(h,-d.discharge,color=orange,width=.8,label='Discharge (−)');ax.plot(h,d.task_shift_kwh,c=purple,label='Task deviation');ax.axhline(0,c=gray,lw=.6);ax.set_ylabel('kWh / hourly interval');ax.legend(frameon=False,fontsize=6,loc='lower left')
ax=axs[1,0];title(ax,'(c) Net grid exchange');ax.plot(h,d.q_reference,c=gray,ls='--',label='Reference');ax.plot(h,d.q_proposed,c=teal,label='Controlled');ax.fill_between(h,d.q_reference,d.q_proposed,color=teal,alpha=.12);ax.axhline(0,c=gray,lw=.6);ax.set(xlabel='Hour (UTC)',ylabel='kWh / hourly interval');ax.legend(frameon=False,loc='upper left')
ax=axs[1,1];title(ax,'(d) Cumulative signed decomposition')
for key,l,c,ls in [('point_surrogate_kg','Point',teal,'-'),('factor_forecast_error_kg','Factor error',orange,'-'),('nonlinear_response_remainder_kg','Remainder',purple,':'),('consequential_change_kg','Total',navy,'-')]:ax.plot(h,d[key].cumsum(),c=c,ls=ls,label=l)
ax.axhline(0,c=gray,lw=.6);ax.set(xlabel='Hour (UTC)',ylabel='Cumulative kg CO$_2$');ax.legend(frameon=False,fontsize=6,loc='lower left',ncol=2)
save(fig,'Figure_4_Hourly_Case')
# 5. Signed means, common scales for direct comparison.
r=pd.read_csv(D/'Figure_6_Signed_Emissions_Full_Precision.csv');fig,axs=plt.subplots(1,3,figsize=(7.2,3.4),sharex=True,sharey=True);fig.subplots_adjust(left=.10,right=.99,top=.85,bottom=.26,wspace=.18)
for i,(ax,reg) in enumerate(zip(axs,regs)):
 v=r[r.regime==reg];y=np.arange(len(v));title(ax,rnames[i]);ax.barh(y,v.mean_positive_kg,height=.56,color=orange,label='Positive magnitude');ax.barh(y,-v.mean_negative_magnitude_kg,height=.56,color=teal,label='Negative magnitude');ax.scatter(v.mean_signed_kg,y,c=navy,marker='D',s=15,zorder=3,label='Signed net mean');ax.axvline(0,c=gray,lw=.6);ax.set_yticks(y,[p.replace('_','-') for p in v.policy]);ax.set(xlim=(-180,270),xlabel='kg CO$_2$ / active day');ax.set_xticks([-150,0,150]);ax.grid(axis='y',visible=False)
axs[0].invert_yaxis();handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.52,.03),ncol=3,frameon=False,fontsize=6.5)
save(fig,'Figure_5_Signed_Emissions')
# S1. Existing uncertainty and draw sensitivity.
fig,axs=plt.subplots(1,2,figsize=(7.2,5));fig.subplots_adjust(left=.18,right=.99,top=.89,bottom=.18,wspace=.50)
ax=axs[0];title(ax,'(a) Resampling block length');ys=[];labs=[]
for i,r in enumerate(regs):
 for j,block in enumerate([1,2,4,7]):
  v=B[(B.regime==r)&(B.block_sampled_observations==block)].iloc[0];m=v.positive_difference_mean_kg_per_day;y=13-i*5-j;ys.append(y);labs.append(f'{block} obs. / {block*4} d');ax.errorbar(m,y,xerr=[[m-v.positive_difference_ci_low],[v.positive_difference_ci_high-m]],fmt='D',color=colors[i],ms=3,capsize=2,lw=1)
 ax.text(-3.4,14-i*5,rnames[i],fontsize=7,color=colors[i],weight='bold')
ax.set_yticks(ys,labs,fontsize=6.5);ax.set(xlim=(-3.5,1.8),ylim=(-1,15),xlabel='CV128 − CV32\n(kg CO$_2$ / active day)');ax.axvline(0,c=gray,ls='--',lw=.7)
ax=axs[1];title(ax,'(b) Draw and load seed');ys=[];labs=[]
for i,r in enumerate(regs):
 for j,draw in enumerate(['default','11','23']):
  y=10-i*4-j;ys.append(y);labs.append('Draw '+draw)
  z=pairs[(pairs.regime==r)&(pairs.scenario_draw.astype(str)==draw)].groupby('demand_seed').paired_difference_kg.mean();assert len(z)==2
  ax.plot(z.values,[y,y],color=colors[i],alpha=.5)
  for k,(seed,val) in enumerate(z.items()):ax.scatter(val,y,marker=['o','s'][k],s=18,c=colors[i],edgecolor='white',lw=.3,zorder=3)
 ax.text(-4.45,10.8-i*4,rnames[i],fontsize=7,color=colors[i],weight='bold')
ax.set_yticks(ys,labs,fontsize=6.5);ax.set(xlim=(-4.6,3.3),ylim=(-1,12),xlabel='CV128 − CV32\n(kg CO$_2$ / active day)');ax.axvline(0,c=gray,ls='--',lw=.7)
fig.legend(handles=[Line2D([],[],marker=m,ls='',color=navy,ms=4,label=str(seed)) for m,seed in zip(['o','s'],[271828,314159])],loc='lower center',bbox_to_anchor=(.56,.015),ncol=2,frameon=False,title='Load seed',title_fontsize=7)
save(fig,'Figure_S1_Robustness')
print('Built five main figures and one supplementary figure from full-precision inputs.')
