---
name: hypertracker
description: Query HyperTracker's pre-computed analytics layer for Hyperliquid. Use when the user asks about Hyperliquid wallets, cohort positioning (Money Printer, Smart Money, Whales, etc.), live order flow, closed trades, liquidation risk, leaderboards, smart money flows, or wants to analyze any address or position on Hyperliquid perps. Covers 21 endpoints across positions, fills, orders, segments (cohorts), and heatmaps. Requires a JWT bearer token from hypertracker.io.
---

# HyperTracker API

Pre-computed intelligence layer for Hyperliquid, the largest on-chain perpetual futures exchange. Cohort analytics, live order flow, liquidation risk scoring, leaderboards, and more. All data is independently aggregated and not available through the standard Hyperliquid API.

## Authentication

```
Authorization: Bearer <your_jwt_token>
```

Get your token: https://app.coinmarketman.com/hypertracker/api-dashboard?utm_source=skill&utm_medium=ai&utm_campaign=skill-launch

## Base URL

```
https://ht-api.coinmarketman.com/api/external
```

All paths below are relative to this base URL.

## Critical Rules

1. **Dates MUST be ISO 8601.** Example: `2026-02-25T00:00:00.000Z`. Never epoch milliseconds.
2. **Coin values are uppercase ticker strings.** Examples: `"BTC"`, `"ETH"`, `"SOL"`. No USDT suffix.
3. **Fills have a 24-hour max window.** `end` must be within the same day as `start`.
4. **Order snapshots floor date:** `2026-01-19T11:05:00Z`. Timestamps must align to 5-minute boundaries.
5. **Leaderboard `rankBy`:** `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay`. **`limit`:** `25`, `50`, `100`.
6. **Default result count is 500** unless `limit` is specified. Paginate with `cursor` from the response.
7. **Data refreshes every ~5 minutes** for most endpoints. State/summary updates may take up to 15-17 minutes. Plan polling accordingly.
8. **REST only.** REST endpoints are the surface across all tiers.

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

**Important:** Cohort bias (`/segments/{segmentId}/bias-history`) returns data over a rolling window. It is not suitable for multi-day backtesting. Use `/position-metrics/coin/{coin}/segment/{segmentId}` for historical cohort analysis (up to ~4 weeks).

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

All 16 cohorts (both PnL and size) use `/segment/{segmentId}`. A separate `/position-size-bucket/{sizeBucketId}` endpoint (IDs 1-10) provides metrics by individual position size ranges, independent of cohort classification. Call `GET /segments` to confirm latest ID mapping.

---

## Endpoints

### Cohort Intelligence

**GET /segments** — All 16 cohort definitions with IDs and names. Call first to confirm segment IDs.

**GET /segments/{segmentId}/bias-history** — Bias history for a specific cohort, exchange-wide across all coins. The `history` field is an array of arrays. Each row's column order matches `historySnapshotStructure` (i.e. `[timestamp, bias, exposureRatio, openValue, openLongValue, openShortValue, activePerpEquity]`). Bias is signed: positive = net long, negative = net short, with magnitude that factors in exposure ratio (can exceed 1). Different scale from per-coin `bias` in `/positions/heatmap` — the two are not directly comparable. Params: `segmentId` (path), `limit` (max 1000), `nextCursor`, `start`, `end`, `positionRecencyTimeframe` (enum: `24h`, `7d`, `30d`, `all`; default: `all`). Note: `start` is required when `limit`, `end`, or `nextCursor` is set, otherwise returns 400 with message `"'start' query param is required for 'end', 'nextCursor' and 'limit' query params"`. To get all cohorts, call once per segment ID.

**GET /segments/{segmentId}/summary** — Per-segment summary: trader counts, aggregate positioning, top 10 open perps. Params: `segmentId` (path), `positionAge` (enum: `all`, `24h`, `7d`, `30d`; default: `all` — filter positions by age).

### Positions & Market Exposure

**GET /positions** — Historic positions. Params: `start` (required), `end`, `coin`, `segmentId` (filter by cohort ID), `address` (one or more addresses, repeat the param for multiple, e.g. `address=0x...` or `address=0x...&address=0x...`), `open`, `limit`, `nextCursor`. Historical from April 2025. Returns tens of thousands of positions per call with pre-computed data (PnL segments, size segments, leverage, liquidation progress, funding, entry price, unrealized PnL). Can also be used for reverse-lookups: given a coin, side, leverage, and entry price from a Hyperliquid PnL share card or screenshot, filter open positions to identify matching wallets (see Reverse Lookup prompts and code pattern below).

**GET /positions/coins** — Summary of position count by coin. Returns total long/short values and position counts per coin across the entire exchange. No parameters beyond auth. Use this for a quick market-wide snapshot of where capital is deployed. Note: `totalValueLong` always equals `totalValueShort` at this coin-aggregate level — that is correct perp math (every long contract has a matched short counterparty), not a broken field. Use `countLong` / `countShort` for crowding analysis; use per-cohort data from `/positions/heatmap` for directional notional.

**GET /positions/metrics** — Metrics for specific positions by ID. Params: `ids` (required, array, max 50 position IDs — 64-char hex), `start`, `end`, `limit`, `nextCursor`. Returns liquidation price, mark price, position value, and unrealized PnL over time.

