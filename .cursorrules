# HyperTracker API

Pre-computed intelligence layer for Hyperliquid, the largest on-chain perpetual futures exchange. Cohort analytics, live order flow, liquidation risk scoring, leaderboards, and more. All data is independently aggregated and not available through the standard Hyperliquid API.

## Authentication

```
Authorization: Bearer <your_jwt_token>
```

Get your token: https://app.coinmarketman.com/hypertracker/api-dashboard

## Base URL

```
https://ht-api.coinmarketman.com/api/external
```

All paths below are relative to this base URL. Full OpenAPI spec: `GET /api/external-json`.

## Critical Rules

1. **Dates MUST be ISO 8601.** Example: `2026-02-25T00:00:00.000Z`. Never epoch milliseconds.
2. **Coin values are uppercase ticker strings.** Examples: `"BTC"`, `"ETH"`, `"SOL"`. No USDT suffix.
3. **Fills have a 24-hour max window.** `end` must be within the same day as `start`.
4. **Order snapshots floor date:** `2026-01-19T11:05:00Z`. Timestamps must align to 5-minute boundaries.
5. **Leaderboard `rankBy`:** `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay`. **`limit`:** `25`, `50`, `100`.
6. **Default result count is 500** unless `limit` is specified. Paginate with `cursor` from the response.
7. **Data refreshes every ~5 minutes.** Plan polling accordingly.
8. **REST only.** WebSocket and Webhook delivery are available on higher tiers as a custom package (not part of the standard API).

---

## Historical Data Availability

Not all data goes back the same distance. Check this before building anything historical.

| Data Type | Lookback | Earliest Date |
|-----------|----------|---------------|
| Individual positions | ~10 months | Apr 2025 |
| Position metrics (general OI) | ~9 months | May 2025 |
| Fills (trades) | ~6.5 months | Jul 2025 |
| Per-coin cohort metrics | ~4 weeks | Jan 2026 |
| Order snapshots | ~3 weeks | Jan 19, 2026 |
| Cohort bias | **12 hours only** | Rolling window |
| Heatmap / Leaderboards | **Current only** | No history |

**Important:** Cohort bias (`/segments/bias`) returns ~6 data points over a 12-hour rolling window. It is not suitable for multi-day backtesting. Use `/position-metrics/coin/{coin}/segment/{segmentId}` for historical cohort analysis (up to ~4 weeks).

---

## Cohort Segments

Every wallet on Hyperliquid is classified into 16 behavioral segments across two dimensions.

### Size-Based Cohorts
| ID | Name | Position Size |
|----|------|---------------|
| 16 | Shrimp | $0 - $250 |
| 1 | Fish | $250 - $10K |
| 2 | Dolphin | $10K - $50K |
| 3 | Apex Predator | $50K - $100K |
| 4 | Small Whale | $100K - $500K |
| 5 | Whale | $500K - $1M |
| 6 | Tidal Whale | $1M - $5M |
| 7 | Leviathan | $5M+ |

### PnL-Based Cohorts
| ID | Name | All-Time PnL |
|----|------|--------------|
| 8 | Money Printer | $1M+ |
| 9 | Smart Money | $100K - $1M |
| 10 | Consistent Grinder | $10K - $100K |
| 11 | Humble Earner | $0 - $10K |
| 12 | Exit Liquidity | -$10K - $0 |
| 13 | Semi-Rekt | -$100K - -$10K |
| 14 | Full Rekt | -$1M - -$100K |
| 15 | Giga-Rekt | Below -$1M |

PnL segments use `/segment/{segmentId}`. Size segments use `/position-size-segment/{id}`. Call `GET /segments` to confirm latest ID mapping.

---

## Endpoints

### Cohort Intelligence

**GET /segments** — All 16 cohort definitions with IDs and names. Call first to confirm segment IDs.

**GET /segments/bias** — Directional bias for every cohort. Negative = net short, positive = net long. ~6 data points over a 12-hour rolling window.

**GET /segments/summary** — High-level summary: trader counts, aggregate positioning, segment distribution.

### Positions & Market Exposure

