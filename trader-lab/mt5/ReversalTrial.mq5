//+------------------------------------------------------------------+
//| ReversalTrial.mq5                                                  |
//| trader-lab, alkaabiz-crypto/day-trader-skill                       |
//|                                                                    |
//| The pre-registered 15:30 New York reversal (trader-lab/paper/      |
//| PLAN.md), trading automatically on MetaTrader 5:                    |
//|   at 15:30 New York, for each index CFD whose move since the        |
//|   previous 16:00 New York price is at least MinMovePct, trade the   |
//|   other way; stop StopPct from the fill; everything flat by 15:55.  |
//| Hard limits: RiskPerTradeUSD a trade (notional capped at            |
//| MaxNotionalUSD, no leverage beyond 1:1), MaxTradesPerDay,           |
//| MaxDailyLossUSD, no entries after LastEntryNY.                      |
//| DryRun=true (the default) only prints what it would do.             |
//| Use on a DEMO account. Research, not financial advice.              |
//+------------------------------------------------------------------+
#property copyright "trader-lab"
#property version   "1.00"

#include <Trade/Trade.mqh>

input string Symbols          = "US500,USTEC,US30";  // broker symbol names (Exness may add a suffix, e.g. US500m)
input double MinMovePct       = 1.0;    // trade only moves of at least this % since the previous 16:00 New York
input double StopPct          = 0.5;    // stop distance from the fill, %
input double RiskPerTradeUSD  = 10.0;   // max loss a trade at the stop
input double MaxNotionalUSD   = 1000.0; // position value cap (1:1 for a ~$1,000 account)
input int    MaxTradesPerDay  = 3;
input double MaxDailyLossUSD  = 30.0;
input string EntryNY          = "15:30";
input string LastEntryNY      = "15:35";
input string FlatNY           = "15:55";
input bool   DryRun           = true;   // true: log only, no orders
input long   Magic            = 153015; // only positions with this number are managed

CTrade trade;
int    lastEntryDay = -1;   // New York day-of-year when entries were decided
int    lastFlatDay  = -1;

//--- New York time from GMT (US daylight time: 2nd Sunday of March 07:00 UTC to 1st Sunday of November 06:00 UTC)
datetime NthSunday(int year, int month, int n)
{
   MqlDateTime t; ZeroMemory(t);
   t.year = year; t.mon = month; t.day = 1;
   datetime d = StructToTime(t);
   MqlDateTime s; TimeToStruct(d, s);
   int add = (7 - s.day_of_week) % 7;
   return d + (add + 7 * (n - 1)) * 86400;
}

int NyOffsetHours(datetime gmt)
{
   MqlDateTime s; TimeToStruct(gmt, s);
   datetime start = NthSunday(s.year, 3, 2) + 7 * 3600;
   datetime end   = NthSunday(s.year, 11, 1) + 6 * 3600;
   return (gmt >= start && gmt < end) ? -4 : -5;
}

datetime NyNow() { datetime g = TimeGMT(); return g + NyOffsetHours(g) * 3600; }

int Minutes(string hhmm)
{
   string p[]; StringSplit(hhmm, ':', p);
   return (int)StringToInteger(p[0]) * 60 + (int)StringToInteger(p[1]);
}

//--- server time of a New York time (server clock = GMT + serverOffset)
datetime NyToServer(datetime ny)
{
   datetime gmt = ny - NyOffsetHours(ny + 5 * 3600) * 3600;
   long serverOffset = (long)(TimeTradeServer() - TimeGMT());
   return gmt + (datetime)serverOffset;
}

//--- the close of the M5 bar that ends at 16:00 New York on the previous weekday
double PrevNyClose(string sym)
{
   datetime ny = NyNow();
   MqlDateTime s; TimeToStruct(ny, s);
   datetime day = ny - (s.hour * 3600 + s.min * 60 + s.sec);
   for(int back = 1; back <= 5; back++)
   {
      datetime d = day - back * 86400;
      MqlDateTime ds; TimeToStruct(d, ds);
      if(ds.day_of_week == 0 || ds.day_of_week == 6) continue;
      datetime barOpenServer = NyToServer(d + 15 * 3600 + 55 * 60);  // the 15:55-16:00 bar
      int shift = iBarShift(sym, PERIOD_M5, barOpenServer, true);
      if(shift >= 0) return iClose(sym, PERIOD_M5, shift);
   }
   return 0.0;
}

double TodayClosedPnl()
{
   datetime ny = NyNow();
   MqlDateTime s; TimeToStruct(ny, s);
   datetime startNy = ny - (s.hour * 3600 + s.min * 60 + s.sec);
   if(!HistorySelect(NyToServer(startNy), TimeTradeServer())) return 0.0;
   double sum = 0.0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong t = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(t, DEAL_MAGIC) != Magic) continue;
      sum += HistoryDealGetDouble(t, DEAL_PROFIT) + HistoryDealGetDouble(t, DEAL_SWAP) + HistoryDealGetDouble(t, DEAL_COMMISSION);
   }
   return sum;
}

int TodayEntries()
{
   datetime ny = NyNow();
   MqlDateTime s; TimeToStruct(ny, s);
   datetime startNy = ny - (s.hour * 3600 + s.min * 60 + s.sec);
   int n = 0;
   if(HistorySelect(NyToServer(startNy), TimeTradeServer()))
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
      {
         ulong t = HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(t, DEAL_MAGIC) == Magic && HistoryDealGetInteger(t, DEAL_ENTRY) == DEAL_ENTRY_IN) n++;
      }
   return n;
}

