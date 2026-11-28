# Famous daily strategies on Exness costs (2026-11-26)

Independent test, run offline from day-trader-skill's stored prices. Rules and pass bar were written down before each batch ran (PREREG section below).
Not financial advice. Costs are cautious estimates from third-party pages, because Exness's own pages didn't load; check MT5 Specification for real spreads and swaps.

**Result: 0 of 244 rule x market x account combinations pass.**

Columns: IS t = in-sample t-stat; judged t / Sharpe = 2021-2026 for US500/USTEC, Jul 2024-Nov 2026 for XAUUSD/EURUSD; 2x t = judged t at double costs; placebo = share of 200 time-shifted copies it beats; $1,000 from 2024-01-02 to 2026-11-25 and the worst drop on the way.

| market | rule | account | IS t | judged t | judged Sharpe | 2x t | placebo | $1,000 since 2024 | worst drop | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | hull | standard | 0.75 | 0.90 | 0.57 | 0.52 | 1.00 | $1092 | -9.9% | FAIL |
| EURUSD | ema921 | standard | 0.44 | 0.80 | 0.51 | 0.42 | 0.96 | $1067 | -6.6% | FAIL |
| EURUSD | ichimoku | standard | -2.21 | 0.69 | 0.44 | 0.32 | 0.92 | $977 | -11.9% | FAIL |
| EURUSD | adx | standard | -1.34 | 0.54 | 0.35 | 0.26 | 0.91 | $1013 | -8.2% | FAIL |
| EURUSD | cumrsi2 | standard | -0.08 | 0.46 | 0.29 | 0.14 | 0.75 | $1026 | -2.7% | FAIL |
| EURUSD | supertrend | standard | -0.74 | 0.39 | 0.25 | 0.00 | 0.92 | $984 | -13.9% | FAIL |
| EURUSD | willr | standard | -0.08 | 0.36 | 0.23 | -0.09 | 0.83 | $1021 | -7.2% | FAIL |
| EURUSD | sma50 | standard | -1.12 | 0.25 | 0.16 | -0.15 | 0.86 | $959 | -13.4% | FAIL |
| EURUSD | tsmom | standard | 1.07 | 0.16 | 0.10 | -0.25 | 0.78 | $1027 | -7.8% | FAIL |
| EURUSD | psar | standard | -0.24 | 0.16 | 0.10 | -0.25 | 0.74 | $999 | -9.6% | FAIL |
| EURUSD | halloween | standard | 1.22 | 0.16 | 0.10 | -0.16 | 0.69 | $971 | -10.0% | FAIL |
| EURUSD | ibs | standard | 0.13 | 0.14 | 0.09 | -0.39 | 0.78 | $996 | -6.8% | FAIL |
| EURUSD | rsi2 | standard | -0.34 | 0.08 | 0.05 | -0.21 | 0.62 | $1006 | -3.2% | FAIL |
| EURUSD | sma200 | standard | -2.33 | 0.04 | 0.03 | -0.36 | 0.67 | $907 | -15.0% | FAIL |
| EURUSD | turtle20 | standard | -0.02 | 0.02 | 0.01 | -0.34 | 0.74 | $968 | -11.6% | FAIL |
| EURUSD | turtle55 | standard | -2.35 | -0.03 | -0.02 | -0.31 | 0.76 | $943 | -13.0% | FAIL |
| EURUSD | double7 | standard | -0.51 | -0.03 | -0.02 | -0.39 | 0.59 | $987 | -4.4% | FAIL |
| EURUSD | stoch | standard | -0.79 | -0.06 | -0.04 | -0.50 | 0.60 | $975 | -8.2% | FAIL |
| EURUSD | insideday | standard | 1.17 | -0.26 | -0.16 | -0.67 | 0.45 | $981 | -5.2% | FAIL |
| EURUSD | buyhold | standard | 0.49 | -0.31 | -0.20 | -0.87 | 1.00 | $923 | -11.3% | FAIL |
| EURUSD | heikin | standard | -2.44 | -0.32 | -0.20 | -0.85 | 0.62 | $884 | -16.0% | FAIL |
| EURUSD | keltner | standard | -1.86 | -0.47 | -0.30 | -0.67 | 0.51 | $939 | -9.4% | FAIL |
| EURUSD | rsi14 | standard | 0.44 | -0.50 | -0.32 | -0.83 | 0.31 | $980 | -13.1% | FAIL |
| EURUSD | macd | standard | 0.25 | -0.58 | -0.37 | -1.00 | 0.47 | $910 | -15.8% | FAIL |
| EURUSD | nr7 | standard | 0.23 | -0.59 | -0.38 | -0.95 | 0.35 | $953 | -5.7% | FAIL |
| EURUSD | bollinger | standard | 0.03 | -0.94 | -0.60 | -1.33 | 0.07 | $963 | -7.0% | FAIL |
| EURUSD | golden | standard | -1.63 | -0.98 | -0.62 | -1.33 | 0.33 | $890 | -21.0% | FAIL |
| EURUSD | cci | standard | -0.08 | -1.03 | -0.65 | -1.44 | 0.08 | $924 | -8.5% | FAIL |
| EURUSD | down3 | standard | 0.46 | -1.15 | -0.73 | -1.55 | 0.17 | $959 | -5.2% | FAIL |
| EURUSD | hull | swapfree | 1.01 | 1.25 | 0.79 | 1.21 | 0.98 | $1141 | -8.6% | FAIL |
| EURUSD | ema921 | swapfree | 0.73 | 1.15 | 0.73 | 1.13 | 0.97 | $1117 | -6.4% | FAIL |
| EURUSD | ichimoku | swapfree | -1.95 | 1.01 | 0.64 | 0.97 | 0.91 | $1015 | -10.5% | FAIL |
| EURUSD | adx | swapfree | -1.12 | 0.80 | 0.51 | 0.76 | 0.90 | $1036 | -7.6% | FAIL |
| EURUSD | willr | swapfree | 0.28 | 0.79 | 0.50 | 0.76 | 0.76 | $1063 | -6.0% | FAIL |
| EURUSD | supertrend | swapfree | -0.45 | 0.75 | 0.48 | 0.73 | 0.90 | $1030 | -12.1% | FAIL |
| EURUSD | cumrsi2 | swapfree | 0.12 | 0.70 | 0.45 | 0.63 | 0.71 | $1037 | -2.6% | FAIL |
| EURUSD | sma50 | swapfree | -0.84 | 0.60 | 0.38 | 0.55 | 0.89 | $1003 | -11.9% | FAIL |
| EURUSD | tsmom | swapfree | 1.33 | 0.55 | 0.35 | 0.54 | 0.69 | $1081 | -7.2% | FAIL |
| EURUSD | ibs | swapfree | 0.49 | 0.52 | 0.33 | 0.38 | 0.72 | $1031 | -5.2% | FAIL |
| EURUSD | psar | swapfree | 0.03 | 0.50 | 0.32 | 0.42 | 0.72 | $1043 | -8.2% | FAIL |
| EURUSD | halloween | swapfree | 1.54 | 0.48 | 0.31 | 0.48 | 0.62 | $1006 | -8.7% | FAIL |
| EURUSD | sma200 | swapfree | -2.10 | 0.42 | 0.26 | 0.39 | 0.69 | $951 | -13.5% | FAIL |
| EURUSD | stoch | swapfree | -0.42 | 0.36 | 0.23 | 0.34 | 0.57 | $1017 | -7.0% | FAIL |
| EURUSD | turtle20 | swapfree | 0.25 | 0.34 | 0.22 | 0.31 | 0.77 | $1003 | -10.2% | FAIL |
| EURUSD | rsi2 | swapfree | -0.12 | 0.30 | 0.19 | 0.22 | 0.63 | $1014 | -2.9% | FAIL |
| EURUSD | double7 | swapfree | -0.22 | 0.26 | 0.17 | 0.21 | 0.57 | $1009 | -3.4% | FAIL |
| EURUSD | buyhold | swapfree | 0.94 | 0.25 | 0.16 | 0.25 | 1.00 | $993 | -9.4% | FAIL |
| EURUSD | turtle55 | swapfree | -2.13 | 0.23 | 0.14 | 0.21 | 0.79 | $966 | -11.9% | FAIL |
| EURUSD | insideday | swapfree | 1.43 | 0.06 | 0.04 | -0.04 | 0.56 | $1001 | -4.8% | FAIL |
| EURUSD | heikin | swapfree | -2.16 | 0.01 | 0.00 | -0.20 | 0.62 | $923 | -12.7% | FAIL |
| EURUSD | rsi14 | swapfree | 0.62 | -0.18 | -0.11 | -0.18 | 0.34 | $1022 | -12.0% | FAIL |
| EURUSD | macd | swapfree | 0.51 | -0.24 | -0.15 | -0.32 | 0.40 | $950 | -13.4% | FAIL |
| EURUSD | keltner | swapfree | -1.63 | -0.30 | -0.19 | -0.33 | 0.50 | $951 | -8.8% | FAIL |
| EURUSD | nr7 | swapfree | 0.47 | -0.32 | -0.20 | -0.40 | 0.31 | $970 | -5.5% | FAIL |
| EURUSD | bollinger | swapfree | 0.31 | -0.58 | -0.37 | -0.62 | 0.10 | $987 | -6.1% | FAIL |
| EURUSD | golden | swapfree | -1.41 | -0.63 | -0.40 | -0.64 | 0.37 | $931 | -19.6% | FAIL |
| EURUSD | cci | swapfree | 0.25 | -0.65 | -0.41 | -0.69 | 0.06 | $952 | -7.2% | FAIL |
| EURUSD | down3 | swapfree | 0.63 | -0.91 | -0.58 | -1.07 | 0.15 | $970 | -4.3% | FAIL |
| US500 | down3 | standard | -1.19 | 1.89 | 0.78 | 1.59 | 0.99 | $1137 | -5.5% | FAIL |
| US500 | cumrsi2 | standard | 0.49 | 1.63 | 0.67 | 1.20 | 0.94 | $1144 | -7.2% | FAIL |
| US500 | rsi2 | standard | 0.35 | 1.48 | 0.61 | 1.05 | 0.90 | $1181 | -4.2% | FAIL |
| US500 | hull | standard | 0.67 | 1.34 | 0.55 | 0.30 | 0.70 | $1241 | -7.0% | FAIL |
| US500 | double7 | standard | 0.23 | 1.27 | 0.52 | 0.66 | 0.78 | $1168 | -9.6% | FAIL |
| US500 | bollinger | standard | 0.71 | 1.24 | 0.51 | 0.96 | 1.00 | $1102 | -10.3% | FAIL |
| US500 | sma200 | standard | 0.69 | 1.09 | 0.45 | -0.03 | 0.47 | $1204 | -11.8% | FAIL |
| US500 | ema921 | standard | 0.79 | 1.09 | 0.45 | 0.03 | 0.55 | $1218 | -9.1% | FAIL |
| US500 | golden | standard | 0.47 | 1.07 | 0.44 | 0.12 | 0.67 | $1121 | -20.8% | FAIL |
| US500 | rsi14 | standard | 0.81 | 1.06 | 0.44 | 0.70 | 0.96 | $1135 | -15.3% | FAIL |
| US500 | buyhold | standard | 1.21 | 1.03 | 0.43 | 0.08 | 1.00 | $1298 | -20.8% | FAIL |
| US500 | turtle20 | standard | 1.69 | 1.02 | 0.42 | 0.02 | 0.51 | $1119 | -8.8% | FAIL |
| US500 | ibs | standard | 1.00 | 1.00 | 0.41 | 0.38 | 0.77 | $1102 | -13.4% | FAIL |
| US500 | tsmom | standard | 0.54 | 0.95 | 0.39 | -0.04 | 0.41 | $1193 | -22.8% | FAIL |
| US500 | cci | standard | 0.80 | 0.95 | 0.39 | 0.60 | 0.93 | $1176 | -11.0% | FAIL |
| US500 | supertrend | standard | 0.96 | 0.87 | 0.36 | -0.18 | 0.38 | $1267 | -7.3% | FAIL |
| US500 | adx | standard | 0.04 | 0.69 | 0.28 | -0.06 | 0.49 | $1049 | -7.6% | FAIL |
| US500 | turnaround | standard | 2.60 | 0.59 | 0.25 | 0.23 | 0.65 | $976 | -4.8% | FAIL |
| US500 | sma50 | standard | 0.49 | 0.58 | 0.24 | -0.50 | 0.19 | $1110 | -11.8% | FAIL |
| US500 | halloween | standard | 0.65 | 0.46 | 0.19 | -0.14 | 0.30 | $993 | -20.8% | FAIL |
| US500 | willr | standard | 0.75 | 0.45 | 0.19 | 0.02 | 0.47 | $1122 | -18.7% | FAIL |
| US500 | tom | standard | 0.94 | 0.36 | 0.15 | -0.15 | 0.48 | $1046 | -12.1% | FAIL |
| US500 | ichimoku | standard | 0.37 | 0.26 | 0.11 | -0.81 | 0.07 | $1036 | -14.2% | FAIL |
| US500 | macd | standard | 1.74 | 0.20 | 0.08 | -0.66 | 0.23 | $1027 | -14.4% | FAIL |
| US500 | keltner | standard | 0.90 | 0.18 | 0.07 | -0.71 | 0.26 | $1034 | -11.2% | FAIL |
| US500 | stoch | standard | 1.42 | 0.11 | 0.05 | -0.25 | 0.34 | $1058 | -18.5% | FAIL |
| US500 | turtle55 | standard | 0.63 | -0.04 | -0.02 | -1.07 | 0.07 | $1090 | -9.9% | FAIL |
| US500 | psar | standard | 1.45 | -0.40 | -0.17 | -1.38 | 0.03 | $996 | -15.7% | FAIL |
| US500 | nr7 | standard | 1.73 | -0.49 | -0.20 | -1.19 | 0.12 | $1129 | -6.3% | FAIL |
| US500 | overnight | standard | -0.08 | -0.55 | -0.23 | -3.33 | 0.00 | $1126 | -17.6% | FAIL |
| US500 | heikin | standard | 1.38 | -0.59 | -0.24 | -1.58 | 0.02 | $962 | -12.4% | FAIL |
| US500 | insideday | standard | 0.26 | -0.81 | -0.33 | -1.33 | 0.07 | $992 | -8.9% | FAIL |
| US500 | hull | swapfree | 1.58 | 2.35 | 0.97 | 2.32 | 0.69 | $1412 | -6.3% | FAIL |
| US500 | sma200 | swapfree | 1.58 | 2.20 | 0.91 | 2.19 | 0.50 | $1435 | -11.0% | FAIL |
| US500 | ema921 | swapfree | 1.76 | 2.14 | 0.88 | 2.12 | 0.47 | $1404 | -7.5% | FAIL |
| US500 | down3 | swapfree | -1.02 | 2.08 | 0.86 | 1.99 | 1.00 | $1157 | -5.5% | FAIL |
| US500 | golden | swapfree | 1.22 | 2.01 | 0.83 | 2.01 | 0.54 | $1338 | -19.8% | FAIL |
| US500 | turtle20 | swapfree | 2.66 | 2.00 | 0.83 | 1.98 | 0.56 | $1256 | -7.7% | FAIL |
| US500 | buyhold | swapfree | 2.06 | 1.99 | 0.82 | 1.99 | 1.00 | $1571 | -19.8% | FAIL |
| US500 | cumrsi2 | swapfree | 0.69 | 1.97 | 0.81 | 1.90 | 0.94 | $1174 | -6.9% | FAIL |
| US500 | tsmom | swapfree | 1.32 | 1.95 | 0.80 | 1.94 | 0.41 | $1443 | -21.7% | FAIL |
| US500 | supertrend | swapfree | 1.93 | 1.89 | 0.78 | 1.87 | 0.41 | $1436 | -6.7% | FAIL |
| US500 | rsi2 | swapfree | 0.53 | 1.82 | 0.75 | 1.73 | 0.92 | $1213 | -3.9% | FAIL |
| US500 | double7 | swapfree | 0.58 | 1.82 | 0.75 | 1.77 | 0.85 | $1260 | -8.9% | FAIL |
| US500 | sma50 | swapfree | 1.49 | 1.62 | 0.67 | 1.58 | 0.28 | $1288 | -11.2% | FAIL |
| US500 | ibs | swapfree | 1.45 | 1.51 | 0.62 | 1.40 | 0.77 | $1188 | -11.5% | FAIL |
| US500 | bollinger | swapfree | 0.89 | 1.51 | 0.62 | 1.49 | 0.96 | $1137 | -9.8% | FAIL |
| US500 | rsi14 | swapfree | 1.15 | 1.41 | 0.58 | 1.41 | 0.92 | $1154 | -15.1% | FAIL |
| US500 | adx | swapfree | 0.59 | 1.40 | 0.58 | 1.36 | 0.49 | $1104 | -6.4% | FAIL |
| US500 | ichimoku | swapfree | 1.34 | 1.31 | 0.54 | 1.28 | 0.10 | $1209 | -11.7% | FAIL |
| US500 | cci | swapfree | 1.04 | 1.28 | 0.53 | 1.25 | 0.89 | $1226 | -10.4% | FAIL |
| US500 | halloween | swapfree | 1.17 | 1.05 | 0.43 | 1.05 | 0.37 | $1088 | -19.8% | FAIL |
| US500 | overnight | swapfree | 1.04 | 1.04 | 0.43 | -0.17 | 0.00 | $1363 | -16.5% | FAIL |
| US500 | keltner | swapfree | 1.91 | 1.04 | 0.43 | 1.01 | 0.30 | $1110 | -10.0% | FAIL |
| US500 | macd | swapfree | 2.49 | 1.01 | 0.41 | 0.95 | 0.21 | $1118 | -13.1% | FAIL |
| US500 | turtle55 | swapfree | 1.56 | 0.98 | 0.40 | 0.97 | 0.07 | $1249 | -7.1% | FAIL |
| US500 | willr | swapfree | 1.01 | 0.86 | 0.35 | 0.84 | 0.49 | $1194 | -17.9% | FAIL |
| US500 | tom | swapfree | 1.33 | 0.80 | 0.33 | 0.72 | 0.53 | $1087 | -11.2% | FAIL |
| US500 | turnaround | swapfree | 2.73 | 0.76 | 0.32 | 0.58 | 0.65 | $985 | -4.8% | FAIL |
| US500 | psar | swapfree | 2.35 | 0.51 | 0.21 | 0.46 | 0.01 | $1126 | -13.3% | FAIL |
| US500 | stoch | swapfree | 1.65 | 0.46 | 0.19 | 0.44 | 0.35 | $1106 | -17.9% | FAIL |
| US500 | heikin | swapfree | 2.26 | 0.26 | 0.11 | 0.11 | 0.02 | $1082 | -11.0% | FAIL |
| US500 | nr7 | swapfree | 2.39 | 0.12 | 0.05 | 0.02 | 0.13 | $1196 | -5.4% | FAIL |
| US500 | insideday | swapfree | 0.79 | -0.35 | -0.14 | -0.42 | 0.07 | $1033 | -8.1% | FAIL |
| USTEC | down3 | standard | -0.32 | 1.77 | 0.73 | 1.51 | 0.97 | $1134 | -5.9% | FAIL |
| USTEC | adx | standard | -0.24 | 1.53 | 0.63 | 1.04 | 0.79 | $1158 | -7.6% | FAIL |
| USTEC | rsi2 | standard | 0.36 | 1.47 | 0.60 | 1.14 | 0.88 | $1179 | -8.1% | FAIL |
| USTEC | supertrend | standard | 1.10 | 1.33 | 0.55 | 0.62 | 0.76 | $1301 | -12.4% | FAIL |
| USTEC | sma200 | standard | 1.43 | 1.32 | 0.54 | 0.53 | 0.82 | $1248 | -16.0% | FAIL |
| USTEC | cumrsi2 | standard | 0.41 | 1.31 | 0.54 | 0.98 | 0.83 | $1094 | -9.3% | FAIL |
| USTEC | golden | standard | 1.62 | 1.26 | 0.52 | 0.57 | 0.83 | $1138 | -25.1% | FAIL |
| USTEC | turtle20 | standard | 1.47 | 1.08 | 0.45 | 0.40 | 0.67 | $1186 | -11.5% | FAIL |
| USTEC | turtle55 | standard | 0.88 | 1.04 | 0.43 | 0.36 | 0.62 | $1136 | -12.3% | FAIL |
| USTEC | keltner | standard | 0.73 | 1.02 | 0.42 | 0.40 | 0.66 | $1119 | -8.0% | FAIL |
| USTEC | ibs | standard | 2.09 | 0.94 | 0.39 | 0.47 | 0.72 | $972 | -15.6% | FAIL |
| USTEC | hull | standard | 1.53 | 0.94 | 0.39 | 0.21 | 0.52 | $1172 | -15.4% | FAIL |
| USTEC | sma50 | standard | 1.65 | 0.94 | 0.39 | 0.17 | 0.47 | $1193 | -16.2% | FAIL |
| USTEC | buyhold | standard | 1.90 | 0.92 | 0.38 | 0.21 | 1.00 | $1318 | -25.1% | FAIL |
| USTEC | tsmom | standard | 1.63 | 0.83 | 0.34 | 0.12 | 0.49 | $1186 | -27.9% | FAIL |
| USTEC | ema921 | standard | 2.17 | 0.83 | 0.34 | 0.08 | 0.41 | $1308 | -14.0% | FAIL |
| USTEC | double7 | standard | 1.43 | 0.83 | 0.34 | 0.40 | 0.67 | $1167 | -14.3% | FAIL |
| USTEC | willr | standard | 1.89 | 0.71 | 0.29 | 0.37 | 0.72 | $1163 | -21.9% | FAIL |
| USTEC | cci | standard | 0.98 | 0.64 | 0.26 | 0.35 | 0.70 | $1184 | -17.5% | FAIL |
| USTEC | turnaround | standard | 2.49 | 0.56 | 0.23 | 0.26 | 0.67 | $1026 | -6.7% | FAIL |
| USTEC | rsi14 | standard | 2.18 | 0.56 | 0.23 | 0.31 | 0.68 | $1274 | -17.3% | FAIL |
| USTEC | ichimoku | standard | 1.04 | 0.52 | 0.22 | -0.23 | 0.26 | $1126 | -15.6% | FAIL |
| USTEC | macd | standard | 1.45 | 0.45 | 0.19 | -0.15 | 0.38 | $991 | -23.6% | FAIL |
| USTEC | stoch | standard | 1.35 | 0.25 | 0.10 | -0.08 | 0.38 | $991 | -21.7% | FAIL |
| USTEC | halloween | standard | 1.20 | 0.25 | 0.10 | -0.20 | 0.32 | $969 | -25.1% | FAIL |
| USTEC | tom | standard | 1.39 | 0.24 | 0.10 | -0.12 | 0.53 | $1072 | -12.9% | FAIL |
| USTEC | bollinger | standard | 1.30 | 0.08 | 0.03 | -0.16 | 0.36 | $929 | -16.7% | FAIL |
| USTEC | psar | standard | 1.27 | -0.08 | -0.03 | -0.76 | 0.10 | $1012 | -20.0% | FAIL |
| USTEC | overnight | standard | 0.63 | -0.17 | -0.07 | -2.22 | 0.00 | $1249 | -20.1% | FAIL |
| USTEC | insideday | standard | 0.63 | -0.36 | -0.15 | -0.80 | 0.19 | $1063 | -15.9% | FAIL |
| USTEC | nr7 | standard | 0.64 | -0.55 | -0.22 | -1.04 | 0.14 | $1108 | -13.4% | FAIL |
| USTEC | heikin | standard | 1.41 | -0.85 | -0.35 | -1.56 | 0.01 | $899 | -18.6% | FAIL |
| USTEC | sma200 | swapfree | 2.09 | 2.09 | 0.86 | 2.09 | 0.83 | $1485 | -15.6% | FAIL |
| USTEC | supertrend | swapfree | 1.86 | 2.03 | 0.84 | 2.02 | 0.77 | $1458 | -11.9% | FAIL |
| USTEC | adx | swapfree | 0.16 | 1.99 | 0.82 | 1.97 | 0.86 | $1199 | -7.4% | FAIL |
| USTEC | golden | swapfree | 2.22 | 1.94 | 0.80 | 1.94 | 0.84 | $1360 | -24.2% | FAIL |
| USTEC | down3 | swapfree | -0.17 | 1.93 | 0.80 | 1.85 | 0.99 | $1151 | -5.6% | FAIL |
| USTEC | turtle20 | swapfree | 2.22 | 1.74 | 0.72 | 1.72 | 0.66 | $1305 | -11.0% | FAIL |
| USTEC | rsi2 | swapfree | 0.55 | 1.73 | 0.71 | 1.67 | 0.89 | $1211 | -7.9% | FAIL |
| USTEC | turtle55 | swapfree | 1.58 | 1.71 | 0.71 | 1.70 | 0.62 | $1272 | -11.3% | FAIL |
| USTEC | sma50 | swapfree | 2.45 | 1.68 | 0.69 | 1.65 | 0.59 | $1371 | -14.6% | FAIL |
| USTEC | hull | swapfree | 2.25 | 1.66 | 0.68 | 1.64 | 0.52 | $1325 | -14.3% | FAIL |
| USTEC | buyhold | swapfree | 2.62 | 1.63 | 0.67 | 1.63 | 1.00 | $1595 | -24.2% | FAIL |
| USTEC | keltner | swapfree | 1.35 | 1.63 | 0.67 | 1.61 | 0.65 | $1190 | -7.2% | FAIL |
| USTEC | cumrsi2 | swapfree | 0.59 | 1.58 | 0.65 | 1.52 | 0.83 | $1125 | -9.0% | FAIL |
| USTEC | ema921 | swapfree | 2.97 | 1.55 | 0.64 | 1.54 | 0.48 | $1499 | -12.8% | FAIL |
| USTEC | tsmom | swapfree | 2.25 | 1.54 | 0.64 | 1.54 | 0.49 | $1435 | -26.8% | FAIL |
| USTEC | ibs | swapfree | 2.45 | 1.33 | 0.55 | 1.24 | 0.79 | $1048 | -13.8% | FAIL |
| USTEC | ichimoku | swapfree | 1.79 | 1.25 | 0.52 | 1.23 | 0.26 | $1290 | -14.0% | FAIL |
| USTEC | double7 | swapfree | 1.73 | 1.23 | 0.51 | 1.19 | 0.68 | $1260 | -13.7% | FAIL |
| USTEC | willr | swapfree | 2.11 | 1.04 | 0.43 | 1.02 | 0.67 | $1237 | -21.3% | FAIL |
| USTEC | macd | swapfree | 2.08 | 1.02 | 0.42 | 0.99 | 0.37 | $1077 | -21.9% | FAIL |
| USTEC | overnight | swapfree | 1.69 | 0.99 | 0.41 | 0.10 | 0.00 | $1512 | -18.8% | FAIL |
| USTEC | cci | swapfree | 1.19 | 0.91 | 0.37 | 0.89 | 0.66 | $1240 | -17.0% | FAIL |
| USTEC | rsi14 | swapfree | 2.51 | 0.80 | 0.33 | 0.80 | 0.70 | $1306 | -17.1% | FAIL |
| USTEC | turnaround | swapfree | 2.60 | 0.70 | 0.29 | 0.54 | 0.71 | $1036 | -6.5% | FAIL |
| USTEC | halloween | swapfree | 1.65 | 0.70 | 0.29 | 0.70 | 0.34 | $1061 | -24.2% | FAIL |
| USTEC | stoch | swapfree | 1.55 | 0.56 | 0.23 | 0.55 | 0.38 | $1049 | -21.2% | FAIL |
| USTEC | psar | swapfree | 1.98 | 0.56 | 0.23 | 0.52 | 0.10 | $1137 | -18.4% | FAIL |
| USTEC | tom | swapfree | 1.70 | 0.55 | 0.23 | 0.49 | 0.50 | $1113 | -12.6% | FAIL |
| USTEC | bollinger | swapfree | 1.47 | 0.32 | 0.13 | 0.30 | 0.38 | $960 | -15.6% | FAIL |
| USTEC | insideday | swapfree | 1.02 | 0.03 | 0.01 | -0.03 | 0.20 | $1122 | -15.2% | FAIL |
| USTEC | nr7 | swapfree | 1.15 | -0.12 | -0.05 | -0.18 | 0.12 | $1169 | -12.1% | FAIL |
| USTEC | heikin | swapfree | 2.10 | -0.24 | -0.10 | -0.35 | 0.03 | $1008 | -17.6% | FAIL |
| XAUUSD | sma200 | standard | 0.63 | 1.97 | 1.25 | 1.68 | 0.98 | $2094 | -28.1% | FAIL |
| XAUUSD | ichimoku | standard | 0.08 | 1.94 | 1.24 | 1.69 | 0.94 | $1934 | -15.7% | FAIL |
| XAUUSD | sma50 | standard | -0.12 | 1.94 | 1.24 | 1.68 | 0.97 | $1807 | -14.1% | FAIL |
| XAUUSD | golden | standard | -0.32 | 1.72 | 1.10 | 1.43 | 0.92 | $1917 | -36.6% | FAIL |
| XAUUSD | ema921 | standard | 0.26 | 1.68 | 1.07 | 1.42 | 0.98 | $1677 | -19.9% | FAIL |
| XAUUSD | turtle55 | standard | -0.45 | 1.53 | 0.97 | 1.31 | 0.95 | $1585 | -26.7% | FAIL |
| XAUUSD | cumrsi2 | standard | 0.74 | 1.24 | 0.79 | 1.14 | 0.94 | $1217 | -12.7% | FAIL |
| XAUUSD | tsmom | standard | 1.17 | 1.22 | 0.78 | 0.89 | 0.86 | $1599 | -39.8% | FAIL |
| XAUUSD | insideday | standard | 1.75 | 1.18 | 0.75 | 0.94 | 0.69 | $1302 | -14.7% | FAIL |
| XAUUSD | nr7 | standard | 0.74 | 1.10 | 0.70 | 0.85 | 0.73 | $1228 | -8.9% | FAIL |
| XAUUSD | double7 | standard | 1.52 | 1.07 | 0.68 | 0.89 | 0.81 | $1332 | -23.0% | FAIL |
| XAUUSD | buyhold | standard | 1.53 | 1.02 | 0.65 | 0.69 | 1.00 | $1488 | -37.7% | FAIL |
| XAUUSD | hull | standard | -0.70 | 0.92 | 0.58 | 0.67 | 0.84 | $1308 | -21.5% | FAIL |
| XAUUSD | supertrend | standard | -0.98 | 0.77 | 0.49 | 0.58 | 0.92 | $1212 | -22.7% | FAIL |
| XAUUSD | turtle20 | standard | -0.18 | 0.74 | 0.47 | 0.54 | 0.81 | $1200 | -30.5% | FAIL |
| XAUUSD | halloween | standard | 2.10 | 0.72 | 0.46 | 0.52 | 0.71 | $1293 | -25.0% | FAIL |
| XAUUSD | psar | standard | 0.78 | 0.69 | 0.44 | 0.44 | 0.76 | $1348 | -27.9% | FAIL |
| XAUUSD | rsi2 | standard | 0.89 | 0.67 | 0.42 | 0.57 | 0.72 | $1117 | -12.7% | FAIL |
| XAUUSD | down3 | standard | 0.25 | 0.46 | 0.29 | 0.36 | 0.62 | $1038 | -12.0% | FAIL |
| XAUUSD | keltner | standard | 0.68 | 0.42 | 0.27 | 0.27 | 0.66 | $1125 | -18.1% | FAIL |
| XAUUSD | heikin | standard | -0.52 | 0.37 | 0.24 | 0.09 | 0.68 | $1035 | -33.2% | FAIL |
| XAUUSD | adx | standard | -0.24 | 0.35 | 0.22 | 0.18 | 0.69 | $1072 | -20.1% | FAIL |
| XAUUSD | stoch | standard | 0.93 | 0.11 | 0.07 | -0.11 | 0.12 | $1010 | -29.2% | FAIL |
| XAUUSD | willr | standard | 0.88 | 0.08 | 0.05 | -0.14 | 0.09 | $1040 | -23.8% | FAIL |
| XAUUSD | bollinger | standard | 0.60 | -0.07 | -0.05 | -0.21 | 0.21 | $998 | -15.2% | FAIL |
| XAUUSD | macd | standard | 0.28 | -0.08 | -0.05 | -0.31 | 0.58 | $863 | -34.1% | FAIL |
| XAUUSD | ibs | standard | 0.88 | -0.10 | -0.06 | -0.33 | 0.18 | $994 | -18.5% | FAIL |
| XAUUSD | cci | standard | 1.68 | -0.69 | -0.44 | -0.84 | 0.07 | $949 | -25.1% | FAIL |
| XAUUSD | rsi14 | standard | -1.16 | -1.65 | -1.05 | -1.77 | 0.22 | $451 | -66.8% | FAIL |
| XAUUSD | sma200 | swapfree | 0.95 | 2.26 | 1.43 | 2.25 | 0.98 | $2383 | -26.5% | FAIL |
| XAUUSD | ichimoku | swapfree | 0.35 | 2.20 | 1.40 | 2.19 | 0.97 | $2151 | -15.2% | FAIL |
| XAUUSD | sma50 | swapfree | 0.20 | 2.19 | 1.40 | 2.18 | 0.94 | $2020 | -13.9% | FAIL |
| XAUUSD | golden | swapfree | -0.02 | 2.01 | 1.28 | 2.01 | 0.91 | $2184 | -35.1% | FAIL |
| XAUUSD | ema921 | swapfree | 0.60 | 1.92 | 1.22 | 1.91 | 0.97 | $1867 | -18.9% | FAIL |
| XAUUSD | turtle55 | swapfree | -0.16 | 1.74 | 1.11 | 1.74 | 0.95 | $1722 | -25.6% | FAIL |
| XAUUSD | tsmom | swapfree | 1.47 | 1.55 | 0.98 | 1.55 | 0.81 | $1847 | -37.4% | FAIL |
| XAUUSD | insideday | swapfree | 1.98 | 1.38 | 0.88 | 1.35 | 0.74 | $1361 | -14.1% | FAIL |
| XAUUSD | buyhold | swapfree | 2.00 | 1.36 | 0.86 | 1.36 | 1.00 | $1723 | -35.1% | FAIL |
| XAUUSD | cumrsi2 | swapfree | 0.96 | 1.33 | 0.85 | 1.31 | 0.88 | $1239 | -12.6% | FAIL |
| XAUUSD | nr7 | swapfree | 0.99 | 1.32 | 0.84 | 1.28 | 0.73 | $1282 | -8.3% | FAIL |
| XAUUSD | double7 | swapfree | 1.74 | 1.24 | 0.79 | 1.22 | 0.77 | $1395 | -22.4% | FAIL |
| XAUUSD | hull | swapfree | -0.43 | 1.15 | 0.73 | 1.14 | 0.80 | $1444 | -20.8% | FAIL |
| XAUUSD | supertrend | swapfree | -0.62 | 0.96 | 0.61 | 0.95 | 0.92 | $1324 | -21.4% | FAIL |
| XAUUSD | turtle20 | swapfree | 0.08 | 0.93 | 0.59 | 0.93 | 0.81 | $1299 | -27.9% | FAIL |
| XAUUSD | psar | swapfree | 1.09 | 0.91 | 0.58 | 0.89 | 0.71 | $1487 | -26.9% | FAIL |
| XAUUSD | halloween | swapfree | 2.45 | 0.91 | 0.58 | 0.91 | 0.78 | $1387 | -23.8% | FAIL |
| XAUUSD | rsi2 | swapfree | 1.08 | 0.75 | 0.48 | 0.73 | 0.71 | $1134 | -12.6% | FAIL |
| XAUUSD | heikin | swapfree | -0.23 | 0.59 | 0.37 | 0.53 | 0.70 | $1138 | -32.5% | FAIL |
| XAUUSD | keltner | swapfree | 0.92 | 0.56 | 0.35 | 0.55 | 0.66 | $1175 | -18.0% | FAIL |
| XAUUSD | down3 | swapfree | 0.44 | 0.53 | 0.34 | 0.50 | 0.61 | $1048 | -11.9% | FAIL |
| XAUUSD | adx | swapfree | 0.03 | 0.50 | 0.32 | 0.49 | 0.67 | $1138 | -19.3% | FAIL |
| XAUUSD | stoch | swapfree | 1.27 | 0.32 | 0.21 | 0.32 | 0.24 | $1075 | -27.2% | FAIL |
| XAUUSD | willr | swapfree | 1.22 | 0.30 | 0.19 | 0.30 | 0.12 | $1107 | -22.0% | FAIL |
| XAUUSD | macd | swapfree | 0.55 | 0.13 | 0.08 | 0.11 | 0.56 | $944 | -31.2% | FAIL |
| XAUUSD | ibs | swapfree | 1.23 | 0.10 | 0.06 | 0.07 | 0.23 | $1049 | -16.8% | FAIL |
| XAUUSD | bollinger | swapfree | 0.85 | 0.06 | 0.04 | 0.05 | 0.25 | $1024 | -14.2% | FAIL |
| XAUUSD | cci | swapfree | 1.98 | -0.54 | -0.34 | -0.55 | 0.05 | $982 | -23.6% | FAIL |
| XAUUSD | rsi14 | swapfree | -1.06 | -1.53 | -0.97 | -1.53 | 0.24 | $473 | -66.1% | FAIL |