**GET /positions/open/coin/{coin}** — Download latest open positions snapshot for a coin as CSV. Params: `coin` (path). Returns 302 redirect to presigned S3 URL. CSV columns include: id, address, coin, side, dex, size, value, entryPrice, unrealizedPnl, funding, liquidationPrice, liquidationProgress, crossLeverage, isolatedLeverage, openTime, and full profile data (totalEquity, perpEquity, countOpenPositions, pnl, balance, perpPnlSegmentId, sizeSegmentId).

**GET /coin/{coin}/open-positions/history** — Historical open positions snapshot entries for a coin. Params: `coin` (path), `start`, `end`, `nextCursor`. Returns snapshot metadata with download URLs.

**GET /position-metrics/general** — Exchange-level OI, position counts, aggregate metrics. Params: `start` (required), `end`, `limit`, `nextCursor`.

**GET /position-metrics/coin/{coin}** — Per-coin long/short breakdown, OI, trader counts. Params: `coin` (path), `start` (required), `end`, `limit`, `nextCursor`.

**GET /position-metrics/coin/{coin}/segment/{segmentId}** — Per-coin, per-cohort metrics. Works for all 16 segments (both PnL and size cohorts). Compare Smart Money (9) vs Exit Liquidity (12), or Leviathan (7) vs Shrimp (16). Params: `coin`, `segmentId` (path, enum: 1-16), `start`, `end`, `limit`, `nextCursor`.

**GET /position-metrics/coin/{coin}/position-size-bucket/{sizeBucketId}** — Per-coin position metrics by position size buckets (not cohorts). Size buckets are based on individual position size, IDs 1-10 (ranging from <$1K to >$2.5M). Params: `coin`, `sizeBucketId` (path), `start` (required), `end`, `limit`, `nextCursor`.

### Order Flow

**GET /orders/5m-snapshots/latest** — Most recent snapshot of every open order. Params: `coin`, `limit`, `nextCursor`, `address`, `oid`, `orderType`, `start`, `end`. orderType enum: `Limit`, `Stop Limit`, `Stop Market`, `Take Profit Limit`, `Take Profit Market`. Default ordering returns the oldest open orders first — pages of GTC limits and triggers from 2023 and 2024 that have never been filled. To get fresh order flow only, pass `start` set to a recent ISO 8601 timestamp (e.g. 24 hours ago). The `start` filter applies to each order's `timestamp` (placed-at time), not to `snapshotTs`.

**GET /orders/5m-snapshots/{snapshotTime}** — Historical snapshot at a specific time. Params: `snapshotTime` (path, must be 5-min boundary, after floor date), `coin`, `limit`, `nextCursor`, `address`, `oid`, `start`, `end`, `orderType`.

**GET /orders/5m-snapshots/latest-snapshot-timestamp** — Returns the most recent available snapshot timestamp.

**GET /orders/5m-snapshots/{snapshotTime}/download** — Download link for a specific 5-minute order snapshot. Params: `snapshotTime` (path, ISO 8601, must be 5-min boundary, after floor date). Returns presigned download URL.

**GET /orders/5m-snapshots/coins/{coin}/download** — Download all order snapshots for a coin as a file.

### Liquidation Risk

**GET /{segmentId}/assets/liquidation-risk** — Per-asset liquidation risk for a specific cohort. Params: `segmentId` (path), `offset`, `limit`. Returns risk scores, at-risk OI, directional skew.

**GET /positions/heatmap** — Per-coin per-cohort positioning across the entire exchange. Returns one entry per coin (~335 coins as of 2026-05) with a `segments` array of 16 rows (one per cohort) containing `segmentId`, `totalValue`, `totalLongValue`, `totalShortValue`, `count`, `countLong`, `countShort`, and `bias`. The per-cohort `bias` is a long-fraction ratio bounded `[0, 1]` (formula: `totalLongValue / (totalLongValue + totalShortValue)`, `0.5 = neutral`, `> 0.5 = net long`, `< 0.5 = net short`). This is per-coin per-cohort positioning — different mathematical quantity and different scale from the signed exchange-wide bias returned by `/segments/{id}/bias-history`. Params: `openedWithin` (enum: `24h`, `7d`, `30d`, `all`; default: `all`). Current snapshot only, no history. Response is ~930 KB unfiltered, which can exceed response size limits in some environments (e.g. ChatGPT Custom GPT Actions); if so, use `/position-metrics/coin/{coin}/segment/{segmentId}` per cohort as a fallback and compute `bias = totalPositionValueLong / totalPositionValue` to get the equivalent per-cohort number. The `coin` query parameter is silently ignored — filter client-side after fetching.

### Leaderboards

**GET /leaderboards/perp-pnl** — Top traders by perp PnL. Params: `rankBy`, `limit`, `offset`, `order`, `orderBy`.

**GET /leaderboards/all-pnl** — Top traders by all PnL (perps + spot + vaults). Broader than perp-only leaderboard. Params: `rankBy` (required, enum: `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay`), `order` (required, `asc`/`desc`), `orderBy` (required, same enum as rankBy), `limit`, `offset`. Returns totalCount, sumPnl, assetsDistribution, and full trader data.

**GET /leaderboards/perp-pnl/{period}/download** — Download leaderboard data for a given period. Params: `period` (path, enum: `all`, `30d`, `7d`, `24h`).

### Fills

**GET /fills** — Trade executions. Params: `start` (required), `end` (same day), `coin` (array, e.g. `coin[]=BTC`), `limit`, `nextCursor`, `address`, `builder`, `side` (enum: `A` = sell/ask, `B` = buy/bid). 24hr max window. Historical from July 2025.

