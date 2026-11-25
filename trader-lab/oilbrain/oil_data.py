#!/usr/bin/env python3
"""Oil brain data: the fundamentals the lab never had, each dated by when it became public.

    python3 oilbrain/oil_data.py fetch      # EIA weekly stocks + CFTC positioning into data/oilbrain/
    python3 oilbrain/oil_data.py show       # row counts and date ranges

Sources (free, no key):
  * EIA weekly stocks (www.eia.gov LeafHandler pages): US crude excluding the SPR (WCESTUS1, 1982+),
    Cushing, Oklahoma crude (W_EPC0_SAX_YCUOK_MBBL, 2004+) and US total gasoline (WGTSTUS1, 1990+).
    Each value is stocks at the end of a week (a Friday); the EIA publishes it the next Wednesday at
    10:30 New York, Thursday in holiday weeks. The lab counts it as known only from the close of the
    Thursday after the week ends (week end + 6 days), so no holiday shift can leak it early.
  * CFTC Commitments of Traders, disaggregated, WTI crude on NYMEX (code 067651, 2006+), from
    publicreporting.cftc.gov. Positions are as of a Tuesday and published that Friday at 15:30
    New York, Monday after a holiday. The lab counts them as known from the close of the Monday after
    (report date + 6 days).
Prices (USO, BNO, UUP, XLE, SPY, CL=F) come from the lab's daily store (`daily.py`), and the futures
curve from `oil.load_curve()` (EIA contracts 1 and 2, 1983 to 2024-04).
Research, not financial advice.
"""

import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, LAB)
import daily  # noqa: E402

STORE = os.path.join(LAB, "data", "oilbrain")
EIA_WEEKLY = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=%s&f=W"
SERIES = {"crude": "WCESTUS1", "cushing": "W_EPC0_SAX_YCUOK_MBBL", "gasoline": "WGTSTUS1"}
COT_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
COT_CODE = "067651"
EIA_LAG_DAYS = 6
COT_LAG_DAYS = 6


def http(url):
    req = urllib.request.Request(url, headers={"User-Agent": daily.UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def parse_weekly(html):
    """EIA weekly table -> {week-end date: value}. Each row is a month ('1982-Oct') followed by up to
    five (date 'MM/DD', value) cell pairs."""
    out = {}
    for row in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        m = re.search(r"class='B6'>[^0-9]*(\d{4})-(\w{3})", row)
        if not m:
            continue
        year = int(m.group(1))
        pairs = re.findall(r"<td class='B5'>\s*(\d\d)/(\d\d)[^<]*</td>\s*<td class='B3'>([^<]*)</td>", row)
        for mm, dd, v in pairs:
            v = v.replace("&nbsp;", "").replace(",", "").strip()
            if not v:
                continue
            try:
                out[datetime.date(year, int(mm), int(dd)).isoformat()] = float(v)
            except ValueError:
                pass
    return out


def parse_cot(rows):
    """CFTC rows -> {report date: {"mm_net": managed money long - short, "oi": open interest,
    "pm_net": producer/merchant long - short}}."""
    out = {}
    for r in rows:
        d = (r.get("report_date_as_yyyy_mm_dd") or "")[:10]
        try:
            out[d] = {"mm_net": float(r["m_money_positions_long_all"]) - float(r["m_money_positions_short_all"]),
                      "pm_net": float(r["prod_merc_positions_long"]) - float(r["prod_merc_positions_short"]),
                      "oi": float(r["open_interest_all"])}
        except (KeyError, ValueError):
            continue
    return out


def available(date_iso, lag_days):
    """The first calendar date on whose close a value dated date_iso may be used."""
    return (datetime.date.fromisoformat(date_iso) + datetime.timedelta(days=lag_days)).isoformat()


def fetch():
    os.makedirs(STORE, exist_ok=True)
    for name, code in SERIES.items():
        data = parse_weekly(http(EIA_WEEKLY % code))
        with open(os.path.join(STORE, name + ".json"), "w") as fh:
            json.dump(data, fh, sort_keys=True)
        print("  EIA %-9s %5d weeks  %s to %s" % (name, len(data), min(data), max(data)), flush=True)
    q = urllib.parse.urlencode({"cftc_contract_market_code": COT_CODE, "$limit": 5000,
                                "$order": "report_date_as_yyyy_mm_dd"})
    cot = parse_cot(json.loads(http(COT_URL + "?" + q)))
    with open(os.path.join(STORE, "cot.json"), "w") as fh:
        json.dump(cot, fh, sort_keys=True)
    print("  CFTC COT     %5d weeks  %s to %s" % (len(cot), min(cot), max(cot)), flush=True)


def load(name):
    path = os.path.join(STORE, name + ".json")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


def show():
    for name in list(SERIES) + ["cot"]:
        d = load(name)
        print("  %-9s %5d  %s to %s" % (name, len(d), min(d) if d else "-", max(d) if d else "-"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch":
        fetch()
    elif cmd == "show":
        show()
    else:
        print(__doc__)
