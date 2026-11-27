"""QQQ TREND / QQQ OG intraday bot backtest on QQQ 5-min bars, Exness USTEC costs.
Rules frozen in PREREG.md (same folder). Usage: python3 qqq_bots.py <data_dir>
data_dir holds qqq_idx.json.gz (trader-lab/data/idx/qqq.json.gz) and qqq_long.json.gz (trader-lab/data/long/QQQ.json.gz),
both from day-trader-skill branch claude/sweet-franklin-ovrtke."""
import sys, gzip, json, math, random, datetime as dt, statistics as st
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
RATIO = 41.0            # NDX points per $1 of QQQ
LOT_USD_PER_PT = 0.05   # 0.05 lot USTEC = $0.05 per NDX point
USD_PER_QQQ = RATIO * LOT_USD_PER_PT   # ~$2.05 per $1 QQQ move
SPLIT = dt.date(2022, 11, 23)


def load(path, has_vol):
    d = json.load(gzip.open(path))
    days = {}
    for k in sorted(d, key=int):
        t = dt.datetime.fromtimestamp(int(k), NY)
        m = t.hour * 60 + t.minute
        if m < 570 or m > 955:       # bars starting 9:30 .. 15:55
            continue
        b = d[k]
        v = max(b[4], 1.0) if has_vol and len(b) > 4 else 1.0
        days.setdefault(t.date(), []).append((m, b[0], b[1], b[2], b[3], v))
    return {k: v for k, v in days.items() if len(v) >= 70}


def build(days):
    """Flatten into bar list with indicators. EMA/ATR/ADX carried across days."""
    bars = []
    e9 = e21 = e50 = None; a9, a21, a50 = 2 / 10, 2 / 22, 2 / 51
    pc = None; atr = None; ag = al = None
    pdm = mdm = trs = None; adx = None; ph = pl = None
    n = 0
    for day in sorted(days):
        cumpv = cumv = 0.0
        orh, orl = -1e9, 1e9
        for (m, o, h, l, c, v) in days[day]:
            n += 1
            e9 = c if e9 is None else e9 + a9 * (c - e9)
            e21 = c if e21 is None else e21 + a21 * (c - e21)
            e50 = c if e50 is None else e50 + a50 * (c - e50)
            tr = h - l if pc is None else max(h - l, abs(h - pc), abs(l - pc))
            atr = tr if atr is None else atr + (tr - atr) / 14
            # RSI (Wilder)
            if pc is not None:
                ch = c - pc
                g, lo = max(ch, 0), max(-ch, 0)
                ag = g if ag is None else ag + (g - ag) / 14
                al = lo if al is None else al + (lo - al) / 14
            rsi = 50 if ag is None else (100 if al == 0 else 100 - 100 / (1 + ag / al))
            # ADX (Wilder)
            if ph is not None:
                up, dn = h - ph, pl - l
                p = up if (up > dn and up > 0) else 0
                q = dn if (dn > up and dn > 0) else 0
                pdm = p if pdm is None else pdm - pdm / 14 + p
                mdm = q if mdm is None else mdm - mdm / 14 + q
                trs = tr if trs is None else trs - trs / 14 + tr
                if trs > 0:
                    pdi, mdi = 100 * pdm / trs, 100 * mdm / trs
                    dx = 0 if pdi + mdi == 0 else 100 * abs(pdi - mdi) / (pdi + mdi)
                    adx = dx if adx is None else adx + (dx - adx) / 14
            tp = (h + l + c) / 3
            cumpv += tp * v; cumv += v
            vwap = cumpv / cumv
            if m < 585:
                orh, orl = max(orh, h), min(orl, l)
            bars.append(dict(day=day, m=m, o=o, h=h, l=l, c=c, e9=e9, e21=e21, e50=e50, atr=atr,
                             rsi=rsi, adx=adx if adx is not None else 0, vwap=vwap,
                             orh=orh if m >= 585 else None, orl=orl if m >= 585 else None, warm=n > 300))
            pc, ph, pl = c, h, l
    return bars