### Closed Trades

HyperTracker reconstructs full closed trades from raw Hyperliquid fills. History goes back to July 2025.

**GET /closed-trades** — Closed trades for a wallet. Params: `address` (required), `startTime`, `endTime`, `limit`, `nextCursor`. Default time range: last 7 days when both omitted. **Param naming quirk:** uses `startTime`/`endTime` (NOT `start`/`end` like other historical endpoints).

**GET /closed-trades/summary** — Aggregate summary for a wallet. Params: `address` (required). Returns `totalTrades`, `wins`, `losses`, `longTrades`, `shortTrades`, `avgDuration` (milliseconds), `updatedAt`. Win rate = `wins / totalTrades`.

**GET /closed-trades/{hash}** — A specific closed trade by hash. Params: `hash` (required).

**GET /closed-trades/{hash}/fills** — Underlying fills for a specific closed trade. Params: `hash` (required), `startTime`, `endTime`, `limit`, `nextCursor`.

### Volume Metrics

**GET /metrics/perp-volume** — Aggregate volume metrics. Params: `start` (required), `end`, `limit`, `nextCursor`.

### Wallets

**GET /wallets** — Tracked wallets. Params: `offset`, `limit`, `order`, `orderBy`, `segmentIds`, `hasOpenPositions`, `address` (filter by individual wallet address).

### $HYPE Token

**GET /hype/holders** — HYPE token holders with balances, staking, and comparisons. Params: `offset`, `limit` (max 500), `order`, `orderBy`, `rankBy`, `rankOrder`.

### Global State

**GET /state/summary** — Exchange snapshot: total/active traders, aggregate OI, segment distribution. No parameters. **Note:** This endpoint may not yet be available on all environments.

### Builders

**GET /builders/list/timeframe/{timeframe}** — Full list of all builders on Hyperliquid for a given timeframe, ordered by revenue (descending). Params: `timeframe` (path, enum: `24h`, `7d`, `30d`, `all`).

**GET /builders/{builder}/profile** — Comprehensive profile for a builder address. Returns identity, revenues, fee rates, and a full breakdown of analytics across 24h/7d/30d/all-time timeframes. Params: `builder` (path).

**GET /builders/all-time-revenue** — All-time revenue, daily revenue, and user statistics for builders. Returns columnar data: `["revenue", "timestamp", "countUsers"]`.

**GET /builders/{builder}/fills** — Trade fills attributed to a builder code. Params: `builder` (path), `start` (required), `end`, `coin`, `limit`, `nextCursor`, `address`, `fillType` (enum: `perp`, `spot`), `side` (enum: `A` = sell/ask, `B` = buy/bid).

**GET /builders/{builder}/users** — Users attributed to a builder code. Params: `builder` (path), `offset`, `limit`, `order`, `orderBy`, `period`.

### Per-Asset Segment Metrics

**GET /perps/coin/{coin}/segment-metrics** — Metrics for a specific coin broken down by each segment. Params: `coin` (path).

### Address Management

Manage your tracked address list. Useful for building custom watchlists and alert pipelines.

**GET /addresses** — List your tracked addresses. Params: `offset`, `limit` (default: 100), `addresses` (array, filter by specific addresses).

**POST /addresses/bulk** — Add addresses to your list. Body: `{ "addresses": ["0x...", "0x..."] }`.

**DELETE /addresses/bulk** — Remove addresses from your list. Body: `{ "addresses": ["0x...", "0x..."] }`.

**PUT /addresses/sync** — Replace your entire address list. Body: `{ "addresses": ["0x...", "0x..."] }`.

### Hyperliquid Info Proxy

**POST /info** — Proxy to Hyperliquid's `/info` API through HyperTracker. Body: `{ "type": "<infoType>" }` with optional `user` (address), `dex`, `builder`. Supported types include: `meta`, `spotMeta`, `clearinghouseState`, `spotClearinghouseState`, `exchangeStatus`, `liquidatable`, `openOrders`, `frontendOpenOrders`, `userFees`, `userRateLimit`, `subAccounts`, and more.

### System Status

**GET /hypertracker/state/status** — HyperTracker system state and data freshness.

### File Exports

**GET /exports/{file}** — Download a general export file. Params: `file` (path, enum: `segments-bias-charts-data-24h`, `total-wallets-equity-chart-data`).

**GET /exports/coins/{coin}/{file}** — Download a coin-specific export file. Params: `coin` (path), `file` (path, enum: `segment-metrics`, `position-metrics`, `position-breakdown-by-size`, `position-breakdown-by-cohort`, `liquidation-heatmap`).

---

## Response Examples

### /segments/{segmentId}/bias-history
```json
{
  "segment": {"id": 9, "name": "Smart Money", "category": "pnl", "criteria": {"minPnl": 100000, "maxPnl": 1000000}},
  "nextCursor": null,
  "positionRecencyTimeframe": "all",
  "start": "2026-03-03T08:10:00.099Z",
  "end": "2026-03-04T08:10:00.099Z",
  "pageStart": "2026-03-04T08:10:00.075Z",
  "pageEnd": "2026-03-03T08:10:00.388Z",
  "historySnapshotStructure": ["timestamp", "bias", "exposureRatio", "openValue", "openLongValue", "openShortValue", "activePerpEquity"],
  "history": [
    ["2026-03-04T08:10:00.075Z", 0.81, 2.95, 169578077.10, 108075482.73, 61502594.37, 57458083.37],
    ["2026-03-04T06:10:00.019Z", 0.91, 3.02, 173871275.29, 113170965.45, 60700309.84, 57517772.99]
  ]
}
```
Returns data for the requested segment. The `history` field is an array of arrays, with column order defined by `historySnapshotStructure`. Bias is signed and exchange-wide (positive = net long, negative = net short), with magnitude that factors in exposure ratio — different scale from per-coin `bias` in `/positions/heatmap`. Call once per segment ID to get all 16 cohorts.