## Pre-registration

# Pre-registration: famous daily strategies on Exness costs (written 2026-11-26, before any run)

Data (offline, from the repo's stores): US500 proxy = SPY session bars 2016-01 to 2026-11 (data/idx/spy),
USTEC proxy = QQQ (data/idx/qqq); XAUUSD and EURUSD 5-minute bars 2022-11 to 2026-11 (data/fx), daily bars cut at 17:00 New York.
Rules use their published default settings. No parameter is tuned.

Fills: signal rules decide on day t's close and trade at day t+1's open. Calendar rules (overnight, turn of month,
turnaround Tuesday) trade at the close, which an always-open CFD can do at 16:00.

Costs (Exness's own pages did not load; third-party figures, made cautious):
- spread per round trip: US500/USTEC 2 bp, XAUUSD 1.5 bp, EURUSD 1.5 bp; no commission (Standard)
- Standard swap per calendar night held (Wednesday rollovers are triple in practice; counted as calendar nights):
  indices long 6.5%/yr, short 1%/yr; gold long 5%/yr, short 1%/yr; EURUSD long 2.5%/yr, short 0.5%/yr (all /360)
- Swap-free: swap 0. Caveat: extended swap-free fees after some nights are unknown and ignored.
- stress: everything x2

Periods: indices IS 2016-2020, JUDGED 2021-01 to 2026-11. Gold/EURUSD IS to 2024-06, JUDGED 2024-07 on (short, weak).
PASS (per rule x market x account): IS net mean > 0, JUDGED t >= 3.0 (about 18 rules x 4 markets x 2 accounts tested),
JUDGED Sharpe above buy-and-hold's under the same account, still positive at 2x costs, and beating 95% of
200 circular time-shift placebos of its own position series on the judged period.
Also reported: $1,000 from 2024-01-02 to the end, with the worst drop.

Rules: buyhold, sma200, golden 50/200, tsmom 252, turtle20 (20/10), turtle55 (55/20), macd 12/26/9, supertrend 10/3,
ema 9/21 cross, rsi2 (Connors: RSI2<10 above SMA200, out close>SMA5), double7, ibs (<0.2 in, >0.8 out),
bollinger 20/2 (below lower in, above mid out), overnight (close to open daily), turn of month (last trading day-1 close
to 3rd trading day close), turnaround tuesday (Monday down close to Tuesday close), donchian-breakout long-short on gold/fx
via turtle rules; trend rules are long/flat on indices, long/short on gold and EURUSD; mean-reversion rules long-only.
Thu Nov 26 20:55:59 UTC 2026

## Batch 2 (written after batch 1's results, before batch 2 runs; same data, costs, gates)
rsi14 30/70 (long below 30, out above 70; long-short on gold/fx: short above 70, out below 30), stoch 14/3 (k<20 in, k>80 out),
williams %R 14 (<-90 in, >-10 out), cci 20 (<-100 in, >0 out), adx 14 > 25 with +DI>-DI (trend, long/flat or LS),
parabolic SAR 0.02/0.2, ichimoku (close above cloud long, below short/flat), hull 55 slope, keltner 20/2 ATR breakout,
nr7 breakout (after a narrowest-of-7 range day, long above its high, exit 5 days), inside-day breakout (same, 5 days),
3 down closes buy (out on first up close), cumulative RSI(2) (sum of 2 days < 35 above SMA200, out RSI2 > 65),
heikin-ashi colour (long green, out/short red), 10-week (50-day) SMA weekly-style filter, halloween (long Nov-Apr only).


## Batch 3: the gold-trend lead on 2000-2026 gold futures (Yahoo GC=F). FAIL

Judged 2010-01 to 2024-06, years batch 1 never saw. $1,000 over those years and worst drop:

| rule | account | IS t | judged t | judged Sharpe | 2x t | placebo | $1,000 2010-2024 | worst drop |
|---|---|---|---|---|---|---|---|---|
| buyhold | standard | 1.85 | 0.30 | 0.08 | -0.90 | 0.00 | $997 | -56.9% |
| buyhold | swapfree | 2.64 | 1.50 | 0.39 | 1.50 | 0.00 | $2079 | -44.8% |
| sma200 | standard | 0.62 | -0.60 | -0.16 | -1.46 | 0.50 | $573 | -68.5% |
| sma200 | swapfree | 1.29 | 0.23 | 0.06 | 0.20 | 0.48 | $952 | -54.3% |
| ichimoku | standard | -0.79 | -0.74 | -0.20 | -1.48 | 0.47 | $555 | -63.6% |
| ichimoku | swapfree | -0.27 | -0.07 | -0.02 | -0.12 | 0.42 | $818 | -52.9% |
| sma50 | standard | -0.92 | -1.36 | -0.36 | -2.16 | 0.21 | $361 | -74.1% |
| sma50 | swapfree | -0.36 | -0.62 | -0.16 | -0.69 | 0.28 | $567 | -64.8% |

The 200-day gold trend lost money from 2010 to mid-2024 (swap-free $1,000 to $952, worst drop 54%). Its 2024-2026 result was luck.

## Mix rerun with dividends (Yahoo adjusted prices, IEF not TLT), $1,000 from 2023-12-29 to 2026-11-17

| mix | end 2024 | end 2025 | 2026-11-17 | worst drop |
|---|---|---|---|---|
| 60/30/10 SPY/IEF/GLD | $1,173 | $1,401 | $1,442 | -10.3% |
| 100% SPY | $1,248 | $1,469 | $1,589 | -18.8% |
| 60/40 SPY/IEF | $1,146 | $1,304 | $1,353 | -10.4% |

## Batch 4: the repo's own past ideas re-run at measured Exness costs (UAE Extended Swap-Free is the main case)

Costs: US500/USTEC/gold 1.0 bp round trip (measured spread + 0.4 bp slippage), EURUSD 1.2 bp, BTC/ETH 1.5 bp; swap 0 (swap-free) or the batch-1 Standard estimates. Each repo engine ran unchanged with only its costs replaced (no repo file edited).

| engine (old cost) | what it tests | best result at new costs | verdict |
|---|---|---|---|
| lab.py 5-minute rules, 4 yrs SPY/QQQ/IWM (3 bp) | ORB, noise area, VWAP, gap, stocks in play, 15:30 reversal... | 15:30 reversal, t 2.00 after in-sample (needs 3) | 0 PASS |
| hourly.py, 727 sessions x 49 symbols (2 bp) | time-of-day rules | gap + first hour, t 0.63 | 0 PASS |
| candles.py "candle brain" (5 bp, crypto 20) | first 5-min candle, 20 daily patterns, ridge combo | ridge on daily candles, judged t 2.32 (needs 3.5) | 0 PASS |
| oilbrain "oil brain" (5 bp + 1 bp a night) | EIA stocks, CFTC positioning, futures curve, momentum | backwardation, t 1.64 swap-free (no measured USOIL spread, so 5 bp kept) | 0 PASS |
| dtc_btc.py, 60+ indicators on BTC (6 bp + 3 bp a night) | ribbon + indicators, judged 2020 on | ttm_squeeze t 2.48 swap-free | 0 PASS |
| catalog.py, 60 named strategies on 10 markets (5 bp, crypto 20) | TradingView/Investopedia/book classics, judged 2016 on | **Coppock t 3.64, TRIX t 3.57: PASS its bar** | 2 PASS (see below) |
| my batches 1-2 at the new costs | 29 daily rules x 4 markets | US500 Hull t 2.36 | 0 PASS (almost unchanged; these rules trade rarely) |

### The two catalog passes, checked (pre-registered follow-up)

| | Coppock (swap-free) | TRIX 15 (swap-free) |
|---|---|---|
| pooled judged t, 2016-2026 | 3.64 | 3.57 |
| 2016-2020 / 2021-2026 | t 3.14 / t 2.00 | t 3.90 / t 1.03 |
| beats time-shifted copies | 99.0% | 99.8% |
| where it comes from (judged t) | BTC 4.0, gold 2.4, QQQ 2.2, ETH 2.1 | BTC 3.3, ETH 3.0, rest under 1.5 |
| Standard account (with swap) | t 2.92, FAIL | t 2.64, FAIL |
| on BTC judged only 2020 on (dtc_btc) | t 1.19 | t 1.15 |
| $1,000 on BTC from 2024, swap-free | $1,164 (worst drop -26%) | $1,273 (-39%) |
| BTC simply held from 2024 | $1,342 | $1,342 |

Reading: both are slow trend filters whose "edge" is mostly sitting out crypto's crashes (2018, 2022). It is much weaker since 2021, it disappears on the Standard account, and since 2024 it made less money than holding BTC. They crossed the bar only because costs fell from 5/20 bp to 1/1.5 bp (they were t 3.49 and 3.44 before). It is a candidate for a paper forward test, not a strategy to fund.

## Batch 5: real minimum lots on a $1,000 account, and Coppock/TRIX on earlier years

| market | min lot | exposure | x account | worst day | worst month | worst peak-to-trough (history) |
|---|---|---|---|---|---|---|
| US500 | 0.14 | ~$950 | 1.0x | -$104 | -$316 | -$538 |
| USTEC | 0.05 | ~$1,250 | 1.3x | -$150 | -$388 | -$1,037 (2000-02) |
| XAUUSD | 0.01 (1 oz) | ~$3,740 | **3.7x** | -$403 | -$779 | -$1,660 |
| BTCUSD | 0.01 | ~$630 | 0.6x | -$234 | -$313 | -$525 |

Gold cannot be held at a size that fits a $200-300 loss limit on $1,000: one minimum lot is 3.7 times the account.
The 60/30/10 mix can't be built from Exness minimum lots on $1,000 either (it needs a broker selling fractional ETF shares).

Coppock and TRIX on 2000-2015 (SPY, QQQ, gold, EURUSD; years the catalog pass never used): pooled alpha t -0.86 and +0.74. **Not confirmed**: outside crypto they have no edge.

Dual momentum rotation (US500/USTEC/gold/BTC, monthly): Sharpe 1.08 vs 1.31 for an equal-weight hold since 2016, worst drop -81%. FAIL. Without BTC: Sharpe 0.76 vs 1.09. FAIL.

## Batch 6: Bitcoin at one 0.01 lot (judged 2020 on, swap-free 1.5 bp)

| rule | IS t | judged t | judged Sharpe | placebo | $1,000 account from 2024 | worst drop | verdict |
|---|---|---|---|---|---|---|---|
| BTC held (0.01 lot) | 2.49 | 2.19 | 0.69 | | $1,385 | -37% | benchmark |
| **Donchian 20/10 breakout** | 3.02 | **3.00** | **0.95** | **96%** | $1,332 | **-25%** | **PASS (bare)** |
| Coppock | 3.29 | 3.19 | 1.01 | 91% | $1,175 | -17% | FAIL (placebo) |
| TRIX | 3.26 | 2.71 | 0.86 | 88% | $1,254 | -26% | FAIL |
| 200-day average | 3.24 | 2.30 | 0.73 | 72% | $1,396 | -21% | FAIL |
| weekdays only | 2.03 | 2.02 | 0.64 | 83% | $1,268 | -36% | FAIL |
| Mayer dip, 50/200 cross, vol filter, weekend, turn of month | | 0.5-1.8 | | | | | FAIL |

Robustness of Donchian on BTC (reported, not tuned): every neighbour setting is positive in both 2020-22 and 2023-26 (judged t 2.5-3.1), and the same 20/10 rule on ETH is positive (judged t 2.6, but t 0.1 since 2023).
At one 0.01 lot it made 37 trades since 2020, 43% winners, worst trade -$117, and one huge winner (2020-21) carries the average.
Bootstrapped one-year outlook: median +$158, 28% chance of a losing year, 14% chance of a $200+ drop along the way, 2% of $300+.

**Verdict:** the first rule in this whole thread to clear every gate, but only just (t exactly 3.00) and after many rules have been tried on Bitcoin across the lab. Treat it as a demo forward-test candidate. It trades about 5 times a year, so a forward test needs a year or more to mean anything. Current state (2026-11-25 close $60,378): FLAT; a buy needs a daily close above $76,291. Script: `btc_donchian_signal.py`.

## Batch 7: all 29 rules on 26 years of US500 and USTEC (judged 2013-2026, swap-free 1 bp). 0 PASS
Nothing beat buy-and-hold's Sharpe (US500 0.91, USTEC 0.94). Closest: US500 Turtle 20 (t 3.48, Sharpe 0.93, placebo 50%), USTEC IBS with next-open fills (Sharpe 0.90, placebo 99%).

## Batch 8: "IBS at the close", which only an always-open CFD allows. **USTEC PASSES**
The repo showed IBS's edge is the overnight bounce, which next-open fills miss. An Exness CFD keeps trading after the 16:00 cash close, so the order can go in a few minutes later.

Rule: after the 16:00 New York close, IBS = (close - low) / (high - low) of the 9:30-16:00 session. Flat and IBS < 0.2: buy. Long and the close is above the previous close: sell. Orders filled at the first 5-minute bar at or after 16:10 (no look-ahead), 1.5 bp round trip, swap-free.

| | USTEC IBS | USTEC held | US500 IBS | US500 held |
|---|---|---|---|---|
| 2016-2026 t | **4.27** | 2.86 | 2.72 | 2.76 |
| Sharpe | **1.29** | 0.87 | 0.82 | 0.84 |
| 2016-20 / 2021-26 t | 3.79 / 2.45 | | 1.71 / 2.14 | |
| beats shifted copies | 100% | | 100% | |
| trades | 381 (about 36 a year) | | 362 | |
| $1,000 from 2024 (1x) | $1,479, worst -9% | $1,570, worst -22% | $1,256 | $1,559 |
| at 3 bp / 5 bp cost | t 4.02 / 3.68 | | t 2.43 / 2.03 | |
| filled at 16:30 / 16:55 | t 4.42 / 4.60 | | t 2.84 / 3.19 | |
| daily-bar version 2000-2026 (close fill, judged 2013 on) | t 4.58 | | t 3.84 | |

At the minimum 0.05 lot (about $1,250, 1.3x a $1,000 account) returns and drops scale by about 1.3: from 2024 roughly +60% with a worst drop near -12%.

Verdict: the strongest result in this thread. It holds on 26 years of daily bars and on 10 years of realistic after-close fills, survives 5 bp costs, and works in both halves. Caveats: it is one of many rules tried (though t 4.3 clears even a strict bar), the US500 version is weaker and fails, after-hours CFD spreads may be wider than 1.5 bp (5 bp still passes), and orders fall around 01:10-01:55 UAE time. Next step: a demo forward test, about 36 trades a year, so 3-6 months gives a first read. Script: `ustec_ibs_signal.py`.

## Batch 9: stress test of USTEC IBS at the close (daily bars, dividend-adjusted QQQ, close fills, 1.3x for the 0.05 lot)

| period | IBS t | IBS: $1,000 became | worst drop | USTEC held | worst drop |
|---|---|---|---|---|---|
| 2000-2015, all | 2.25 | $5,640 | -49% | $1,077 | -91% |
| dot-com crash, Mar 2000 - Oct 2002 | -0.02 | $761 | -49% | $99 | -91% |
| 2008 crisis, Oct 2007 - Mar 2009 | 0.19 | $999 | -22% | $394 | -64% |
| Covid crash, Feb - Mar 2020 | 2.11 | $1,385 | 0% | $653 | -36% |
| 2022 bear market | 0.47 | $1,096 | -16% | $587 | -44% |
| 2016-2026 | 4.31 | $9,171 | -16% | $9,911 | -44% |

971 trades since 2000, 73% winners, worst single trade at 0.05 lot about -$155.
Reading: it never made money in a long bear market, but it lost far less than holding. The dot-com period alone would have dropped a $1,000 account by about $490, past a $300 limit. So the paper ledger has a fixed kill rule: stop new trades after a $250 drop from the peak.
A replay of Oct 1 - Nov 25 2026 with the ledger script: 6 trades, 4 won, net -$34.71.

## Paper ledger (scheduled)
`ibs_paper/ibs_paper.py` records every full session from 2026-11-27 in `ibs_paper/ledger.csv` (0.05 lot, 1.12 pt spread + 1 pt slippage, swap-free, $1,000 start, kill at -$250). A scheduled task runs it each weekday at 21:40 UTC (16:40 New York), posts BUY/SELL lines, and posts a weekly summary on Fridays. Half days are skipped. Review bar: 30+ closed trades, net > $0, t >= 2, never stopped.

## Batch 10: 18 intraday setups with stop-loss and take-profit (5-minute bars, real Exness costs). 0 of 67 PASS

Stop and target from the 14-day average daily range (ADR): stop 0.15 or 0.30 ADR, target 1, 2 or 3 times the stop; best of the 6 chosen on in-sample years only (indices before 2022, gold/EURUSD before Jul 2024), then judged after. If one candle touches both, the stop is counted first. Flat by the close every day, so no swap. Dollars are at the minimum lot (US500 0.14, USTEC 0.05, gold 0.01, EURUSD 0.01) over the judged trades from 2024 (gold/EURUSD from Jul 2024).

| market | setup | stop x ADR | target R | IS t | judged trades | bp a trade | judged t | 2x cost t | win rate | placebo | $ at min lot since 2024 | worst run | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USTEC | pdhl_break | 0.30 | 2 | 0.54 | 1034 | 5.36 | 2.64 | 2.32 | 44% | 99% | $+197 | $-84 | FAIL |
| USTEC | first30_mom | 0.30 | 3 | 1.14 | 372 | 6.45 | 1.68 | 1.51 | 39% | 95% | $+62 | $-81 | FAIL |
| USTEC | orb15 | 0.30 | 3 | 0.49 | 1228 | 3.24 | 1.56 | 1.24 | 39% | 92% | $+108 | $-286 | FAIL |
| US500 | orb30 | 0.30 | 2 | -0.44 | 1216 | 1.93 | 1.44 | 0.69 | 43% | 93% | $+76 | $-64 | FAIL |
| XAUUSD | bb_rev | 0.30 | 3 | 0.56 | 623 | 3.04 | 1.11 | 0.80 | 39% | 88% | $+708 | $-348 | FAIL |
| XAUUSD | pdhl_break | 0.15 | 1 | -0.67 | 486 | 1.23 | 1.09 | 0.34 | 53% | 97% | $+223 | $-123 | FAIL |
| XAUUSD | vwap_pb | 0.30 | 1 | -0.74 | 601 | 1.63 | 0.83 | 0.40 | 51% | 93% | $+366 | $-249 | FAIL |
| US500 | orb15 | 0.30 | 2 | 0.57 | 1227 | 1.12 | 0.81 | 0.09 | 42% | 90% | $+56 | $-82 | FAIL |
| XAUUSD | rsi_rev | 0.30 | 1 | 1.62 | 581 | 1.52 | 0.76 | 0.34 | 52% | 87% | $+330 | $-244 | FAIL |
| US500 | inside_break | 0.30 | 2 | 0.31 | 203 | 2.15 | 0.66 | 0.35 | 44% | 93% | $+5 | $-37 | FAIL |
| USTEC | vwap_pb | 0.15 | 3 | 0.45 | 1105 | 0.77 | 0.61 | 0.09 | 32% | 71% | $-5 | $-139 | FAIL |
| US500 | pivot_bounce | 0.15 | 3 | -0.80 | 883 | 0.53 | 0.49 | -0.43 | 30% | 63% | $+14 | $-69 | FAIL |
| USTEC | pivot_bounce | 0.30 | 2 | 1.09 | 870 | 1.07 | 0.49 | 0.19 | 40% | 74% | $+99 | $-82 | FAIL |
| XAUUSD | first30_mom | 0.15 | 1 | 1.39 | 31 | 2.01 | 0.48 | 0.28 | 61% | 76% | $+23 | $-32 | FAIL |
| USTEC | orb30 | 0.15 | 3 | -0.18 | 1203 | 0.52 | 0.42 | -0.10 | 31% | 89% | $+86 | $-118 | FAIL |
| US500 | first30_mom | 0.30 | 1 | 0.68 | 263 | 0.85 | 0.38 | -0.06 | 54% | 79% | $+37 | $-34 | FAIL |
| XAUUSD | rally_open | 0.30 | 2 | 0.03 | 207 | 0.62 | 0.18 | -0.07 | 43% | 74% | $+48 | $-270 | FAIL |
| XAUUSD | three_pb | 0.30 | 3 | -0.54 | 592 | 0.33 | 0.13 | -0.20 | 39% | 63% | $+74 | $-472 | FAIL |
| EURUSD | inside_break | 0.30 | 2 | -0.29 | 108 | 0.06 | 0.03 | -0.46 | 44% | 70% | $+1 | $-32 | FAIL |
| USTEC | inside_break | 0.15 | 1 | -2.38 | 176 | -0.14 | -0.08 | -0.43 | 49% | 60% | $+16 | $-30 | FAIL |
| USTEC | gap_fill | 0.15 | 2 | 1.59 | 792 | -0.27 | -0.21 | -0.71 | 35% | 47% | $+31 | $-111 | FAIL |
| EURUSD | orb30 | 0.30 | 3 | -0.39 | 623 | -0.24 | -0.25 | -1.28 | 37% | 79% | $-16 | $-93 | FAIL |
| US500 | three_pb | 0.15 | 2 | 1.11 | 652 | -0.24 | -0.26 | -1.34 | 40% | 76% | $-50 | $-76 | FAIL |
| EURUSD | vwap_pb | 0.30 | 3 | 0.40 | 598 | -0.25 | -0.26 | -1.34 | 40% | 81% | $-16 | $-64 | FAIL |
| EURUSD | first30_mom | 0.30 | 1 | 0.33 | 63 | -0.67 | -0.29 | -0.73 | 51% | 56% | $-5 | $-15 | FAIL |
| EURUSD | london_break | 0.30 | 2 | 0.73 | 613 | -0.27 | -0.31 | -1.46 | 41% | 50% | $-18 | $-78 | FAIL |
| US500 | ny_reversal | 0.15 | 3 | 0.01 | 118 | -0.93 | -0.32 | -0.67 | 25% | 36% | $-11 | $-44 | FAIL |
| XAUUSD | inside_break | 0.30 | 3 | -0.01 | 89 | -3.04 | -0.37 | -0.47 | 29% | 28% | $-101 | $-317 | FAIL |
| US500 | gap_fill | 0.15 | 3 | -0.46 | 790 | -0.48 | -0.41 | -1.26 | 27% | 42% | $-9 | $-66 | FAIL |
| US500 | rally_open | 0.15 | 3 | -0.70 | 421 | -0.83 | -0.55 | -1.21 | 28% | 29% | $-32 | $-50 | FAIL |
| XAUUSD | london_break | 0.15 | 1 | -1.47 | 551 | -0.60 | -0.56 | -1.36 | 51% | 64% | $-123 | $-329 | FAIL |
| USTEC | dip_open | 0.15 | 3 | 0.96 | 424 | -1.19 | -0.59 | -0.92 | 27% | 11% | $-16 | $-68 | FAIL |
| EURUSD | orb15 | 0.15 | 3 | -1.04 | 623 | -0.37 | -0.61 | -2.27 | 28% | 87% | $-25 | $-47 | FAIL |
| EURUSD | pdhl_break | 0.15 | 3 | -0.29 | 480 | -0.46 | -0.68 | -2.17 | 28% | 91% | $-24 | $-49 | FAIL |
| US500 | ema_cross | 0.15 | 2 | -1.43 | 1113 | -0.59 | -0.73 | -1.98 | 36% | 64% | $+21 | $-46 | FAIL |
| US500 | vwap_pb | 0.15 | 3 | -1.04 | 1105 | -0.69 | -0.73 | -1.79 | 30% | 57% | $-72 | $-115 | FAIL |
| US500 | pdhl_break | 0.15 | 3 | -0.07 | 1052 | -0.79 | -0.80 | -1.83 | 29% | 69% | $-77 | $-92 | FAIL |
| USTEC | rally_open | 0.30 | 2 | -0.45 | 435 | -2.42 | -0.90 | -1.14 | 38% | 24% | $-67 | $-96 | FAIL |
| XAUUSD | pdhl_fade | 0.30 | 1 | 0.81 | 398 | -2.29 | -0.98 | -1.34 | 49% | 30% | $-341 | $-570 | FAIL |
| USTEC | three_pb | 0.30 | 3 | 1.04 | 683 | -1.60 | -0.99 | -1.39 | 47% | 38% | $-163 | $-207 | FAIL |
| EURUSD | ny_reversal | 0.30 | 1 | 0.35 | 27 | -3.78 | -1.02 | -1.29 | 41% | 22% | $-11 | $-14 | FAIL |
| USTEC | rsi_rev | 0.30 | 3 | -0.78 | 840 | -2.10 | -1.04 | -1.36 | 40% | 18% | $+4 | $-132 | FAIL |
| USTEC | sweep | 0.15 | 1 | 0.28 | 790 | -1.06 | -1.14 | -1.85 | 49% | 35% | $-15 | $-84 | FAIL |
| EURUSD | dip_open | 0.15 | 1 | -1.82 | 205 | -0.67 | -1.16 | -2.90 | 52% | 76% | $-15 | $-17 | FAIL |
| XAUUSD | sweep | 0.30 | 1 | 0.63 | 360 | -3.22 | -1.35 | -1.70 | 47% | 19% | $-434 | $-686 | FAIL |
| USTEC | ema_cross | 0.15 | 1 | -0.41 | 1106 | -1.07 | -1.39 | -2.22 | 50% | 29% | $+23 | $-89 | FAIL |
| US500 | sweep | 0.30 | 1 | -0.46 | 812 | -1.82 | -1.41 | -2.18 | 49% | 26% | $-128 | $-142 | FAIL |
| US500 | pdhl_fade | 0.15 | 1 | -0.37 | 909 | -1.01 | -1.58 | -3.15 | 50% | 54% | $-46 | $-58 | FAIL |
| XAUUSD | dip_open | 0.15 | 3 | 0.46 | 175 | -4.91 | -1.73 | -2.03 | 23% | 15% | $-321 | $-364 | FAIL |
| XAUUSD | pivot_bounce | 0.30 | 2 | 0.19 | 421 | -5.04 | -1.78 | -2.08 | 37% | 6% | $-793 | $-871 | FAIL |
| EURUSD | rsi_rev | 0.30 | 2 | -0.96 | 581 | -1.52 | -1.79 | -2.97 | 38% | 52% | $-97 | $-137 | FAIL |
| US500 | bb_rev | 0.30 | 3 | 0.40 | 1191 | -2.19 | -1.80 | -2.61 | 41% | 14% | $-203 | $-266 | FAIL |
| USTEC | ny_reversal | 0.15 | 3 | -0.44 | 209 | -4.74 | -1.84 | -2.09 | 21% | 4% | $-89 | $-101 | FAIL |
| USTEC | bb_rev | 0.30 | 3 | 1.04 | 1184 | -2.95 | -1.87 | -2.29 | 42% | 6% | $-299 | $-361 | FAIL |
| US500 | dip_open | 0.15 | 3 | 0.05 | 414 | -2.83 | -1.96 | -2.66 | 25% | 8% | $-56 | $-74 | FAIL |
| EURUSD | three_pb | 0.30 | 1 | -0.80 | 584 | -1.35 | -2.05 | -3.57 | 47% | 38% | $-87 | $-90 | FAIL |
| EURUSD | rally_open | 0.15 | 2 | -0.38 | 200 | -1.65 | -2.08 | -3.34 | 33% | 49% | $-36 | $-48 | FAIL |
| EURUSD | bb_rev | 0.15 | 1 | -1.71 | 625 | -0.73 | -2.12 | -5.01 | 51% | 80% | $-50 | $-58 | FAIL |
| EURUSD | ema_cross | 0.30 | 3 | 0.39 | 619 | -1.92 | -2.12 | -3.23 | 35% | 9% | $-131 | $-137 | FAIL |
| XAUUSD | ema_cross | 0.30 | 1 | 0.37 | 615 | -4.26 | -2.19 | -2.63 | 46% | 5% | $-980 | $-1051 | FAIL |
| XAUUSD | orb30 | 0.15 | 1 | -1.15 | 622 | -2.28 | -2.23 | -3.06 | 47% | 9% | $-531 | $-586 | FAIL |
| EURUSD | pivot_bounce | 0.15 | 2 | -0.90 | 454 | -1.25 | -2.31 | -4.15 | 34% | 33% | $-63 | $-72 | FAIL |
| USTEC | pdhl_fade | 0.30 | 3 | 0.16 | 886 | -5.12 | -2.32 | -2.62 | 36% | 9% | $-315 | $-329 | FAIL |
| EURUSD | sweep | 0.15 | 3 | 0.50 | 399 | -1.69 | -2.45 | -3.90 | 25% | 18% | $-74 | $-77 | FAIL |
| EURUSD | pdhl_fade | 0.15 | 3 | 0.50 | 446 | -1.91 | -2.93 | -4.46 | 24% | 8% | $-94 | $-95 | FAIL |
| XAUUSD | orb15 | 0.15 | 1 | -1.64 | 622 | -3.10 | -3.04 | -3.87 | 46% | 1% | $-721 | $-814 | FAIL |
| US500 | rsi_rev | 0.15 | 1 | -2.69 | 886 | -2.23 | -3.47 | -5.04 | 47% | 4% | $-73 | $-82 | FAIL |

Reading: no buy-low/sell-high, breakout, support/resistance, pullback, sweep or session-open setup makes money reliably after costs on these markets. The closest is the USTEC previous-day high/low breakout (judged t 2.64, beats 99% of random-direction copies, +$197 at 0.05 lot since 2024), below the t 3 bar. Gold at its 3.7x minimum lot swings hundreds of dollars either way, so even a break-even setup is outside a $200-300 loss limit.

## Batch 11A: the repo's skill chain as one system, 2024-01-02 to 2026-11-25 ($1,000 account)
Scanner (opening-range breakouts on the 40-name store) > entry timer (first 5-min close above the 9:30-9:45 high) > exit planner (stop at the range midpoint, 2R target, out 15:55) > budget ($10 risk, $1,000 cap) > risk check (stop the day after -$30). The news skill can't be replayed (no headline archive), so it's left out. Exness stock-CFD spreads aren't measured, so 3 bp (and 5 bp) per round trip.

| system | trades | won | net | $ a trade | worst drop | daily t | end equity |
|---|---|---|---|---|---|---|---|
| full chain, 3 bp | 3,551 | 44% | **-$911** | -$0.26 | -$1,228 | -1.65 | $89 |
| full chain + Time Machine gate, 3 bp | 261 | 47% | **+$189** | +$0.72 | -$73 | 1.37 | $1,189 |
| full chain, 5 bp | 3,550 | 43% | -$1,493 | -$0.42 | -$1,713 | -2.70 | (account gone) |
| + Time Machine gate, 5 bp | 261 | 47% | +$146 | +$0.56 | -$86 | 1.06 | $1,146 |

Reading: the chain on its own would have emptied a $1,000 account. The Time Machine's history check is the only part that adds value: it cuts trades by 93% and turns the result slightly positive, but daily t 1.37 is not proof.

## Batch 11B: breakout strategies on daily bars (swap-free; judged 2013 on, BTC 2020 on)
| market | squeeze | 52-week high | weekly high | NR4 | ATR channel | Donchian + 2/4 ATR bracket | Williams volatility breakout |
|---|---|---|---|---|---|---|---|
| US500 | t -0.40 | 1.64 | 2.25 | 1.87 | 2.74 | 2.58 | -1.25 |
| USTEC | -0.03 | 1.82 | 2.75 | 0.85 | 2.10 | 3.58 (placebo 56%, FAIL) | 0.85 |
| gold | -0.44 | 1.73 | -0.09 | 0.89 | 0.36 | 2.09 | **3.14** (dies after 2020) |
| BTC | 0.13 | 2.64 | 0.64 | 1.47 | 2.86 | 2.33 | **5.96 PASS** |
(Darvas was excluded: an exit bug made it identical to buy-and-hold.)

### Williams volatility breakout on Bitcoin (buy-stop at today's open + 0.6 x yesterday's range, sell at the day's close)
- Judged 2020-2026 t 5.96; every k from 0.4 to 0.8 positive in 2020-22 AND 2023-26 (t 3.5-3.9 in the later half); 3x cost t 5.62; ETH the same (t 5.3-6.2).
- Checked on the repo's 1-hour BTC bars (Nov 2024 - Nov 2026): the intraday fills match the daily-bar method exactly (4.73 vs 4.76 bp a day), but those two years alone are only t 1.2. Most of the edge came before late 2024.
- At one 0.01 lot from 2024: 368 trades, 52% won, net +$547, worst day -$49, worst drop -$226, $1,000 to $1,547.
- Gold: strong 2013-2019 (t 4.4), gone since 2020 (t 0.3). Not for gold.
Verdict: the strongest crypto result in this research. It is a well-known public rule, so the edge may be fading (the last two years are weaker). Demo forward-test candidate alongside USTEC IBS.

## Batch 12: rules that fit $228-$1,000 at minimum lots (BTC 0.01, USTEC 0.05, US500 0.14, EURUSD 0.01). 0 PASS
Pre-registered 2026-11-27 00:31 UTC. Swap-free costs (BTC 1.5 bp, USTEC 2.12 pt, US500 0.9 pt, EURUSD 1.2 pip). "$ from 2024" is one minimum lot.

| rule | IS t | judged t | 2x cost | placebo | last 2 yrs t | $ from 2024 (worst drop) | verdict |
|---|---|---|---|---|---|---|---|
| BTC IBS < 0.2 at the UTC close | -0.22 | 1.47 | 1.41 | 69% | 0.52 | +$298 (-$104) | FAIL |
| BTC IBS > 0.8 momentum | 3.75 | 0.16 | 0.08 | 14% | -1.18 | -$218 (-$372) | FAIL |
| BTC RSI2 < 10 above SMA200 | 0.81 | 2.00 | 1.98 | 90% | 1.49 | +$280 (-$160) | FAIL |
| BTC 3 lower closes | 1.47 | 1.70 | 1.66 | 88% | 1.60 | +$474 (-$85) | FAIL |
| Williams SHORT, BTC | 4.65 | 2.56 | 2.41 | 100% | 0.75 | +$119 (-$195) | FAIL |
| Williams long + short, BTC | 9.80 | 6.14 | 5.89 | 100% | 1.14 | +$681 (-$195) | the long side alone already passed; adding the short adds +$134 and no lower drop |
| Williams SHORT, USTEC | 0.16 | 1.38 | 1.02 | 99% | 1.87 | +$352 (-$106) | FAIL |
| Williams SHORT, US500 | -1.41 | -1.74 | -2.47 | 48% | 0.19 | -$6 | FAIL |
| Williams long / short, EURUSD (2022-26 5-min bars, judged 2024-07 on) | -0.67 / -1.26 | 0.22 / 0.75 | | 58% / 96% | | -$25 / +$33 | FAIL |
| Intraday momentum (Gao et al.): overnight+first 30 min sign -> trade 15:30-16:00, USTEC / US500 | 0.65 / -1.17 | **-2.91 / -3.24** | | | | -$94 / -$123 | FAIL (it ran backwards since 2021) |
| Same, 9:30-15:30 sign (Baltussen) | -0.45 / -1.22 | -0.62 / -2.52 | | | | -$238 / -$237 | FAIL |
| Same, both signs must agree | 0.62 / -0.92 | -1.71 / -2.90 | | | | | FAIL |
(Yahoo's daily EURUSD bars have open = close and can't be used for intraday rules; the repo's 5-minute EURUSD was used instead.)

Reading: none of the small-lot ideas beats the two survivors. BTC RSI2 and 3-lower-closes are mildly positive but under t 2. Intraday momentum, a well-published effect, has reversed on US indices since 2021, so it is not worth a reversal bet either (that would be chosen after seeing the data).

## Batch 13: after-close overnight reversal and crude oil at 0.01 lot. 0 PASS
| rule | IS t | judged t | 2x cost | Standard | placebo | last 2 yrs t | $ from 2024 at min lot | verdict |
|---|---|---|---|---|---|---|---|---|
| USTEC: day down 1%+ -> buy 16:10, sell next 9:30 | 0.16 | 1.02 | 0.90 | 0.67 | 66% | 1.04 | +$258 | FAIL |
| USTEC: any down day, same | 0.51 | 1.44 | 1.21 | 0.73 | 71% | 1.27 | +$352 | FAIL |
| US500: day down 1%+ / any down day | 0.44 / 0.96 | 0.79 / 1.07 | | | 65% / 57% | | +$91 / +$141 | FAIL |
| Oil IBS at the close | 1.87 | -0.91 (1.40 without the Apr-May 2020 negative-price weeks) | | | 28% | 0.45 | +$121 | FAIL |
| Oil RSI2 | -0.13 | -0.60 | | | | | -$69 | FAIL |
| Oil Williams long / short | 1.38 / -1.43 | -1.54 / 1.24 | | | 11% / 98% | | -$33 / +$117 | FAIL |
(Oil cost assumed 5 bp; Exness's oil spread is not measured. Pre-FOMC drift on USTEC was dropped: the Fed calendar site isn't on the network allowlist.)

## Batch 14: "IBS at the close" on other stock indices (daily bars, judged 2013 on, 1.5 bp). No new market passes
| index | judged t | Sharpe vs hold | Standard | placebo | last 2 yrs t | verdict |
|---|---|---|---|---|---|---|
| USTEC (QQQ, check) | **4.66** | 1.25 vs 0.90 | 4.22 | 100% | 1.94 | PASS (as batch 8) |
| US30 (Dow) | 2.79 | 0.75 vs 0.65 | 2.22 | 98% | 0.81 | FAIL (just short) |
| US2000 (Russell) | 2.40 | 0.64 vs 0.48 | 1.84 | 98% | 1.28 | FAIL |
| Nikkei 225 | 1.79 | 0.49 vs 0.68 | 1.29 | 77% | 0.82 | FAIL |
| DAX, FTSE, STOXX 50, Hang Seng | -0.85 to 0.25 | | | | | FAIL |
Reading: the IBS bounce is a US-index effect, strongest on the Nasdaq. Europe and Asia show nothing. This supports USTEC IBS being real rather than luck, but it adds no second market. Its last two years are weaker (t 1.94), which the paper ledger will show.

## Batch 15: scanner strategies that trade EVERY day (Hazza's ask: at least 3 daily candidates)
Universe: the repo's 30 single stocks (stock CFDs; Exness spreads, lots and listings not verified) and the CFD indices/crypto. $1,000 split across the picks, 3 bp round trip. Placebo = buying the same number of RANDOM names from the same list on the same days (this matters: the list is today's winners, so just holding any of them made money).

Daily bars, judged 2019-2026:
| rule (trades every day) | judged t | 5 / 10 bp | placebo | $ 2019 on | worst drop | $ 2024 on | last 2 yrs t |
|---|---|---|---|---|---|---|---|
| D1 3 lowest-IBS stocks, close -> next open | 2.93 | 2.33 / 0.82 | **96%** | +$1,924 | -$380 | +$1,068 | 1.65 |
| D1b same, close -> next close | 1.90 | | 40% | +$2,014 | -$557 | +$719 | 0.58 |
| D2 3 lowest RSI2 above SMA200 | 2.36 | | 42% | +$2,164 | -$548 | +$470 | -0.49 |
| D3 2 biggest gap-downs, open -> close | -0.41 | | 7% | -$465 | -$1,263 | -$962 | -1.37 |
| D4 3 worst 5-day returns | 1.37 | | 12% | +$1,816 | -$997 | +$772 | 0.38 |
| D5 lowest-IBS market of US500/USTEC/US30/US2000/BTC/ETH | 2.82 | | 96% | +$4,040 | -$554 | +$885 | 0.97 (look-ahead: BTC/ETH's day closes 3 h after the US close; not usable as is) |
| D5b same, US indices only | 1.74 | | 54% | +$1,126 | -$423 | +$290 | 0.70 |
| D6 scanner + Time Machine, relaxed to 1 trade a day (5-min, 2024-26) | -0.37 | | | -$76 | -$289 | | -0.96 (relaxing the gate kills the +$189) |
Random 3 names held close -> next close made a median +$2,100 since 2019: D1b, D2 and D4 are no better than random.

5-minute check (realistic: decide 15:50, buy the 15:55 bar, sell the next 9:30 open; 2022-12 to 2026-11; the store isn't split-adjusted, so split nights were dropped):
| rule | t | placebo | total $ | worst drop | $ 2024 on | last 2 yrs t |
|---|---|---|---|---|---|---|
| **D7 3 worst intraday losers (9:30-15:50), 15:55 -> 9:30** | 1.65 | 61% | +$987 | -$352 | **+$1,134** | 0.95 |
| D1 3 lowest IBS, 15:55 -> 9:30 | 1.10 | 38% | +$472 | -$465 | +$413 | -0.55 |
| USTEC every night, 16:10 -> 9:30, 0.05 lot (from batch 13) | 1.94 | | +$640 | -$264 | +$621 | |
| random 3 of the 30 stocks, 15:55 -> 9:30 (median of 200) | | | +$651 | | +$534 | |
Exiting at 9:35 or 10:00 instead of 9:30 cuts D1 and D7 by half or more. 10 bp costs make D1 lose and leave D7 at about breakeven-plus.

Ranking for daily trading (by profit since 2024 and worst drop, realistic fills). **All three are WEAK: none clears t 3, and most of their profit is the ordinary overnight drift that random stocks or plain USTEC also earn.**
1. D7 intraday-loser scan: +$1,134 since 2024, worst -$352 (above the $300 limit at $1,000; run at $500 for -$176).
2. USTEC every night at 0.05 lot: +$621, worst -$264, known costs, no scanner.
3. D1 lowest-IBS scan: +$413, worst -$465; the daily-bar result (t 2.93, placebo 96%) did not survive 5-minute fills.
All three are on the paper ledger (`ibs_paper/daily_paper.py`, from 2026-11-27, kill -$300 per book). A replay of Nov 2-25 2026: D7 +$43, D1 +$44, USTEC +$46.

### Batch 15c: the stock scans at Exness's real stock-CFD hours. NOT TRADABLE on Exness
Exness stock CFDs trade only 09:40-15:45 New York and are not swap-free (web lookup 2026-11-27). Retest: decide 15:35, buy 15:40, sell next 09:45, 3 bp + 8%/yr long swap (Friday 3 nights).
| rule | t | placebo | total $ 2022-26 | worst drop | $ 2024 on |
|---|---|---|---|---|---|
| D7 intraday losers | 0.86 | 29% | +$557 | -$436 | +$584 |
| D1 lowest IBS | -0.17 | 4% | -$84 | -$784 | -$304 |
| (random 3 names, one draw) | 1.35 | | +$668 | -$354 | +$269 |
Both fail the pre-set bar (t >= 2 and net > 0 after swap) and were taken off the paper ledger before any paper trade.
Replacement daily book, same timing as USTEC every night: **US500 every night** at 0.14 lot (16:10 -> 9:30, 0.9 pt cost): 2016-26 +$610 (worst -$326), 2024 on +$337 (worst -$174), t 2.09 since 2024. Weak.
Daily-trading candidates actually executable on Exness, ranked: 1) USTEC every night (+$621 since 2024, worst -$264); 2) US500 every night (+$337, -$174); 3) BTC Williams, an order every day that fills on about 1 day in 3 (+$562, -$150; the one real pass). NQ and SP move together, so run one of them, not both, on $1,000.
Update 2026-11-27 01:20 UTC: Hazza says the 09:40-15:45 stock-hours source is wrong, so D7 and D1 are back on the paper ledger as first designed (15:55 -> 9:30, $0 swap, 3 bp), next to NQ and SP. Exness stock hours stay unconfirmed; if the 15:55 entry or 9:30 exit isn't possible in MT5, the 15c numbers apply.

## Batches 16-19: swing "buy low, sell in 2-3 days" and academic anomalies (overnight 2026-11-27)
All pre-registered (PREREG.md). Indices judged 2013-2026 on 2000-2026 daily data, crypto judged 2020 on, swap-free costs, close fills.
Pass bar: IS > 0, judged t >= 3, 2x cost positive, placebo >= 95%, Sharpe above holding, both halves positive.

- **Batch 16:** 13 swing/calendar rules on US500, USTEC, US30, US2000, BTC and ETH: 1 PASS of 70.
  - Rules: Connors RSI2, cumulative RSI, R3, %b, multiple down days, 10-day low hold 3 days, 5-day low hold 2 days, VIX stretch, multi-day IBS, pre-holiday, option-expiration week, Halloween, turn of month.
  - The pass is US30 %b (t 3.72, 37 trades).
  - Near: US500 10-day low hold 3 days (t 3.11, Sharpe 0.83 vs hold 0.86). USTEC multi-day IBS (t 2.96).
  - Calendar effects (pre-holiday, opex week, Halloween, turn of month) all failed since 2013.
- **Batch 17:**
  - FX swing on 6 pairs: 0 of 36.
  - **Vol filter (hold only when 20-day vol < 20%) PASSES:** US500 t 3.69, USTEC t 3.61.
  - US dip ensemble (R1+R6+R9 on US500 and USTEC): t 3.72, but a -$543 drop since 2024 at min lots.
  - Connors stock swing (RSI2 < 5 above SMA200, up to 3 names, sell above SMA5, average hold 3.9 days, 67% winners): t 2.66, placebo 96%, +$773 since 2024, worst -$300. Near.
  - Weekly stock reversal: t 3.13 but placebo 83%. Fail.
- **Batch 18:**
  - Vol filter confirmed on US30 (t 3.42), not US2000.
  - VIX contango filter: placebo fail.
  - Month-end pension rebalancing: t 2.85, placebo 99%, 4% of days in market. Near.
  - BTC weekend fade: fail.
- **Batch 19:** crypto weekly time-series momentum.
  - ETH 7-day passes bare (t 3.09). BTC 7-day fails (2.49).
  - The 28-day lookback passes on both (t 3.70 / 3.71), but it was a reported neighbour, and on BTC it is the same trade as Donchian (correlation 0.80).

### Ranked list of everything that passes (distinct ideas, at Exness minimum lots)
| # | strategy | judged t | $ since 2024 | worst drop since 2020 | trades/yr | notes |
|---|---|---|---|---|---|---|
| 1 | USTEC IBS at the close (0.05) | 4.3-4.6 | +$426 | -$154 | ~36 | on paper ledger |
| 2 | BTC Williams breakout (0.01) | 5.96 | +$562 | -$250 | ~120 | last 2 yrs t 1.2; on paper |
| 3 | BTC trend: Donchian 20/10 or 28-day momentum (0.01) | 3.0 / 3.7 | +$339 / +$459 | -$385 / -$221 | 5-10 | one idea, two versions |
| 4 | Vol-managed index: hold USTEC / US500 / US30 only when 20-day vol < 20% | 3.4-3.7 | +$293 (USTEC) / +$321 (US500) | -$211 / -$142 | 2-4 | earns LESS than holding, but halves the worst drop (USTEC 2000-26: -16% vs -83%) |
| 5 | US30 Bollinger %b dip (min lot unverified) | 3.72 | +$89 | -$147 | ~3 | fragile: 37 trades, flat for 2 years |
| 6 | ETH weekly momentum, 7-day (ETH min lot unverified) | 3.09 | +$589 | -$502 | ~13 | drop too big for $1,000 |
| 7 | US dip ensemble, 6 sub-rules at min lots | 3.72 | +$1,476 | -$665 | ~70 | too big for $1,000 (up to 6 lots at once); 0.60 correlated with #1 |
Near misses (not called strategies): month-end rebalancing (t 2.85), Connors stock swing (t 2.66), US500 10-day low hold 3 days (t 3.11, Sharpe just under hold).
**Fewer than 10 pass. 7 clear the bar; only #1-#4 are usable on a $1,000 account.**
Correlations (2020 on): IBS vs Williams 0.13, IBS vs vol filter 0.19, Williams vs Donchian 0.43, Donchian vs BTC 28-day 0.80, IBS vs ensemble 0.60.

## Batch 20: every standard indicator and candlestick signal. 0 of 400 PASS
- **What was tested:** 50 textbook signals with standard settings:
  - Oscillators: RSI, Stochastic, StochRSI, Williams %R, CCI, ROC, Momentum, Ultimate, CMO, MACD, PPO, TRIX, Awesome.
  - Trend: MA crosses, ADX/DI, Parabolic SAR, Supertrend, Ichimoku, Aroon, Donchian, Keltner, Heikin-Ashi, Vortex.
  - Volatility: Bollinger, squeeze, Keltner touch, big range, NR7.
  - Volume: OBV, CMF, A/D, MFI, volume spike, Force index.
  - Candles: engulfing, hammer, morning star, piercing, three soldiers, doji, harami, inside bar, key reversal, three crows.
- **How:** long entries at the close, hold 1 or 3 days, on US500, USTEC, US30 and BTC, at swap-free costs.
- **Multiple-testing guard:** 200 sets of random entries matched to each signal's trade count. The 95th percentile of the best random t across the 50 signals was 3.2-4.0 depending on market and hold. In other words, with 50 tries, pure luck reaches t 3-4.
- **Results:**
  - Best real signals: USTEC Donchian 20 breakout, hold 1 day, t 3.64 (but in-sample negative). US30 inside bar, hold 3 days, t 3.52 (below its random bar of 3.69). BTC Keltner upper break, hold 3 days, t 3.07 (bar 3.40).
  - Nothing beats random luck.
- **Reading:** standard indicators and candlestick patterns used as entry signals add nothing on these markets once you account for how many were tried.
- **Caution on earlier passes:** results with t 3.0-3.7 (BTC Donchian 3.00, ETH momentum 3.09, US30 %b 3.72, vol filters 3.4-3.7) sit inside the range luck reaches over a large family of tries. Only USTEC IBS at the close (t 4.3-4.6, and it holds on 26 years and on the other US indices) and BTC Williams (t 5.96) clearly clear it.

## Paper strategies backtested before 2024 (daily bars, swap-free costs, fixed min-lot notional: USTEC $1,250, US500 $950, BTC $630, stock books $1,000)
| strategy | 2000-07 | 2008-12 | 2013-19 | 2020-23 | 2024-now | t before 2024 |
|---|---|---|---|---|---|---|
| USTEC IBS at close | +$1,240 (worst -$586) | +$756 (-$208) | +$835 (-$187) | +$1,338 (-$154) | +$426 (-$113) | 3.99 |
| BTC Williams (from 2014-09) | | | +$4,251 (-$95) | +$2,198 (-$250) | +$562 (-$150) | 10.1 |
| BTC 20-day breakout | | | +$2,005 (-$473) | +$1,559 (-$385) | +$339 (-$286) | 4.13 |
| Calm USTEC hold | +$480 (-$179) | +$366 (-$187) | +$1,268 (-$137) | +$532 (-$174) | +$293 (-$211) | 3.81 |
| USTEC every night | +$1,031 (-$508) | +$255 (-$349) | +$1,010 (-$156) | +$284 (-$395) | +$606 (-$242) | 2.95 |
| US500 every night | +$252 (-$422) | -$5 (-$258) | +$415 (-$152) | +$120 (-$316) | +$303 (-$168) | 1.49 |
| Stock scan: biggest losers (from 2005) | +$264 (-$155) | +$553 (-$418) | +$943 (-$338) | +$104 (-$626) | +$1,368 (-$280) | 2.02 |
| Stock scan: lowest IBS (from 2005) | +$539 (-$67) | +$1,207 (-$173) | +$1,273 (-$244) | +$713 (-$380) | +$1,050 (-$277) | 4.83 |
Caveats:
- The stock scans here use daily bars (close to next open). On 5-minute bars from 2022, the IBS scan made far less (t 1.10) and did no better than random stocks.
- The 30-stock list is today's winners, so its early years flatter it (survivorship bias).
- Every strategy has made money in every period with data, except US500 every night, which lost $5 in 2008-12. Its t before 2024 is only 1.49.
- Worst drops over $300 in some periods: USTEC IBS -$586 in 2000-07 (dot-com), BTC breakout -$473, USTEC every night -$508 and -$395, US500 every night -$422 and -$316, biggest-losers scan -$626 in 2020-23, lowest-IBS scan -$380 in 2020-23.

## Batch 22: Supertrend on its own (ATR 7/10/14 x mult 2/3, long-only and long/short). FAIL everywhere
Earlier tests: Supertrend 10/3 always-in (batches 1-2, 7) and as a 1/3-day entry (batch 20) also failed.

| market | long-only judged t (6 variants) | long/short judged t | verdict |
|---|---|---|---|
| USTEC daily | 2.6 to 3.1 | -0.0 to 0.4 | FAIL: Sharpe 0.83 vs 0.91 for just holding (it does cut the worst drop from -35% to -20%) |
| US500 daily | 1.9 to 2.3 | -0.7 to -0.2 | FAIL |
| US30 daily | 2.1 to 2.7 | -0.4 to 0.2 | FAIL |
| Gold daily | 0.3 to 1.7 | -1.1 to 0.9 | FAIL |
| BTC daily | 2.0 to 2.9 | 0.4 to 1.6 | FAIL |
| ETH daily | 2.5 to 3.3 (3 of 6 clear every gate) | 1.0 to 2.3 | FAIL (needed 4 of 6); closest; Sharpe 1.01 vs 0.72, worst drop -52% |
| USTEC 1-hour | 0.8 to 1.8 | -0.6 to 0.9 | FAIL |
| US500 1-hour | 1.1 to 2.2 | -0.7 to 0.8 | FAIL |

Reading: long-only Supertrend mostly just follows buy-and-hold with smaller drops. The short side loses on every index. Intraday it is weaker still.

## Batch 23: low-risk daily candidates for a $3,000 account (minimum lots, swap-free)
Single rules (daily bars; judged 2013-now, BTC 2020-now; the pre-2024 slice must be positive):
| rule | verdict | t | random-timing placebo | pre-2024 per year | 2024-now | worst drop since 2016 |
|---|---|---|---|---|---|---|
| USTEC IBS (base) | PASS | 4.56 | 99% | $198 | +$426 | -$154 |
| F1 IBS only while calm (vol < 20%) | PASS | 3.15 | 97% | $81 | +$87 | -$90 |
| F2 IBS only above SMA200 | PASS | 4.14 | 100% | $118 | +$338 | -$130 |
| F3 BTC Williams only above SMA50 | fail (the filter is no better than a random filter, 86%) | 5.39 | 86% | $354 | +$457 | -$140 |
| F4 buy USTEC after a BTC day down 5%+ | fail | 0.85 | 68% | $37 | +$71 | -$230 |
| F5 IBS overnight only (close -> next open) | fail | 2.80 | 94% | $56 | +$231 | -$166 |
| US500 IBS (daily bars) | PASS | 3.61 | 100% | $98 | +$230 | -$155 |

The US500 IBS pass is on daily bars. With realistic 16:10 fills (batch 8) it was weaker (t 2.72). Calm USTEC had a 94% placebo with this seed (96-98% before).

$3,000 portfolios, one minimum lot per rule, no optimisation. BTC is valued at today's 0.01-lot size (~$630) in every year, so the BTC dollars for 2016-2019 are scaled up. The 2024-now column is the realistic one.
| portfolio | 2016-23 per year (worst drop) | 2024-now per year (worst drop) | per trading day since 2024 | worst drop 2016-now | losing years |
|---|---|---|---|---|---|
| P3 USTEC IBS + BTC Williams + Calm USTEC | $1,083 (-$244) | $444 (-$269) | $1.76 | -$269 (9.0%) | 0 of 11 |
| P5 USTEC IBS + US500 IBS + BTC Williams | $1,046 (-$238) | $422 (-$231) | $1.67 | -$238 (7.9%) | 0 of 11 |
| P6 USTEC IBS above SMA200 + US500 IBS + BTC Williams | $946 (-$238) | $391 (-$158) | $1.55 | -$238 (7.9%) | 0 of 11 |
| P1 USTEC IBS + BTC Williams | $934 (-$239) | $342 (-$146) | $1.36 | -$239 (8.0%) | 0 of 11 |
| P2 P1 + BTC Donchian | $1,375 (-$372) | $460 (-$232) | $1.83 | -$372 (12.4%, over the limit) | 0 of 11 |
| P4 all four | $1,524 (-$372) | $561 (-$341) | $2.23 | -$372 (12.4%, over) | 0 of 11 |

## Batch 24: new edges (Williams breakout on other markets, pairs)
- Williams breakout on single alt coins passes: XRP t 3.28, BCH 3.85, LINK 3.71. Every coin tested was positive in-sample. Hourly-built bars confirm the crypto daily data is genuine.
- 24b, an 11-coin basket ($250 per coin): t 3.69, placebo 100%, about $1,100/yr since 2024, worst drop -$681 (too big). At $100 per coin, scaled: about $440/yr, worst about -$270. Correlation with USTEC IBS 0.17.
- Stocks Williams fail (t 1.50). USTEC/US500 and ETH/BTC pairs fail.
- 24c: copper and silver Williams "passes" (t 8.85 / 5.17) were Yahoo futures daily-bar artifacts: on bars built from hourly data they showed t 0.60 / 1.06. Natural gas and platinum fail. IBS on commodities fails.
- On paper from 2026-11-28: crypto_williams_paper.py (10 coins, $100 each, 5 bp, -$300 basket kill). Replay over Nov 1-27 2026: -$27 (53 fills, 20 won). UNCONFIRMED: Exness alt-coin min lots and spreads.

## Batch 25: free "Bloomberg-style" data as filters (2026-11-28)
FRED, CBOE, Coinmetrics and Binance downloads were refused in this session, so free Yahoo proxies were used: yield curve (10y-3m), credit (HYG/IEF), VIX term structure, dollar index, MOVE bond vol, SKEW, consumer risk appetite (XLY/XLP), QQQ trend.
Result: 0 of 31 filter tests helped (chosen on pre-2024, confirmed on 2024-now, against random gates). Filters mostly cut profit more than risk.
Closest: bond-vol-low on the coin basket (passed pre-2024, failed 2024-now) and on BTC Williams (worst drop -$250 -> -$150, but profit roughly halved, placebo 91%).
Not tested: jobless claims and financial-conditions index (FRED), funding rates and exchange flows (crypto), because those sources were blocked; oil inventories (no oil candidate).

## Batch 26: hourly and 15-minute rules at full Exness spreads (2026-11-28)
23 rules: opening-range breakout with daily trend, RSI(2) on 15m and 60m, EMA20/50 trend on 15m and 60m with daily filter, gap fade,
last-half-hour momentum (USTEC, US500 5-min 2016-26); London breakout, hourly RSI(2), hourly EMA trend (BTC, ETH, gold, hourly 2024-26).
Result: 0 pass. Index rules: best was USTEC EMA trend 15m (+$753 2016-22, t 1.84, but +$91 2023-26, no better than random times).
RSI(2) intraday lost in nearly every year (57% win rate, still losing). Near misses (only 2 years of hourly data):
| rule | trades/wk | 2025 | 2026 | worst | t | placebo |
|---|---|---|---|---|---|---|
| ETH London breakout ($1,000) | 4.0 | +$1,008 | +$654 | -$146 | 2.98 | 100% |
| Gold London breakout (1 oz) | 2.8 | +$70 | +$1,189 | -$410 | 1.82 | 98% |
| Gold EMA trend 60m | 1.1 | +$710 | +$936 | -$302 | 1.71 | 98% |
ETH London breakout is on paper as WATCH ONLY from 2026-11-28 (eth_london_paper.py; replay Nov 1-27: 17 trades, +$168).

## Batch 27: hourly near misses before 2024 (Binance hourly data)
| rule | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | worst drop |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ETH London breakout ($1,000) | -49 | +1,289 | +487 | +1,815 | +991 | +29 | -98 | +192 | +666 | +437 | -$672 |
| Gold London breakout (1 oz, PAXG proxy) | | | | -122 | -1,269 | -503 | -983 | -1,245 | -513 | +1,493 | -$4,710 |
| Gold EMA trend 60m (1 oz, PAXG proxy) | | | | -197 | -493 | -175 | -38 | -258 | +414 | +610 | -$1,212 |
ETH: PASS on the long data (2017-23 t 3.58, placebo 100%; 2024-now t 2.00), 4 trades a week; at $1,000 the worst drop is -$672, so about $400-500 of ETH
fits a $3k account (worst about -$270 to -$340). Gold: fail (PAXG is a token proxy, noisier than XAUUSD; the 2024-26 numbers differ from GC=F).

## Batches 28-30: one fixed WORTHY bar (trader-lab/judge.py), candle brain v2, oil brain v2, new session breakouts (2026-11-28)
Bar: before 2024 net > 0 and t >= 2; 2024-now net > 0 and t >= 1; whole t >= 3; 2x costs positive; beats 95% of random timing; worst drop within -$300 at today's min lot; distinct = corr <= 0.5.
| rank | candidate | size | yearly $ (2024, 2025, 2026 to Nov) | worst drop | whole t |
|---|---|---|---|---|---|
| 1 | BTC Williams breakout | 0.01 lot | +391, -21, +151 | -$237 | 9.32 |
| 2 | USTEC IBS | 0.05 lot | +63, +327, +65 | -$200 | 4.56 |
| 3 | Coin Williams basket (10 alts) | $100 each | +640, +177, +375 | -$255 | 3.57 |
| 4 | ETH London breakout | 0.2 lot (~$330) | +28, +184, +114 | -$259 | 3.57 |
| (dup) | US500 IBS | 0.14 lot | +118, +131, -3 | -$167 | 3.61 (corr 0.75 with USTEC IBS) |
Failed the bar: Calm USTEC (no better than random timing), BTC Donchian (drop -$447), ETH 7-day momentum, BTC London breakout (t 2.70, drop -$337),
ETH/BTC US-session breakouts, alt London basket, gold IBS / turn of month / Williams (1 oz drops -$510 to -$660), oil Williams;
candle brain v2 0 of 19 (inside-day breakouts on BTC/ETH/gold worked before 2024, flat since); oil brain v2 0 of 4 (inventories, COT hedging pressure, curve).

## Batches 31-34: broad search (other indices, FX, silver, calendar, weekly bars, short side, pair, contraction setups)
About 50 more rules. New WORTHY and distinct: BTC NR4 breakout, BTC Williams short below SMA50, BTC weekly Williams. Seven distinct in all:
| rank | candidate | size | 2024 / 2025 / 2026 | worst drop | whole t |
|---|---|---|---|---|---|
| 1 | BTC Williams breakout | 0.01 | +391 / -21 / +151 | -$237 | 9.32 |
| 2 | BTC NR4 breakout (both sides by SMA50) | 0.01 | +200 / -42 / +226 | -$94 | 5.27 |
| 3 | USTEC IBS | 0.05 | +63 / +327 / +65 | -$200 | 4.56 |
| 4 | BTC weekly Williams | 0.01 | +242 / +25 / +53 | -$245 | 4.43 |
| 5 | BTC Williams short below SMA50 | 0.01 | +82 / +35 / +85 | -$210 | 3.58 |
| 6 | Coin Williams basket | $100 x 10 | +640 / +177 / +375 | -$255 | 3.57 |
| 7 | ETH London breakout | 0.2 lot | +28 / +184 / +114 | -$259 | 3.57 |
Failed: IBS on GER40/UK100/JP225 (US30 t 2.92 near, but same family), turn of month, pre-holiday, weekly IBS, FX RSI2, silver, index Williams
long/short, GER40/US500 pair (t 2.01), 4-hour NR7, gold weekly/short Williams, alt short and NR7 baskets (t 1.78 / 2.84). FOMC days not tested (no
reliable date list offline). Five of the seven are BTC rules: low daily correlation, but one regime.
