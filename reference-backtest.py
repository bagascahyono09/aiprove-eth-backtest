import csv, math

rows = list(csv.DictReader(open('/tmp/ch/bars.csv')))
C = [float(r['close']) for r in rows]
H = [float(r['high']) for r in rows]
L = [float(r['low']) for r in rows]
N = len(C)
print('bars:', N, 'start', C[0], 'end', C[-1], 'change %', round((C[-1]/C[0]-1)*100, 2))

def ema(x, n):
    k = 2/(n+1); out=[x[0]]
    for v in x[1:]: out.append(out[-1] + k*(v-out[-1]))
    return out

def backtest(pos, fee_bps=5.0, slip_bps=2.0):
    # pos[t] in [-1,1] decided at close t, held over bar t+1
    pnl = 0.0; equity = [0.0]; prev = 0.0
    cost_rate = (fee_bps + slip_bps) / 10000.0
    for t in range(N-1):
        p = pos[t]
        pnl += p * (C[t+1]-C[t]) / C[t]
        pnl -= abs(p - prev) * cost_rate
        prev = p
        equity.append(pnl)
    peak, mdd = -1e9, 0.0
    for e in equity:
        peak = max(peak, e); mdd = max(mdd, peak - e)
    return pnl*100, mdd*100  # in %

def strat_ema(f, s):
    ef, es = ema(C, f), ema(C, s)
    return [1.0 if ef[i] > es[i] else -1.0 for i in range(N)]

def strat_ema_band(f, s, band_bps=5):
    ef, es = ema(C, f), ema(C, s)
    out = []
    for i in range(N):
        d = (ef[i]-es[i])/C[i]*10000
        out.append(1.0 if d > band_bps else (-1.0 if d < -band_bps else 0.0))
    return out

def strat_mom(lb, thresh_bps=10):
    out = [0.0]*N
    for i in range(N):
        if i >= lb:
            r = (C[i]/C[i-lb]-1)*10000
            out[i] = 1.0 if r > thresh_bps else (-1.0 if r < -thresh_bps else 0.0)
    return out

def strat_donchian(lb):
    out=[0.0]*N
    for i in range(N):
        if i>=lb:
            hh=max(H[i-lb:i]); ll=min(L[i-lb:i])
            out[i]= 1.0 if C[i]>hh else (-1.0 if C[i]<ll else out[i-1])
    return out

cands = {
 'ema 10/60': strat_ema(10,60), 'ema 20/120': strat_ema(20,120), 'ema 5/40': strat_ema(5,40),
 'ema band 10/60 5bp': strat_ema_band(10,60,5), 'ema band 20/120 8bp': strat_ema_band(20,120,8),
 'mom 60 10bp': strat_mom(60,10), 'mom 120 15bp': strat_mom(120,15), 'mom 240 20bp': strat_mom(240,20),
 'donchian 120': strat_donchian(120), 'donchian 240': strat_donchian(240),
 'buy&hold': [1.0]*N, 'short&hold': [-1.0]*N,
}
for name, pos in cands.items():
    p5, d5 = backtest(pos, 5, 2)
    p10, d10 = backtest(pos, 10, 3)
    print(f"{name:22s} pnl@7bp={p5:+.2f}% mdd={d5:.2f}% | pnl@13bp={p10:+.2f}% mdd={d10:.2f}%")

def strat_donchian2(entry_lb, exit_lb):
    out=[0.0]*N; cur=0.0
    for i in range(N):
        if i>=entry_lb:
            hh=max(H[i-entry_lb:i]); ll=min(L[i-entry_lb:i])
            if C[i]>hh: cur=1.0
            elif C[i]<ll: cur=-1.0
            elif cur==1.0 and i>=exit_lb and C[i]<min(L[i-exit_lb:i]): cur=0.0
            elif cur==-1.0 and i>=exit_lb and C[i]>max(H[i-exit_lb:i]): cur=0.0
        out[i]=cur
    return out

def strat_donchian_vol(entry_lb):
    # breakout with ATR-ish range filter: skip entries when recent range is tiny (chop)
    out=[0.0]*N; cur=0.0
    rng=[0.0]*N
    for i in range(1,N): rng[i]=max(H[i]-L[i], rng[i-1]*0.97)
    for i in range(N):
        if i>=entry_lb:
            hh=max(H[i-entry_lb:i]); ll=min(L[i-entry_lb:i])
            mid=(hh+ll)/2
            width=(hh-ll)/mid
            if C[i]>hh and width>0.004: cur=1.0
            elif C[i]<ll and width>0.004: cur=-1.0
        out[i]=cur
    return out

for name, pos in {'donchian 240/120 exit': strat_donchian2(240,120), 'donchian 360': strat_donchian(360), 'donchian 240 volfilter': strat_donchian_vol(240), 'donchian 180': strat_donchian(180)}.items():
    p5, d5 = backtest(pos, 5, 2); p10, d10 = backtest(pos, 10, 3)
    trades = sum(1 for i in range(1,N) if pos[i]!=pos[i-1])
    print(f"{name:24s} pnl@7bp={p5:+.2f}% mdd={d5:.2f}% | pnl@13bp={p10:+.2f}% mdd={d10:.2f}% | changes={trades}")