### /{segmentId}/assets/liquidation-risk
```json
{
  "totalCount": 297,
  "items": [
    {"coin": "BTC", "totalValue": 287062584.45, "riskValue": 50791.19, "percentRisk": 49.06}
  ]
}
```

### /orders/5m-snapshots/latest
```json
{
  "orders": [
    {
      "height": 922290820,
      "address": "0xdef1...",
      "oid": 756322353,
      "coin": "BTC",
      "side": "B",
      "limitPx": 21500,
      "sz": 0.00465,
      "timestamp": "2023-07-18T10:30:51.626Z",
      "triggerCondition": "N/A",
      "isTrigger": false,
      "triggerPx": 0,
      "children": [],
      "isPositionTpsl": false,
      "reduceOnly": false,
      "orderType": "Limit",
      "origSz": 0,
      "tif": "",
      "cloid": "",
      "status": "open",
      "builder": "",
      "builderFee": 0,
      "untriggered": false,
      "snapshotTs": "2026-03-13T09:40:00.000Z"
    }
  ],
  "nextCursor": "eyJ..."
}
```

### /positions/coins
```json
[
  {"coin": "BTC", "totalValue": 2107846156.36, "totalValueLong": 1053923078.18, "totalValueShort": 1053923078.18, "count": 29758, "countLong": 16623, "countShort": 13135},
  {"coin": "ETH", "totalValue": 1148466271.07, "totalValueLong": 574233135.54, "totalValueShort": 574233135.54, "count": 14930, "countLong": 8666, "countShort": 6264}
]
```
Quick market-wide snapshot: total long/short values and position counts per coin.

### /leaderboards/all-pnl
```json
{
  "totalCount": 150000,
  "sumPnl": 45230000.50,
  "assetsDistribution": [...],
  "data": [
    {"address": "0xabc1...", "age": 365, "totalValue": 5200000.00, "stableValue": 1200000.00, "topHolding": "BTC", "pnlAllTime": 15230000.50, "pnlMonth": 1230000.00, "pnlWeek": 450000.00, "pnlDay": 85000.00, "rank": 1, "profile": {...}}
  ]
}
```
Broader than the perp-only leaderboard. Includes perps + spot + vaults PnL.

### /builders/all-time-revenue
```json
{
  "columns": ["revenue", "timestamp", "countUsers"],
  "data": [
    [1250.50, "2026-03-30T00:00:00.000Z", 342],
    [1180.25, "2026-03-29T00:00:00.000Z", 328]
  ]
}
```
Daily revenue and user counts for all builders over time.

### /closed-trades
```json
{
  "trades": [
    {
      "address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
      "hash": "bIUSUWzlZp01EToRyouN4yL9hPYAAAAAAN7aAQAAAZ2TOTDU",
      "id": "14604801",
      "side": "long",
      "coin": "ETH",
      "avgEntry": 2012.115,
      "avgExit": 2373.060,
      "duration": 5594052669,
      "openTime": "2026-02-10T04:23:59.383Z",
      "closeTime": "2026-04-15T22:18:12.052Z",
      "partial": false,
      "totalSize": 50000.0059,
      "totalUsd": 100605773.22,
      "realizedPnlUsd": 18596486.52,
      "countFills": 12080,
      "fee": 86246.79,
      "feeUsd": 86246.79,
      "fundingUsd": -635458.53
    }
  ],
  "nextCursor": "eyJjbG9zZVRpbWUiOjE3NzYyOTE0OTIwNTIsImlkIjoiMTQ2MDQ4MDEifQ..."
}
```
`duration` is in milliseconds. `side` is `"long"` or `"short"`. `partial` indicates whether a trade was partially closed. Use `hash` to fetch the trade detail or its fills via `/closed-trades/{hash}` and `/closed-trades/{hash}/fills`. Note: `id` is returned as a string in the list endpoint but as a number in the single-trade endpoint (`/closed-trades/{hash}`).

### /closed-trades/summary
```json
{
  "address": "0xa5b0edf6b55128e0ddae8e51ac538c3188401d41",
  "totalTrades": 8,
  "wins": 7,
  "losses": 1,
  "avgDuration": 1913858487,
  "longTrades": 7,
  "shortTrades": 1,
  "updatedAt": "2026-04-20T09:00:27.070Z"
}
```
Win rate is `wins / totalTrades`. `avgDuration` is in milliseconds. `updatedAt` is `null` for wallets with no closed trades yet.

### Paginated responses
Paginated endpoints return results in a named array with a `nextCursor` field. The array key varies by endpoint (`positions`, `fills`, `orders`, `items`, etc.).
```json
{
  "positions": [...],
  "nextCursor": "eyJsYXN0SWQiOiAxMjM0NX0="
}
```
Pass the `nextCursor` value as the `nextCursor` query parameter on the next request to get the next page. When `nextCursor` is `null`, you've reached the end.

---

## Rate Limits