**GET /positions** — Individual open positions. Params: `start` (required), `end`, `coin`, `limit`, `cursor`. Historical from April 2025.

**GET /positions/ranked** — Positions ranked by criteria. Params: `rankBy`, `segmentIds`, `coin`, `limit`.

**GET /position-metrics/general** — Exchange-level OI, position counts, aggregate metrics. Params: `start`, `end`.

**GET /position-metrics/coin/{coin}** — Per-coin long/short breakdown, OI, trader counts. Params: `start`, `end`.

**GET /position-metrics/coin/{coin}/segment/{segmentId}** — Per-coin, per-PnL-cohort metrics. Compare Smart Money (9) vs Exit Liquidity (12). Params: `start`, `end`.

**GET /position-metrics/coin/{coin}/position-size-segment/{id}** — Per-coin, per-size-tier metrics. Params: `start`, `end`.

### Order Flow

**GET /orders/5m-snapshots/latest** — Most recent snapshot of every open order. Params: `coin`. Returns: price, size, side, orderType (stop, tp, limit_increase, limit_reduction).

**GET /orders/5m-snapshots** — Historical snapshots. Params: `coin`, `timestamp` (must be 5-min boundary, after floor date).

### Liquidation Risk

**GET /liquidation-risk** — Per-asset risk scoring based on proximity to liquidation thresholds. Returns risk scores, at-risk OI, directional skew.

**GET /heatmap** — Liquidation clusters across price levels. Current snapshot only, no history.

### Leaderboards

**GET /leaderboards/perp-pnl** — Top traders by PnL. Params: `rankBy`, `limit`, `page`.

**GET /leaderboards/perp-volume** — Top traders by volume. Params: `rankBy`, `limit`, `page`.

### Fills

**GET /fills** — Trade executions. Params: `start` (required), `end` (required, same day), `coin`, `limit`, `cursor`. 24hr max window. Historical from July 2025.

### Volume Metrics

**GET /perp-volume-metrics** — Aggregate volume metrics. Params: `start`, `end`, `cursor`.

### Wallets

**GET /wallets/all** — All tracked wallets with profile data and activity.

**GET /wallets/{address}** — Profile for a specific wallet.

**GET /wallets/{address}/positions** — Open positions for a specific wallet.

### $HYPE Token

**GET /hype/holders** — Top 100 HYPE holders with balances, staking, 24h/7d comparisons.

### Global State

**GET /state/summary** — Exchange snapshot: total/active traders, aggregate OI, segment distribution. Params: `includeDetails`, `includeHistory`.

### Builders

**GET /builders** — All builder code holders with user counts and volume.

**GET /builders/{builder}/users** — Users attributed to a builder code.

---

## Response Examples

### /segments/bias
```json
[
  {"segmentId": 9, "segmentName": "Smart Money", "bias": 0.42, "timestamp": "2026-03-01T12:00:00Z"},
  {"segmentId": 12, "segmentName": "Exit Liquidity", "bias": -0.31, "timestamp": "2026-03-01T12:00:00Z"}
]
```
Positive bias = net long, negative = net short.

### /liquidation-risk
```json
[
  {"coin": "BTC", "riskScore": 0.72, "atRiskOI": 1450000, "longRisk": 0.65, "shortRisk": 0.79}
]
```

### /orders/5m-snapshots/latest
```json
[
  {"coin": "BTC", "price": 89500.0, "size": 2.5, "side": "B", "orderType": "stop"}
]
```

### Paginated response (positions, fills, etc.)
```json
{
  "data": [...],
  "cursor": "eyJsYXN0SWQiOiAxMjM0NX0="
}
```
Pass `cursor` value as a query parameter on next request to get the next page. When `cursor` is `null`, you've reached the end.

---

## Rate Limits

| Tier | Price | Requests | Rate Limit |
|------|-------|----------|------------|
| Free | $0 | 100/day | — |
| Pulse | $179/mo | 50,000/mo | 12/min |
| Flow | $1,159/mo | 200,000/mo | 25/min |
| Stream | $2,399/mo | 1,000,000/mo | 100/min |

---

## Code Patterns

