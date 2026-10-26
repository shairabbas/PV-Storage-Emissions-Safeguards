"""Attributional ledger and explicit transferable-surplus settlement."""
import numpy as np


def ledger(loads, pv, charge, discharge, factors, soc0, carbon0, eta, auxiliary):
    T=len(charge)
    names=('soc_start','soc_end','carbon_start','carbon_end','import','export',
           'bus_intensity','load_carbon','loss_carbon','aux_carbon','export_carbon',
           'source_carbon','carbon_residual','energy_residual')
    out={name:np.zeros(T) for name in names}
    out['participant_carbon']=np.zeros((3,T))
    S=float(soc0); Q=float(carbon0)
    for t in range(T):
        c,d=float(charge[t]),float(discharge[t])
        aux=auxiliary*(c+d)
        demand=float(loads[:,t].sum()); renewable=float(pv[:,t].sum())
        q=demand-renewable+c-d+aux
        gi,ge=max(q,0),max(-q,0)
        intensity=Q/S if S>1e-9 else 0.
        removed=(d/eta)*intensity
        supply=gi+renewable+d
        carbon_in=gi*factors[t]+d*intensity
        mix=carbon_in/supply if supply>1e-10 else 0.
        S2=S+eta*c-d/eta
        Q2=Q+eta*c*mix-removed
        loss=(1-eta)*c*mix+(1/eta-1)*d*intensity
        consumption=demand*mix; exported=ge*mix; auxcarbon=aux*mix
        vals=(S,S2,Q,Q2,gi,ge,mix,consumption,loss,auxcarbon,exported,
              gi*factors[t],gi*factors[t]+Q-Q2-consumption-loss-auxcarbon-exported,
              gi+renewable+d-demand-c-aux-ge)
        for name,value in zip(names,vals): out[name][t]=value
        out['participant_carbon'][:,t]=loads[:,t]*mix
        S,Q=S2,Q2
    return out,S,Q


def settlement(baseline_bills, real_cost):
    """Budget-balanced contract; negative surplus is explicit operator deficit."""
    bills=np.asarray(baseline_bills,dtype=float)
    surplus=float(bills.sum()-real_cost)
    benefits=np.full(len(bills),.8*max(surplus,0)/len(bills))
    charges=bills-benefits
    margin=.2*surplus if surplus>=0 else surplus
    return {'surplus':surplus,'charges':charges,'benefits':benefits,'operator_margin':margin,
            'budget_residual':float(charges.sum()-real_cost-margin)}