| Tier | Price | Requests | Rate Limit |
|------|-------|----------|------------|
| Free | $0 | 100/day | — |
| Pulse | $179/mo | 50,000/mo | 60/min |
| Surge | $399/mo | 150,000/mo | 100/min |
| Flow | $799/mo | 400,000/mo | 200/min |
| Stream | $1,999/mo | 2,000,000/mo | 500/min |

**Note:** Some endpoints may support up to 200 requests/min. The rate limit counter on the API dashboard may not reflect per-endpoint limits.

---

## Code Patterns

### Python: Auth + Request
```python
import requests

headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
response = requests.get(
    "https://ht-api.coinmarketman.com/api/external/segments/9/bias-history",
    headers=headers
)
data = response.json()
```

### JavaScript: Auth + Request
```javascript
const response = await fetch(
  "https://ht-api.coinmarketman.com/api/external/segments/9/bias-history",
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
all_positions = []
while True:
    params = {"start": start, "end": end, "coin": "BTC"}
    if cursor:
        params["nextCursor"] = cursor
    resp = requests.get(url + "/positions", headers=headers, params=params).json()
    all_positions.extend(resp["positions"])
    cursor = resp.get("nextCursor")
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
        "coin[]": "BTC"
    }
    response = requests.get(url + "/fills", headers=headers, params=params)
```

### 5-Minute Boundary Alignment
```python
def align_to_5min(dt):
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
```

### Reverse Lookup: Match a PnL share card to wallets

A Hyperliquid PnL share card surfaces coin, side, leverage, entry price, mark price, and ROI. Reverse-lookup candidates like this:

```python
def find_positions_matching_card(coin, side, leverage, entry_price,
                                  entry_tolerance=0.05, start="2026-01-01T00:00:00.000Z"):
    matches = []
    cursor = None
    while True:
        params = {"coin": coin, "open": True, "start": start, "limit": 500}
        if cursor: params["nextCursor"] = cursor
        r = requests.get(f"{BASE}/positions", headers=HEADERS, params=params).json()
        for p in r["positions"]:
            # side is lowercase string: "long" or "short"
            if p["side"] != side.lower(): continue
            lev = float(p.get("crossLeverage") or p.get("isolatedLeverage") or 0)
            if abs(lev - leverage) > 0.5: continue
            if abs(float(p["entryPrice"]) - entry_price) > entry_tolerance: continue
            matches.append(p)
        cursor = r.get("nextCursor")
        if not cursor: break
    return matches

# Look up matched wallets for cohort context
def lookup_wallet(address):
    r = requests.get(f"{BASE}/wallets", headers=HEADERS, params={"address": address}).json()
    return r["items"][0] if r.get("items") else None
    # wallet["segments"] is an array of 2 IDs: one size cohort (1-7, 16), one PnL cohort (8-15)
```

**Match dimensions available on each position:** `side` (string: `"long"` or `"short"`), `crossLeverage`/`isolatedLeverage`, `entryPrice`, `size`, `openTime`, `unrealizedPnl`, `profile.segments` (array of 2 cohort IDs — one size-based, one PnL-based; see Cohort Segments table).

**ROI from a card (short):** `(entry - mark) / entry * leverage * 100`. Long: flip the numerator. Use this to sanity-check a candidate, not to match on, since the card's mark price is frozen at share time.

**Tolerances worth trying:** 0.05 (tight, Hyperliquid cards round to 2dp), 0.5 (loose, catches rounding), 1.0 (very loose, last resort).

**Disambiguating multiple matches:** smallest `size` is often the share-card author (retail flex pattern), but not guaranteed. Consider surfacing all matches with size and open time rather than auto-picking. Use the card's `markPrice` as a tiebreaker: the candidate whose current API `markPrice` is closest to the card's mark is the strongest match, since mark prices vary by position (different mark sources at different timestamps).

**Shortcut: cohort data is on the position itself.** Each position includes `profile.segments` (array of 2 cohort IDs). You can skip the `/wallets` lookup if you only need cohort classification. Use `/wallets` when you also want `totalEquity`, `perpPnl`, or `displayName`.

---

## Example Prompts

### For Vibe Coders (no dev experience needed)

**"I want to see what smart money is doing right now. Build me something simple."**
Endpoints: `/segments/{segmentId}/bias-history`, `/segments`
Fetch bias data, display each cohort with a simple long/short indicator. Color-code green for long, red for short. One-page HTML.

**"Show me which coins are about to get liquidated"**
Endpoints: `/{segmentId}/assets/liquidation-risk`
Fetch risk data, sort by score, display as a simple ranked list with risk level colors.

**"What should I be watching today? Rank coins by where the most interesting activity is happening."**
Endpoints: `/segments/{segmentId}/bias-history`, `/position-metrics/coin/{coin}/segment/9`, `/orders/5m-snapshots/latest`, `/{segmentId}/assets/liquidation-risk`
Score each coin by: smart money conviction, order flow clustering, liquidation proximity. Rank and surface top 5 with a one-line reason for each.

**"Am I about to get liquidated? Check if my position is safe."**
Endpoints: `/{segmentId}/assets/liquidation-risk`, `/positions/heatmap`
User provides coin and direction. Fetch liquidation risk for that coin, show how close current price is to liquidation clusters, and give a plain-English safety rating.