### Python: Auth + Request
```python
import requests

headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
response = requests.get(
    "https://ht-api.coinmarketman.com/api/external/segments/bias",
    headers=headers
)
data = response.json()
```

### JavaScript: Auth + Request
```javascript
const response = await fetch(
  "https://ht-api.coinmarketman.com/api/external/segments/bias",
  { headers: { "Authorization": "Bearer YOUR_JWT_TOKEN" } }
);
const data = await response.json();
```

### ISO 8601 Dates (Python)
```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
params = {
    "start": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "end": now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
}
```

### Cursor Pagination
```python
cursor = None
all_data = []
while True:
    params = {"start": start, "end": end, "coin": "BTC"}
    if cursor:
        params["cursor"] = cursor
    resp = requests.get(url + "/positions", headers=headers, params=params).json()
    all_data.extend(resp["data"])
    cursor = resp.get("cursor")
    if not cursor:
        break
```

### Paginating Fills (day by day)
```python
base_date = datetime(2026, 2, 20, tzinfo=timezone.utc)
for day_offset in range(5):
    start = base_date + timedelta(days=day_offset)
    end = start + timedelta(hours=23, minutes=59, seconds=59)
    params = {
        "start": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "coin": "BTC"
    }
    response = requests.get(url + "/fills", headers=headers, params=params)
```

### 5-Minute Boundary Alignment
```python
def align_to_5min(dt):
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
```

---

## Example Prompts

### For Vibe Coders (no dev experience needed)

**"I want to see what smart money is doing right now. Build me something simple."**
Endpoints: `/segments/bias`, `/segments`
Fetch bias data, display each cohort with a simple long/short indicator. Color-code green for long, red for short. One-page HTML.

**"Show me which coins are about to get liquidated"**
Endpoints: `/liquidation-risk`
Fetch risk data, sort by score, display as a simple ranked list with risk level colors.

**"What should I be watching today? Rank coins by where the most interesting activity is happening."**
Endpoints: `/segments/bias`, `/position-metrics/coin/{coin}/segment/9`, `/orders/5m-snapshots/latest`, `/liquidation-risk`
Score each coin by: smart money conviction, order flow clustering, liquidation proximity. Rank and surface top 5 with a one-line reason for each.

**"Am I about to get liquidated? Check if my position is safe."**
Endpoints: `/liquidation-risk`, `/heatmap`
User provides coin and direction. Fetch liquidation risk for that coin, show how close current price is to liquidation clusters, and give a plain-English safety rating.

**"Show me a fear/greed gauge for Hyperliquid right now"**
Endpoints: `/segments/bias`, `/liquidation-risk`, `/state/summary`
Composite score from cohort sentiment, liquidation proximity, and OI trends. Display as a simple gauge with color-coded zones. One-page HTML.

**"Show me what whales are doing vs retail on BTC"**
Endpoints: `/position-metrics/coin/BTC/segment/9`, `/position-metrics/coin/BTC/position-size-segment/7`, `/position-metrics/coin/BTC/position-size-segment/16`
Compare Leviathan (7) and Smart Money (9) positioning against Shrimp (16). Show who's long, who's short, and whether they agree.

### Dashboards

**"Build a Hyperliquid market dashboard with cohort positioning, order flow, and liquidation risk"**
Endpoints: `/segments/bias`, `/orders/5m-snapshots/latest`, `/liquidation-risk`, `/position-metrics/coin/{coin}`

**"Track my positions and compare them against smart money"**
Endpoints: `/wallets/{address}/positions`, `/position-metrics/coin/{coin}/segment/9`, `/segments/bias`

### Trading Signals

**"Alert me when two cohorts diverge on any coin"**
Endpoints: `/segments/bias`, `/position-metrics/coin/{coin}/segment/{segmentId}`
Poll bias data, detect when cohorts split (e.g., Smart Money long, Exit Liquidity short). Pull coin-level metrics to find which coins drive the divergence.

**"Mean-reversion alert when a cohort's bias hits an extreme and reverses"**
Endpoints: `/segments/bias`
Track bias time series, define extremes (> 0.7 or < -0.7), fire alert when pullback starts.

