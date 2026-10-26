from dataclasses import dataclass, asdict
import time
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix


@dataclass
class Settings:
    capacity: float = 600.
    power: float = 150.
    efficiency: float = .95
    auxiliary: float = .003
    degradation: float = .015
    discomfort: float = .002
    carbon_price: float = .08
    alpha: float = .8
    factor_error: float = 1.
    critical_forecast_bias: float = 1.
    pv_forecast_bias: float = 1.
    carbon_forecast_bias: float = 1.
    shuffle_residual_hours: bool = False
    pv_scale: float = 1.
    demand_scale: float = 1.
    flex_scale: float = 1.
    participation: bool = True
    grid_limit: float = 2000.
    time_limit: float = 10.
    scenario_count: int = 8
    scenario_seed: int = 20261019
    scenario_seasonal: bool = False
    margin: float = 0.


def independent_bills(critical, flex, pv, buy, sell):
    q = critical+flex-pv
    return (np.maximum(q,0)*buy - np.maximum(-q,0)*sell).sum(axis=1)


def optimize(critical, f0, pv, buy, sell, aef, mef, blocks, policy, cfg, start_soc):
    """One 24-hour MILP; no future reference outcomes enter this function."""
    T, N = 24, 3
    # c,d,energy,import,export,mode,flex(3*24),abs-flex(3*24),zeta,excess_s
    ids={}; n=0
    for name, size in [('c',T),('d',T),('s',T),('i',T),('e',T),('mode',T),
                       ('f',N*T),('u',N*T),('z',1),('xi',len(blocks)),
                       ('w',T if policy=='MARGIN' else 0)]:
        ids[name]=np.arange(n,n+size); n+=size
    c,d,s,gi,ge,y,f,u,z,xi,w=[ids[k] for k in ['c','d','s','i','e','mode','f','u','z','xi','w']]
    f=f.reshape(N,T); u=u.reshape(N,T)
    lower=np.zeros(n); upper=np.full(n,np.inf); integer=np.zeros(n)
    upper[c]=cfg.power; upper[d]=cfg.power; upper[s]=cfg.capacity
    upper[gi]=cfg.grid_limit; upper[ge]=cfg.grid_limit; upper[y]=1; integer[y]=1
    upper[f]=np.repeat((3*f0.mean(axis=1))[:,None],T,axis=1)
    if policy in ('B4_noflex','S0'): lower[f]=f0; upper[f]=f0
    lower[z]=-np.inf
    eta=cfg.efficiency; a=cfg.auxiliary
    rows=[]; lo=[]; hi=[]
    def add(index, values, lb=-np.inf, ub=np.inf):
        row={}
        for j,v in zip(np.asarray(index).ravel(),np.asarray(values).ravel()):
            row[int(j)]=row.get(int(j),0)+float(v)
        rows.append(row); lo.append(lb); hi.append(ub)
    net=(critical-pv).sum(axis=0)
    for t in range(T):
        add([gi[t],ge[t],*f[:,t],c[t],d[t]], [1,-1,-1,-1,-1,-(1+a),1-a],net[t],net[t])
        idx=[s[t],c[t],d[t]]; vals=[1,-eta,1/eta]
        rhs=start_soc if t==0 else 0
        if t: idx.append(s[t-1]); vals.append(-1)
        add(idx,vals,rhs,rhs)
        add([c[t],y[t]],[1,-cfg.power],ub=0)
        add([d[t],y[t]],[1,cfg.power],ub=cfg.power)
        for j in range(N):
            add([f[j,t],u[j,t]],[1,-1],ub=f0[j,t])
            add([f[j,t],u[j,t]],[-1,-1],ub=-f0[j,t])
    add([s[-1]],[1],start_soc,start_soc)
    for j in range(N): add(f[j],np.ones(T),f0[j].sum(),f0[j].sum())
    real=np.zeros(n)
    real[gi]=buy; real[ge]=-sell
    model_degradation=0 if policy=='B4_nodeg' else cfg.degradation
    real[c]=model_degradation; real[d]=model_degradation; real[u]=cfg.discomfort
    objective=real.copy()
    if policy not in ('B1','B5','M1','S0','S1'):
        factors=np.full(T,float(aef.mean())) if policy=='B2' else aef
        objective[gi]+=cfg.carbon_price*factors
    if cfg.participation and policy != 'B4_nopart':
        baseline=float(independent_bills(critical,f0,pv,buy,sell).sum())
        # Actual degradation coefficient is retained in participation even in the no-degradation objective ablation.
        capcoef=real.copy(); capcoef[c]=cfg.degradation; capcoef[d]=cfg.degradation
        add(np.arange(n),capcoef,ub=baseline)
    guard = {'B4':'cvar','CV8':'cvar','CV32':'cvar','CV64':'cvar','CV128':'cvar',
             'CV32_SEAS':'cvar','CV32_S11':'cvar','CV32_S23':'cvar',
             'B4_nodeg':'cvar','B4_nopart':'cvar','B4_noflex':'cvar',
             'G_point':'point','G_mean':'mean','G_worst':'worst',
             'MARGIN':'margin'}.get(policy)
    factors=np.clip(mef[None,:]+cfg.factor_error*blocks,0,.95)
    def delta_row(m):
        ind=np.r_[f.ravel(),c,d]
        val=np.r_[np.tile(m,N),m*(1+a),-m*(1-a)]
        return ind,val,float(m@f0.sum(axis=0))
    if guard == 'margin':
        for t in range(T):
            fsum=float(f0[:,t].sum())
            add([*f[:,t],c[t],d[t],w[t]],
                [1,1,1,1+a,-(1-a),-1],ub=fsum)
            add([*f[:,t],c[t],d[t],w[t]],
                [-1,-1,-1,-(1+a),1-a,-1],ub=-fsum)
        ind,val,rhs=delta_row(mef)
        add(np.r_[ind,w],np.r_[val,np.full(T,cfg.margin)],ub=rhs)
    elif guard in ('point','mean'):
        ind,val,rhs=delta_row(mef if guard=='point' else factors.mean(axis=0))
        add(ind,val,ub=rhs)
    elif guard == 'worst':
        for m in factors:
            ind,val,rhs=delta_row(m); add(ind,val,ub=rhs)
    elif guard == 'cvar':
        for k,m in enumerate(factors):
            ind,val,rhs=delta_row(m)
            add(np.r_[ind,z,xi[k]],np.r_[val,-1,-1],ub=rhs)
        add(np.r_[z,xi],np.r_[1,np.full(len(xi),1/(len(xi)*(1-cfg.alpha)))],ub=0)
    A=lil_matrix((len(rows),n))
    for j,row in enumerate(rows):
        for k,v in row.items(): A[j,k]=v
    A=A.tocsr()
    tick=time.perf_counter()
    result=milp(objective,integrality=integer,bounds=Bounds(lower,upper),
        constraints=LinearConstraint(A,lo,hi),options={'time_limit':cfg.time_limit,'mip_rel_gap':1e-7})
    runtime=time.perf_counter()-tick
    fallback=result.x is None
    if not fallback:
        ax=A@result.x
        residual=max(np.max(np.asarray(lo)-ax),np.max(ax-np.asarray(hi)),
                     np.max(lower-result.x),np.max(result.x-upper))
        fallback=bool(residual>2e-5)
    if fallback:
        charge=np.zeros(T); discharge=np.zeros(T); flexible=f0.copy()
    else:
        charge=np.maximum(result.x[c],0); discharge=np.maximum(result.x[d],0)
        flexible=np.maximum(result.x[f],0)
    delta=(flexible-f0).sum(axis=0)+(1+a)*charge-(1-a)*discharge
    scenario_delta=factors@delta
    tail=np.sort(scenario_delta)[::-1]
    # Empirical CVaR integrates fractional boundary scenario mass exactly.
    mass=len(tail)*(1-cfg.alpha); whole=int(np.floor(mass)); frac=mass-whole
    risk=(tail[:whole].sum()+(tail[whole]*frac if frac>1e-10 else 0))/mass
    return {'charge':charge,'discharge':discharge,'flexible':flexible,
        'status':str(result.message),'status_code':int(result.status),'fallback':fallback,
        'runtime':runtime,'gap':float(getattr(result,'mip_gap',np.nan) or 0),
        'dual_bound':float(getattr(result,'mip_dual_bound',np.nan) or 0),
        'objective':float(result.fun) if result.fun is not None else None,
        'surrogate_cvar':float(risk),'surrogate_mean':float(scenario_delta.mean()),
        'surrogate_worst':float(scenario_delta.max()),'guard':guard or 'none'}