**"Show me a fear/greed gauge for Hyperliquid right now"**
Endpoints: `/segments/{segmentId}/bias-history`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`
Composite score from cohort sentiment, liquidation proximity, and OI trends. Display as a simple gauge with color-coded zones. One-page HTML.

**"Show me what whales are doing vs retail on BTC"**
Endpoints: `/position-metrics/coin/BTC/segment/9`, `/position-metrics/coin/BTC/segment/7`, `/position-metrics/coin/BTC/segment/16`
Compare Leviathan (7) and Smart Money (9) positioning against Shrimp (16). Show who's long, who's short, and whether they agree.

### Dashboards

**"Build a Hyperliquid market dashboard with cohort positioning, order flow, and liquidation risk"**
Endpoints: `/segments/{segmentId}/bias-history`, `/orders/5m-snapshots/latest`, `/{segmentId}/assets/liquidation-risk`, `/position-metrics/coin/{coin}`

**"Track my positions and compare them against smart money"**
Endpoints: `/wallets`, `/position-metrics/coin/{coin}/segment/9`, `/segments/{segmentId}/bias-history`

### Trading Signals

**"Alert me when two cohorts diverge on any coin"**
Endpoints: `/segments/{segmentId}/bias-history`, `/position-metrics/coin/{coin}/segment/{segmentId}`
Poll bias data, detect when cohorts split (e.g., Smart Money long, Exit Liquidity short). Pull coin-level metrics to find which coins drive the divergence.

**"Mean-reversion alert when a cohort's bias hits an extreme and reverses"**
Endpoints: `/segments/{segmentId}/bias-history`
Track bias time series, define extremes (> 0.7 or < -0.7), fire alert when pullback starts.

**"Contrarian signal: go opposite of Exit Liquidity and Giga-Rekt"**
Endpoints: `/segments/{segmentId}/bias-history`, `/position-metrics/coin/{coin}/segment/12`, `/position-metrics/coin/{coin}/segment/15`
When Exit Liquidity (12) and Giga-Rekt (15) are heavily positioned one way, flag the opposite direction as a potential trade.

### Order Flow

**"Map BTC orders by price level and type. Show where stops, TPs, and limits cluster."**
Endpoints: `/orders/5m-snapshots/latest?coin=BTC`
Group orders into price buckets, count by type, visualize as a bar chart relative to current price.

### Liquidation

**"Liquidation risk monitor across all coins, ranked and auto-refreshing"**
Endpoints: `/{segmentId}/assets/liquidation-risk`, `/position-metrics/coin/{coin}`
Rank by risk score, pull OI for top 5 riskiest, color-code severity, refresh every 5 minutes.

### Leaderboard

**"Watchlist from today's top 25 traders. Alert me when they open new positions."**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlDay&limit=25`, `/wallets`
Fetch leaderboard, look up wallets, poll for changes every 5 minutes.

### Closed Trades

**"Pull this wallet's full closed trade history and compute their win rate and average hold."**
Endpoints: `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`
Hit `/summary` first for `wins`, `losses`, `totalTrades`, `avgDuration`. Use `/closed-trades` to paginate through individual trades when you need per-trade breakdown (entry, exit, realized PnL, fills count). Default window is 7 days. Use `startTime`/`endTime` (not `start`/`end`) to widen.