**"Contrarian signal: go opposite of Exit Liquidity and Giga-Rekt"**
Endpoints: `/segments/bias`, `/position-metrics/coin/{coin}/segment/12`, `/position-metrics/coin/{coin}/segment/15`
When Exit Liquidity (12) and Giga-Rekt (15) are heavily positioned one way, flag the opposite direction as a potential trade.

### Order Flow

**"Map BTC orders by price level and type. Show where stops, TPs, and limits cluster."**
Endpoints: `/orders/5m-snapshots/latest?coin=BTC`
Group orders into price buckets, count by type, visualize as a bar chart relative to current price.

### Liquidation

**"Liquidation risk monitor across all coins, ranked and auto-refreshing"**
Endpoints: `/liquidation-risk`, `/position-metrics/coin/{coin}`
Rank by risk score, pull OI for top 5 riskiest, color-code severity, refresh every 5 minutes.

### Leaderboard

**"Watchlist from today's top 25 traders. Alert me when they open new positions."**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlDay&limit=25`, `/wallets/{address}/positions`
Fetch leaderboard, baseline positions, poll for changes every 5 minutes.

### Backtesting

**"Backtest: how did Smart Money positioning on BTC predict price moves over the last 4 weeks?"**
Endpoints: `/position-metrics/coin/BTC/segment/9`
Use per-coin cohort metrics (available ~4 weeks back). Correlate Smart Money net exposure changes with subsequent BTC price movement. Report hit rate and average return per signal. Note: cohort bias (`/segments/bias`) only has 12 hours of history and cannot be used for multi-day backtests.

**"Compare all 8 PnL cohorts as predictors of BTC direction over the last month"**
Endpoints: `/position-metrics/coin/BTC/segment/{segmentId}` (for each ID 8-15)
For each cohort, pull 4 weeks of positioning data. Correlate exposure changes with subsequent price moves. Rank cohorts by predictive accuracy.

### Market Regime

**"Is the market in risk-on or risk-off mode right now based on cohort behavior?"**
Endpoints: `/segments/bias`, `/state/summary`, `/liquidation-risk`
Risk-on signals: Smart Money and Money Printer net long, low liquidation risk, rising OI. Risk-off: defensive cohorts reducing exposure, high liq risk, falling OI. Classify current regime and show supporting data.

**"Daily market regime report: combine cohort bias, OI, and liquidation risk into one summary"**
Endpoints: `/segments/bias`, `/position-metrics/general`, `/liquidation-risk`, `/state/summary`
Pull all four data sources. Classify as risk-on, risk-off, or neutral. Show the 3 strongest supporting signals and 1 contradicting signal. Output as a clean summary.

### Multi-Endpoint

**"Coin screener ranking assets by smart money conviction, order flow health, and liquidation risk"**
Endpoints: `/position-metrics/coin/{coin}/segment/9`, `/orders/5m-snapshots/latest`, `/liquidation-risk`, `/state/summary`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 401 Unauthorized | Check JWT token is valid, included as `Bearer <token>` |
| Empty fills | `start` and `end` must be within the same 24-hour period |
| Empty order snapshots | Timestamp must be after `2026-01-19T11:05:00Z` and on a 5-minute boundary |
| Dates not working | Use ISO 8601: `2026-02-25T00:00:00.000Z`. Not epoch milliseconds. |
| Leaderboard error | `rankBy` must be `pnlAllTime`/`pnlMonth`/`pnlWeek`/`pnlDay`. `limit` must be 25/50/100. |
| Empty cohort history | `/segments/bias` only has 12 hours. Use `/position-metrics/coin/{coin}/segment/{id}` for longer lookbacks (up to ~4 weeks). |
| Stale data | Refreshes every ~5 minutes. Wait for next cycle. |
| No more pages | `cursor` is `null` in the response. You've fetched everything. |

## Links

- Dashboard & API Key: https://app.coinmarketman.com/hypertracker/api-dashboard
- Docs: https://docs.coinmarketman.com
- OpenAPI Spec: `GET /api/external-json`