def signals(b, prev, cfg, orb_used):
    """Return +1 / -1 / 0 for the bot's entry signal on bar b (close)."""
    c = b['c']
    if cfg.get('chop', True) and b['adx'] < 20:
        return 0
    sig = []
    kinds = cfg['kinds']
    if 'trend' in kinds:
        if b['e9'] > b['e21'] > b['e50'] and c > b['vwap'] and b['l'] <= b['e9'] < c and 50 <= b['rsi'] <= 70:
            sig.append(1)
        if b['e9'] < b['e21'] < b['e50'] and c < b['vwap'] and b['h'] >= b['e9'] > c and 30 <= b['rsi'] <= 50:
            sig.append(-1)
    if 'orb' in kinds and b['orh'] is not None:
        if c > b['orh'] and c > b['vwap'] and b['e9'] > b['e21'] and 1 not in orb_used:
            sig.append(1);
        if c < b['orl'] and c < b['vwap'] and b['e9'] < b['e21'] and -1 not in orb_used:
            sig.append(-1)
    if 'vwapx' in kinds and prev is not None and prev['day'] == b['day']:
        if prev['c'] <= prev['vwap'] and c > b['vwap'] and b['e9'] > b['e21'] > b['e50']:
            sig.append(1)
        if prev['c'] >= prev['vwap'] and c < b['vwap'] and b['e9'] < b['e21'] < b['e50']:
            sig.append(-1)
    if 'ema50x' in kinds and prev is not None:
        if prev['c'] <= prev['e50'] and c > b['e50'] and c > b['vwap'] and b['e9'] > b['e21']:
            sig.append(1)
        if prev['c'] >= prev['e50'] and c < b['e50'] and c < b['vwap'] and b['e9'] < b['e21']:
            sig.append(-1)
    s = set(sig)
    if len(s) != 1:
        return 0
    d = s.pop()
    if cfg.get('long_only') and d < 0:
        return 0
    return d


def run(bars, cfg, cost_pts=2.5, placebo=None, rng=None):
    """Returns dict day -> list of trade pnl in $ (0.05 lot)."""
    stop_k = cfg.get('stop', 1.0); trail_k = cfg.get('trail', 1.5); lock_k = cfg.get('lock', 1.0); tgt_k = cfg.get('target', 0)
    max_losses = cfg.get('max_losses', 2); max_trades = cfg.get('max_trades', 6)
    cost_usd = cost_pts * LOT_USD_PER_PT
    out = {}
    i = 0; N = len(bars)
    while i < N:
        day = bars[i]['day']; j = i
        while j < N and bars[j]['day'] == day:
            j += 1
        trades = []; pos = None; losses = 0; orb_used = set()
        pl_times = None
        if placebo is not None:
            k = placebo.get(day, 0)
            allowed = [x for x in range(i, j) if 585 <= bars[x]['m'] <= 925]
            pl_times = set(rng.sample(allowed, min(k, len(allowed)))) if k else set()
        for x in range(i, j):
            b = bars[x]
            if pos is not None:
                d, ent, stop, best, atr0 = pos
                exitp = None
                if d > 0 and b['l'] <= stop:
                    exitp = min(b['o'], stop)
                elif d < 0 and b['h'] >= stop:
                    exitp = max(b['o'], stop)
                elif tgt_k and d * ((b['h'] if d > 0 else b['l']) - ent) >= tgt_k * atr0:
                    exitp = ent + d * tgt_k * atr0
                    if d * (b['o'] - ent) > tgt_k * atr0:
                        exitp = b['o']
                elif b['m'] >= 950:
                    exitp = b['c']
                if exitp is not None:
                    pnl = d * (exitp - ent) * USD_PER_QQQ - cost_usd
                    trades.append(pnl); pos = None
                    if pnl < 0:
                        losses += 1
                    continue
                best = max(best, b['c']) if d > 0 else min(best, b['c'])
                if d * (best - ent) >= lock_k * atr0:
                    stop = max(stop, ent) if d > 0 else min(stop, ent)
                if trail_k:
                    t = best - d * trail_k * atr0
                    stop = max(stop, t) if d > 0 else min(stop, t)
                pos = (d, ent, stop, best, atr0)
                continue
            if not b['warm'] or b['m'] < 585 or b['m'] > 925:
                continue
            if losses >= max_losses or len(trades) >= max_trades:
                continue
            if placebo is not None:
                if x not in pl_times:
                    continue
                d = rng.choice((1, -1))
            else:
                d = signals(b, bars[x - 1] if x > 0 else None, cfg, orb_used)
                if d == 0:
                    continue
                if 'orb' in cfg['kinds'] and b['orh'] is not None and ((d > 0 and b['c'] > b['orh']) or (d < 0 and b['c'] < b['orl'])):
                    orb_used.add(d)
            atr0 = b['atr']
            pos = (d, b['c'], b['c'] - d * stop_k * atr0, b['c'], atr0)
        out[day] = trades
        i = j
    return out