**"Show me the most profitable closed trades on Hyperliquid this month, by wallet."**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&limit=25`, `/closed-trades/summary?address={address}` (per leader), `/closed-trades?address={address}&startTime=...`
Top monthly leaderboard gives candidates; pull each one's summary, then their largest trades by `realizedPnlUsd` for the month.

**"Build a copy-trading feed from a wallet's closed trades."**
Endpoints: `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`
Poll closed-trades for a watched wallet on a cadence (every few minutes). When a new trade hash appears, optionally pull `/closed-trades/{hash}/fills` for the underlying execution detail (slippage, partial fills, builder).

### Reverse Lookup

**"Whose wallet is behind this Hyperliquid PnL share card?" / "Identify this trader" / "Who opened this position?"**
Endpoints: `/positions?coin={coin}&open=true`, `/wallets?address={address}`
A Hyperliquid share card or screenshot exposes: coin, side, leverage, entryPrice, markPrice, ROI%. If the user provides an image, extract these values from the card first. The first four are matchable against open positions; the mark on the card is frozen in time so re-derive the card's implied ROI from entry/mark instead of matching on mark directly. Pull open positions for the coin, filter by side and leverage (±0.5), rank candidates by entry-price proximity. Tighten to an exact entry match first; widen the tolerance if zero hits. Multiple matches are normal — share cards aren't unique. Look up the matched address via `GET /wallets?address={address}` for cohort segments, total equity, and PnL context.

**"I only have the coin, side, and ROI — no entry price"**
Endpoints: `/positions?coin={coin}&open=true`, `/wallets?address={address}`
If entry price is missing, filter by coin + side + leverage only, then rank candidates by how closely their computed ROI matches the card's ROI. Short ROI: `(entry - mark) / entry * leverage * 100`. Long ROI: `(mark - entry) / entry * leverage * 100`. Current mark price from the API may differ from the card's mark, so this is a fuzzy match — present multiple candidates rather than picking one.

**"The card doesn't match any currently open positions"**
Endpoints: `/positions?coin={coin}&open=false&start=...`, `/coin/{coin}/open-positions/history`
Card may represent a closed trade or an older snapshot. Query historical positions with `open=false` across a wider time window, or pull a historical open-positions snapshot from `/coin/{coin}/open-positions/history` and match against that instead. Entry price is still the strongest match dimension.

**"Which cohort is behind a given share card?"**
Endpoints: `/positions?coin={coin}&open=true`, `/wallets?address={address}`
Match the card to candidate addresses as above, then look up each wallet via `/wallets?address={address}`. Each wallet has a `segments` array containing two IDs: one size-based cohort (IDs 1-7, 16) and one PnL-based cohort (IDs 8-15). Cross-reference with the Cohort Segments table above. If all candidates share a cohort, that's the answer. If they don't, the card is cohort-ambiguous — surface the distribution instead of picking one.

**"Biggest money behind this trade idea, not the specific share card"**
Endpoints: `/positions?coin={coin}&open=true`, `/position-metrics/coin/{coin}/segment/{segment}`
Reframe the question: instead of finding the card's author, list all open positions matching the card's direction and leverage band, sorted by position size. Add cohort breakdown to show which segments are positioned this way.

### Backtesting

**"Backtest: how did Smart Money positioning on BTC predict price moves over the last 4 weeks?"**
Endpoints: `/position-metrics/coin/BTC/segment/9`
Use per-coin cohort metrics (available ~4 weeks back). Correlate Smart Money net exposure changes with subsequent BTC price movement. Report hit rate and average return per signal. Note: cohort bias (`/segments/{segmentId}/bias-history`) only has 12 hours of history and cannot be used for multi-day backtests.

**"Compare all 8 PnL cohorts as predictors of BTC direction over the last month"**
Endpoints: `/position-metrics/coin/BTC/segment/{segmentId}` (for each ID 8-15)
For each cohort, pull 4 weeks of positioning data. Correlate exposure changes with subsequent price moves. Rank cohorts by predictive accuracy.

### Market Regime

**"Is the market in risk-on or risk-off mode right now based on cohort behavior?"**
Endpoints: `/segments/{segmentId}/bias-history`, `/state/summary`, `/{segmentId}/assets/liquidation-risk`
Risk-on signals: Smart Money and Money Printer net long, low liquidation risk, rising OI. Risk-off: defensive cohorts reducing exposure, high liq risk, falling OI. Classify current regime and show supporting data.

**"Daily market regime report: combine cohort bias, OI, and liquidation risk into one summary"**
Endpoints: `/segments/{segmentId}/bias-history`, `/position-metrics/general`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`
Pull all four data sources. Classify as risk-on, risk-off, or neutral. Show the 3 strongest supporting signals and 1 contradicting signal. Output as a clean summary.

### Multi-Endpoint

**"Coin screener ranking assets by smart money conviction, order flow health, and liquidation risk"**
Endpoints: `/position-metrics/coin/{coin}/segment/9`, `/orders/5m-snapshots/latest`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`

### Use Case Recipes

Larger end-to-end workflows. Each lists the exact endpoints to call and how to combine them. All endpoints verified against prod.

**"Give me a 60-second morning market brief on Hyperliquid"**
Endpoints: `/positions/heatmap`, `/position-metrics/general?start={24h ago}&end={now}`, `/leaderboards/perp-pnl?rankBy=pnlDay&limit=25`, `/orders/5m-snapshots/latest?coin=BTC&start={24h ago}`
Pull per-cohort positioning from the heatmap (which cohorts lean long vs short on the major coins), market health from `/position-metrics/general` (long/short ratio, OI, position count), today's top performers from the leaderboard, and BTC stop/TP clusters from the order snapshot (pass `start` to avoid stale 2023-2024 orders). Summarize in plain English: market mood, what smart money cohorts are doing, what today's winners are positioned in, and where BTC order-flow tension is building.

**"What are today's top-earning traders doing differently from everyone else?"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlDay&limit=100`, `/positions/heatmap`, `/position-metrics/general?start={ISO}&end={now}`
Pull the top 100 daily PnL wallets. Compute what fraction are net profitable and the median daily PnL. Compare their weekly vs monthly ranks to separate consistent winners from one-day luck. Cross-reference the heatmap to see whether the strong cohorts (Money Printer 8, Smart Money 9) are aligned with or against where the leaderboard is positioned. `rankBy` options: `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay`; `limit` must be 25, 50, or 100.

**"Find the most crowded trade on Hyperliquid right now"**
Endpoints: `/position-metrics/coin/{coin}/segment/{segmentId}?start={1h ago}&end={now}` (per coin per cohort), or `/positions/heatmap` for a single bulk pull
For each coin + cohort, compute long fraction (`totalPositionValueLong / totalPositionValue`). Flag a cohort as crowded when long fraction is > 0.8 or < 0.2. Weight by `totalPositionValue` so a crowded large position counts more than a small one. Score each coin by how many cohorts are crowded on the same side. The heatmap (`/positions/heatmap`) returns all coins and cohorts in one call with a pre-computed per-cohort `bias` (0-1 long fraction), so it is the faster path. PnL cohorts: 8 Money Printer, 9 Smart Money, 10 Consistent Grinder, 11 Humble Earner, 12 Exit Liquidity, 13 Semi-Rekt, 14 Full Rekt, 15 Giga-Rekt. Flag disagreements: when Smart Money leans one way but several weaker cohorts lean the other, that divergence is the higher-conviction signal.

