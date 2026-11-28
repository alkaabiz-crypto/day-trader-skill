from intra import ema, rsi
def first(cond_iter):
    for x in cond_iter:
        if x: return x
    return None
def make(kind):
    if kind == 'idx': S0, E0, E1, FLAT, T1000, T1030, T930 = 570, 575, 900, 955, 600, 630, 570
    else: S0, E0, E1, FLAT, T1000, T1030, T930 = 480, 480, 1020, 1255, 540, 600, 480
    def sess(bars): return [b for b in bars if b[0] >= S0]
    def idx_of(B, tm): return next((k for k, b in enumerate(B) if b[0] >= tm), None)
    def setups(B, ctx):
        """B: session bars; ctx: adr, pdh, pdl, pc, asia_h, asia_l, pivot. Return {name: (bar index of signal, side)}"""
        out = {}; adr = ctx['adr']; o0 = B[0][1]
        def scan(f, start=E0):
            for k, b in enumerate(B):
                if b[0] < start: continue
                if b[0] > E1: return None
                s = f(k, b)
                if s: return (k, s)
            return None
        for name, mins in (('orb15', 15), ('orb30', 30)):
            r = [b for b in B if b[0] < T930+mins]
            if r:
                hi = max(b[2] for b in r); lo = min(b[3] for b in r)
                out[name] = scan(lambda k, b: 1 if b[4] > hi else (-1 if b[4] < lo else 0), T930+mins)
        out['dip_open'] = scan(lambda k, b: 1 if b[4] < o0 - .5*adr else 0)
        out['rally_open'] = scan(lambda k, b: -1 if b[4] > o0 + .5*adr else 0)
        # VWAP (equal weights; volume not stored for fx): typical-price running mean
        vw = []; s = 0
        for k, b in enumerate(B): s += (b[2]+b[3]+b[4])/3; vw.append(s/(k+1))
        k30 = idx_of(B, T1030)
        if k30 is not None:
            d = 1 if B[k30][4] > vw[k30] else -1
            out['vwap_pb'] = scan(lambda k, b: d if k > k30 and b[3] <= vw[k] <= b[2] else 0, T1030)
        C = [b[4] for b in B]
        def bb(k, b):
            if k < 20: return 0
            w = C[k-19:k+1]; m = sum(w)/20; sd = (sum((x-m)**2 for x in w)/20)**.5
            return 1 if b[4] < m-2*sd else (-1 if b[4] > m+2*sd else 0)
        out['bb_rev'] = scan(bb)
        R = rsi(C)
        out['rsi_rev'] = scan(lambda k, b: 0 if R[k] is None else (1 if R[k] < 30 else (-1 if R[k] > 70 else 0)))
        out['pdhl_break'] = scan(lambda k, b: 1 if b[4] > ctx['pdh'] else (-1 if b[4] < ctx['pdl'] else 0))
        out['pdhl_fade'] = scan(lambda k, b: -1 if b[2] >= ctx['pdh'] > b[3] else (1 if b[3] <= ctx['pdl'] < b[2] else 0))
        st = {'lo': False, 'hi': False}
        def sweep(k, b):
            if b[3] < ctx['pdl']: st['lo'] = True
            if b[2] > ctx['pdh']: st['hi'] = True
            if st['lo'] and b[4] > ctx['pdl']: return 1
            if st['hi'] and b[4] < ctx['pdh']: return -1
            return 0
        out['sweep'] = scan(sweep)
        if kind == 'idx':
            g = o0 - ctx['pc']
            out['gap_fill'] = (0, -1 if g > 0 else 1) if abs(g) >= .2*adr else None
        e9, e21 = ema(C, 9), ema(C, 21)
        out['ema_cross'] = scan(lambda k, b: 0 if k == 0 else (1 if e9[k] > e21[k] and e9[k-1] <= e21[k-1] else (-1 if e9[k] < e21[k] and e9[k-1] >= e21[k-1] else 0)), T1000)
        P = ctx['pivot']; S1, R1 = 2*P-ctx['pdh'], 2*P-ctx['pdl']
        out['pivot_bounce'] = scan(lambda k, b: 1 if b[3] <= S1 < b[2] else (-1 if b[2] >= R1 > b[3] else 0))
        k10 = idx_of(B, T1000)
        if k10:
            mv = B[k10-1][4] - o0
            out['first30_mom'] = (k10-1, 1 if mv > 0 else -1) if abs(mv) > .3*adr else None
            out['ny_reversal'] = (k10-1, -1 if mv > 0 else 1) if abs(mv) > .4*adr else None
        if len(B) > 2 and B[1][2] < B[0][2] and B[1][3] > B[0][3]:
            out['inside_break'] = scan(lambda k, b: 0 if k < 2 else (1 if b[4] > B[0][2] else (-1 if b[4] < B[0][3] else 0)))
        e50 = ema(C, 50)
        out['three_pb'] = scan(lambda k, b: 0 if k < 50 else (1 if C[k] < C[k-1] < C[k-2] < C[k-3] and C[k] > e50[k] else (-1 if C[k] > C[k-1] > C[k-2] > C[k-3] and C[k] < e50[k] else 0)))
        if kind == 'fx' and ctx.get('asia_h'):
            out['london_break'] = scan(lambda k, b: 1 if b[4] > ctx['asia_h'] else (-1 if b[4] < ctx['asia_l'] else 0))
        return {k: v for k, v in out.items() if v}
    return setups, sess, FLAT