def stats(res, lo=None, hi=None):
    days = [d for d in sorted(res) if (lo is None or d >= lo) and (hi is None or d < hi)]
    daily = [sum(res[d]) for d in days]
    tr = [p for d in days for p in res[d]]
    if not tr:
        return dict(n=0)
    eq = pk = dd = 0
    for p in daily:
        eq += p; pk = max(pk, eq); dd = min(dd, eq - pk)
    sd = st.pstdev(daily)
    t = (st.mean(daily) / sd * math.sqrt(len(daily))) if sd > 0 else 0
    wins = sum(1 for p in tr if p > 0)
    return dict(n=len(tr), net=round(sum(tr), 1), per_tr=round(sum(tr) / len(tr), 3), win=round(wins / len(tr), 3),
                t=round(t, 2), dd=round(dd, 1), worst_day=round(min(daily), 1),
                yrs=round(len(days) / 252, 1), per_yr=round(sum(tr) / (len(days) / 252), 1))


def yearly(res):
    y = {}
    for d, tr in res.items():
        y[d.year] = y.get(d.year, 0) + sum(tr)
    return {k: round(v, 1) for k, v in sorted(y.items())}


BOTS = {
    'TREND': dict(kinds={'trend', 'orb'}),
    'OG': dict(kinds={'vwapx', 'ema50x', 'orb'}),
}

if __name__ == '__main__':
    dd = sys.argv[1]
    A = build({k: v for k, v in load(dd + '/qqq_idx.json.gz', False).items() if k < SPLIT})
    B = build(load(dd + '/qqq_long.json.gz', True))
    Bt = build({k: [(m, o, h, l, c, 1.0) for (m, o, h, l, c, v) in vv] for k, vv in load(dd + '/qqq_long.json.gz', True).items()})
    report = {}
    variants = {}
    for name, cfg in BOTS.items():
        variants[name] = cfg
        variants[name + ' long-only'] = dict(cfg, long_only=True)
        variants[name + ' no-chop'] = dict(cfg, chop=False)
        variants[name + ' trail1.0'] = dict(cfg, trail=1.0)
        variants[name + ' trail2.5'] = dict(cfg, trail=2.5)
        variants[name + ' stop0.5'] = dict(cfg, stop=0.5)
        variants[name + ' quick-target1.0'] = dict(cfg, target=1.0)
        variants[name + ' target2.0'] = dict(cfg, target=2.0)
        variants[name + ' no-loss-brake'] = dict(cfg, max_losses=99)
    for k in ['trend', 'orb', 'vwapx', 'ema50x']:
        variants['only ' + k] = dict(kinds={k})
    for vn, cfg in variants.items():
        rB = run(B, cfg); rA = run(A, cfg)
        rec = dict(B=stats(rB), A=stats(rA), B_5pt=stats(run(B, cfg, 5.0)), B_twap=stats(run(Bt, cfg)),
                   B_years=yearly(rB), A_years=yearly(rA))
        report[vn] = rec
        print(vn, json.dumps(rec), flush=True)
    # placebo for the two frozen bots
    for name, cfg in BOTS.items():
        real = run(B, cfg)
        k = {d: len(v) for d, v in real.items()}
        rng = random.Random(7)
        nets = [stats(run(B, cfg, placebo=k, rng=rng))['net'] for _ in range(200)]
        rn = stats(real)['net']
        pct = sum(1 for x in nets if x < rn) / len(nets)
        report[name]['placebo'] = dict(real=rn, beats=pct, median=sorted(nets)[100], p95=sorted(nets)[189])
        print(name, 'placebo', report[name]['placebo'], flush=True)
    json.dump(report, open(dd + '/qqq_bots_results.json', 'w'), indent=1, default=str)