**"Build a personal portfolio auditor for my wallet"**
Endpoints: `/wallets?address={address}`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`
Pull wallet equity, exposure, and cohort segments from `/wallets`. Pull win rate, profit factor, expectancy, and the per-coin breakdown from `/closed-trades/summary`. Page through individual closed trades with `/closed-trades` (uses `startTime`/`endTime`, not `start`/`end`) and drill into execution quality per trade with `/closed-trades/{hash}/fills`. Render win-rate and profit-factor views from the summary; use the `coins[]` breakdown to show which assets the wallet is actually good at.

**"Alpha screener: find and vet top traders before following them"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&limit=100`, `/wallets?address={address}`, `/positions?address={address}&start={ISO}&end={now}`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`
Discover candidates from the monthly leaderboard. For each, pull `/wallets` for equity and liquidation proximity, `/positions` for current active bias/size/leverage (note: `address` is an array param), and `/closed-trades/summary` for the long-term track record (win rate, profit factor, per-coin specialization). Drill into specific open/close pairs with `/closed-trades`. Rank survivors by per-coin `expectancy` or `profitFactor` to find genuine specialists.

**"Macro sentiment and smart money cohort radar"**
Endpoints: `/segments`, `/positions/heatmap`, `/position-metrics/general?start={ISO}&end={now}`, `/position-metrics/coin/{coin}?start={ISO}&end={now}`, `/position-metrics/coin/{coin}/segment/{segmentId}?start={ISO}&end={now}`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`
Pull cohort definitions from `/segments` (the data legend). Pull the global directional grid from `/positions/heatmap`. Layer in market-wide health from `/position-metrics/general` and per-coin concentration from `/position-metrics/coin/{coin}`. Track 15-minute trend shifts on divergent assets via `/position-metrics/coin/{coin}/segment/{segmentId}`. Add liquidation pressure from `/{segmentId}/assets/liquidation-risk` and network context from `/state/summary`. Build a macro indicator that isolates pairs where smart money is fading the retail crowd.

**"Systematic exposure analysis and backtesting pipeline"**
Endpoints: `/state/summary`, `/positions?start={ISO}&end={now}`, `/position-metrics/general?start={ISO}&end={now}`, `/position-metrics/coin/{coin}?start={ISO}&end={now}`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`, `/exports/coins/{coin}/liquidation-heatmap`
Check data freshness with `/state/summary`. Pull current and historical positioning with `/positions` (paginate with `nextCursor`). Pull macro OI/position profiles from `/position-metrics/general` and per-coin exposure from `/position-metrics/coin/{coin}`. Sync cohort performance baselines from `/closed-trades/summary`, reconstruct open/close pairs from `/closed-trades`, and model entry/exit slippage from `/closed-trades/{hash}/fills`. Download price-bin liquidation structures from `/exports/coins/{coin}/liquidation-heatmap`. Note: positions history goes back to April 2025; per-coin cohort metrics ~4 weeks.

**"Structural order flow and liquidation cluster mapper"**
Endpoints: `/orders/5m-snapshots/latest-snapshot-timestamp`, `/orders/5m-snapshots/latest`, `/orders/5m-snapshots/{snapshotTime}`, `/orders/5m-snapshots/coins/{coin}/download`, `/{segmentId}/assets/liquidation-risk`, `/positions/heatmap`, `/builders/all-time-revenue`
Poll `/orders/5m-snapshots/latest-snapshot-timestamp` to detect new snapshot intervals, then ingest the resting order book from `/orders/5m-snapshots/latest` (always pass `start` to filter zombie orders). Pull historical snapshots by timestamp, or bulk-export a coin's snapshots via `/orders/5m-snapshots/coins/{coin}/download`. Map liquidation pressure with `/{segmentId}/assets/liquidation-risk` and the position heatmap. Audit builder/frontend routing volume with `/builders/all-time-revenue`.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 401 Unauthorized | Check JWT token is valid, included as `Bearer <token>` |
| Empty fills | `start` and `end` must be within the same 24-hour period |
| Empty order snapshots | Timestamp must be after `2026-01-19T11:05:00Z` and on a 5-minute boundary |
| Dates not working | Use ISO 8601: `2026-02-25T00:00:00.000Z`. Not epoch milliseconds. |
| Leaderboard error | `rankBy` must be `pnlAllTime`/`pnlMonth`/`pnlWeek`/`pnlDay`. `limit` must be 25/50/100. |
| Empty cohort history | `/segments/{segmentId}/bias-history` has limited history. Use `/position-metrics/coin/{coin}/segment/{id}` for longer lookbacks (up to ~4 weeks). |
| Stale data | Most data refreshes every ~5 minutes. State/summary updates may take up to 15-17 minutes. Wait for next cycle. |
| No more pages | `nextCursor` is `null` in the response. You've fetched everything. |
| Reverse lookup: no matches | Widen `entry_tolerance` (try 0.5 then 1.0). If still empty, the position may be closed — retry with `open=false`. For very old cards, use `/coin/{coin}/open-positions/history` for historical snapshots. |
| Reverse lookup: too many matches | Narrow `entry_tolerance` to 0.05. Use ROI as a sanity check: compute each candidate's ROI and compare to the card's ROI. Candidates whose current `markPrice` is close to the card's mark are strongest. |
| Closed trades empty | Default time range is 7 days when neither `startTime` nor `endTime` is set. Widen the window or set both. **Param naming gotcha:** closed-trades uses `startTime`/`endTime`, not `start`/`end` like other historical endpoints. |

## Links

- Dashboard & API Key: https://app.coinmarketman.com/hypertracker/api-dashboard?utm_source=skill&utm_medium=ai&utm_campaign=skill-launch
- Docs: https://docs.coinmarketman.com