double Lots(string sym, double price)
{
   double notional = MathMin(MaxNotionalUSD, RiskPerTradeUSD / (StopPct / 100.0));
   double contract = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(contract <= 0 || price <= 0 || step <= 0) return 0.0;
   double lots = MathFloor(notional / (price * contract) / step) * step;   // round DOWN: never above the cap
   if(lots < vmin) return 0.0;                                             // too small to trade within the cap
   return MathMin(lots, vmax);
}

void CloseAll(string why)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(!PositionSelectByTicket(t) || PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      if(DryRun) { PrintFormat("[DRY RUN] would close %s (%s)", sym, why); continue; }
      if(!trade.PositionClose(t)) PrintFormat("close %s failed: %d", sym, GetLastError());
      else PrintFormat("closed %s (%s)", sym, why);
   }
}

void DecideEntries()
{
   string list[]; int n = StringSplit(Symbols, ',', list);
   string sym[]; double move[]; double px[];
   ArrayResize(sym, 0); ArrayResize(move, 0); ArrayResize(px, 0);
   for(int i = 0; i < n; i++)
   {
      string s = list[i]; StringTrimLeft(s); StringTrimRight(s);
      if(!SymbolSelect(s, true)) { PrintFormat("symbol %s not found: check the name in Market Watch", s); continue; }
      double pc = PrevNyClose(s);
      double bid = SymbolInfoDouble(s, SYMBOL_BID), ask = SymbolInfoDouble(s, SYMBOL_ASK);
      if(pc <= 0 || bid <= 0 || ask <= 0) { PrintFormat("%s: no previous 16:00 price or quote", s); continue; }
      double mid = (bid + ask) / 2.0;
      double m = (mid / pc - 1.0) * 100.0;
      PrintFormat("%s: previous 16:00 New York %.2f, now %.2f, move %+.2f%%", s, pc, mid, m);
      if(MathAbs(m) < MinMovePct) continue;
      int k = ArraySize(sym);
      ArrayResize(sym, k + 1); ArrayResize(move, k + 1); ArrayResize(px, k + 1);
      sym[k] = s; move[k] = m; px[k] = mid;
   }
   // largest moves first
   for(int a = 0; a < ArraySize(sym); a++)
      for(int b = a + 1; b < ArraySize(sym); b++)
         if(MathAbs(move[b]) > MathAbs(move[a]))
         {
            string ts = sym[a]; sym[a] = sym[b]; sym[b] = ts;
            double tm = move[a]; move[a] = move[b]; move[b] = tm;
            double tp = px[a]; px[a] = px[b]; px[b] = tp;
         }
   int allowed = (int)MathMin(MaxTradesPerDay - TodayEntries(), MathFloor(MaxDailyLossUSD / RiskPerTradeUSD));
   if(TodayClosedPnl() <= -MaxDailyLossUSD) { Print("daily loss limit reached: no entries"); return; }
   for(int j = 0; j < ArraySize(sym) && j < allowed; j++)
   {
      bool buy = move[j] < 0;                  // fade the move
      double price = buy ? SymbolInfoDouble(sym[j], SYMBOL_ASK) : SymbolInfoDouble(sym[j], SYMBOL_BID);
      double lots = Lots(sym[j], price);
      if(lots <= 0) { PrintFormat("%s: minimum volume is above the $%.0f cap: skipped", sym[j], MaxNotionalUSD); continue; }
      int digits = (int)SymbolInfoInteger(sym[j], SYMBOL_DIGITS);
      double sl = NormalizeDouble(buy ? price * (1 - StopPct / 100.0) : price * (1 + StopPct / 100.0), digits);
      if(DryRun)
      {
         PrintFormat("[DRY RUN] would %s %.2f lots %s at %.2f, stop %.2f (moved %+.2f%%)", buy ? "BUY" : "SELL",
                     lots, sym[j], price, sl, move[j]);
         continue;
      }
      bool ok = buy ? trade.Buy(lots, sym[j], 0.0, sl, 0.0, "trader-lab reversal")
                    : trade.Sell(lots, sym[j], 0.0, sl, 0.0, "trader-lab reversal");
      PrintFormat("%s %.2f lots %s, stop %.2f: %s", buy ? "BUY" : "SELL", lots, sym[j], sl,
                  ok ? "sent" : "FAILED " + IntegerToString(trade.ResultRetcode()));
   }
}

int OnInit()
{
   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints(50);
   EventSetTimer(10);
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
      Print("WARNING: this is NOT a demo account. The trial plan says demo only.");
   PrintFormat("ReversalTrial ready. DryRun=%s, symbols %s, New York time now %s", DryRun ? "true" : "false",
               Symbols, TimeToString(NyNow(), TIME_DATE | TIME_MINUTES));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

void OnTimer()
{
   datetime ny = NyNow();
   MqlDateTime s; TimeToStruct(ny, s);
   if(s.day_of_week == 0 || s.day_of_week == 6) return;
   int now = s.hour * 60 + s.min;
   if(now >= Minutes(FlatNY) && lastFlatDay != s.day_of_year)
   {
      CloseAll("flat by " + FlatNY + " New York");
      lastFlatDay = s.day_of_year;
   }
   if(now >= Minutes(EntryNY) && now < Minutes(LastEntryNY) && lastEntryDay != s.day_of_year)
   {
      lastEntryDay = s.day_of_year;
      DecideEntries();
   }
}
//+------------------------------------------------------------------+
