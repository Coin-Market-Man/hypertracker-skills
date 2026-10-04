# HyperTracker API

Pre-computed intelligence layer for Hyperliquid perpetual futures. Cohort analytics, order flow, liquidation data, leaderboards, closed-trade analytics, builder analytics, and real-time and push delivery (WebSocket streams, server-side alerts, webhooks). Cohort, leaderboard and closed-trade datasets are computed by HyperTracker and are not available as ready-made outputs from the standard Hyperliquid API.

## Authentication

```
Authorization: Bearer <your_jwt_token>
```

Get your token: https://app.coinmarketman.com/hypertracker/api-dashboard?utm_source=skill&utm_medium=ai&utm_campaign=skill-launch

The same token works for the REST API, the WebSocket streams and the server-side alerts API.

## Base URL

```
https://ht-api.coinmarketman.com/api/external
```

All REST paths below are relative to this base URL. WebSocket streams use `wss://ws.hypertracker.io/connection/websocket` (see Infrastructure).

## Critical Rules

1. **Dates MUST be ISO 8601.** Example: `2026-02-25T00:00:00.000Z`. Never epoch milliseconds.
2. **Coins are case-sensitive strings.** Main-exchange perps are uppercase tickers: `"BTC"`, `"ETH"`, `"HYPE"`. No USDT suffix. HIP-3 markets (equities, commodities, indices) carry a lowercase dex prefix: `xyz:GOLD`, `xyz:SP500`. Pass them exactly as written; the colon does not need URL encoding. Wrong case (`btc`, `XYZ:GOLD`) returns an empty list, not an error. Position and cohort data cover the dexes listed by `/positions/coins`; some dexes (e.g. `cash:`) appear in fills and liquidations but return empty position data. Exception: `/perps/coin/{coin}/segment-metrics` uppercases the coin and only works for main-exchange coins.
3. **Lowercase wallet addresses.** `/wallets` and `/positions` match addresses case-sensitively: a checksummed or uppercase address returns an empty result. (`/closed-trades/summary`, `/fundings` and `/fills/liquidation` accept any case.)
4. **Boolean query params are lowercase strings.** Send `open=true`, not `open=True`. Python `requests` serializes `True` as `True`, which the API reads as false: `open=True` returns closed positions and `hasOpenPositions=True` returns wallets with no open positions. Pass `"true"`/`"false"` as strings.
5. **Some params must be arrays.** On `/fills` and `/builders/{builder}/fills`, `address` and `coin` must be sent as arrays: `address[]=0xabc...&coin[]=BTC`, or repeat the key (`address=0x1...&address=0x2...`). A single scalar `address=0x...` or `coin=BTC` returns 400 `"... must be an array"`. On `/positions`, repeat `address` for multiple wallets.
6. **`/fills` requires `address` (1 to 10 wallets) and a window inside one UTC calendar day.** There is no market-wide fill pull in REST. A window that crosses midnight UTC returns 400 `"End date must be within the same day as the start date"`. For exchange-wide fills use the WebSocket `rooms:fills` stream; for liquidations use `/fills/liquidation`.
7. **Closed trades and fundings use `startTime`/`endTime`, not `start`/`end`.** The window between them can be at most one month (400 `"endTime - startTime can not be longer then 1 month"` on closed trades, `"... cannot be longer than 1 month"` on fundings). `start`/`end` are silently ignored. The missing bound defaults to now (or now minus 7 days), so passing only a `startTime` more than a month back fails and passing only an `endTime` older than 7 days returns an empty list: set both. For longer history, loop over consecutive windows of 30 days or less.
8. **Paginate with `nextCursor`.** Pass the response's `nextCursor` back as the `nextCursor` query param. A param named `cursor` is silently ignored and returns page 1 forever. When `nextCursor` is `null` or absent, you have every page.
9. **Default page size varies by endpoint.** 100 for orders, closed trades, closed-trade fills, fundings and wallets; 500 for fills and liquidation fills; 1000 for positions and position metrics; 25 for the perp-PnL leaderboard; 100 for the all-PnL and biggest-positions leaderboards. Most endpoints cap `limit` at 1000; closed trades, fundings, wallets, liquidation risk and HYPE holders cap at 500; `/leaderboards/perp-pnl` accepts only 25, 50 or 100, while `/leaderboards/all-pnl` and `/leaderboards/biggest-positions` accept 1 to 100.
10. **Leaderboards: set `orderBy` to the same value as `rankBy`.** `orderBy` controls the sort and defaults to `pnlAllTime`; `rankBy` only controls the `rank` number. `?rankBy=pnlDay&limit=25` alone returns the all-time top, not today's. Use `?rankBy=pnlDay&orderBy=pnlDay&order=desc&limit=25`.
11. **Follow redirects and download immediately.** Several endpoints answer with a 302 to a pre-signed S3 file, or return a `downloadUrl` (CSV/JSON exports, snapshot summaries, builder lists). `requests` and `fetch` follow redirects by default; with curl use `-L`. Pre-signed links expire after 30 to 240 seconds (30 seconds for per-coin exports and `/segments/{id}/summary`). A 0-byte body usually means the redirect was not followed.
12. **Most data refreshes on each Hyperliquid state update (roughly every 15 to 30 minutes).** Order snapshots refresh every 5 minutes; see Data Freshness below. Polling faster than the cadence uses your usage allowance without returning new data.

---

## Data Freshness

| Data | Update cadence |
|------|----------------|
| Order snapshots (`/orders/5m-snapshots/*`) | Every 5 minutes |
| Exchange-wide position metrics (`/position-metrics/general`) | About every 10 minutes |
| State, positions, per-coin and per-cohort metrics, heatmap, open-position CSVs | Each state update, usually every 15 to 30 minutes. Check `GET /hypertracker/state/status` (`lastUpdate`, `nextUpdate`) or subscribe to the state webhook. |
| Cohort bias history (`/segments/{id}/bias-history`) | Stored every 2 hours by default (about every 30 minutes with `positionRecencyTimeframe=24h` and a `start`; a call without `start` is always 2-hourly) |
| Closed trades | About 10 seconds after a trade's final fill |
| WebSocket streams, server-side alerts | Real time |

Always read the `createdAt` (or snapshot timestamp) on each row instead of assuming the newest row is "now".

---

## Historical Data Availability

| Data | Available from |
|------|----------------|
| Positions (`/positions`) | April 4, 2025. Liquidation prices before September 2, 2025 are stored as static values. |
| Exchange-wide position metrics | May 2025 |
| Fills, closed trades, builder fills | July 2025 |
| Liquidation fills (`/fills/liquidation`) | July 27, 2025, queried in windows of up to 3 months |
| Fundings (`/fundings`) | September 27, 2025 |
| Cohort bias history | July 9, 2025. A call with no `start` returns the last ~60 days at 2-hour spacing; pass `start`/`end` for older ranges. |
| Per-coin cohort metrics (`/position-metrics/coin/{coin}/segment/{id}`) | February 19, 2026 (`positionRecencyTimeframe=all`); March 19, 2026 for `24h`/`7d`/`30d` |
| Open-position snapshot files (`/coin/{coin}/open-positions/history`) | March 25, 2026 |
| Order snapshots, paginated (`/orders/5m-snapshots/{snapshotTime}`) | Rolling 30-day window. Older timestamps return an empty list. |
| Heatmap, leaderboards, liquidation risk, wallet profiles | Current snapshot only |

---

## Cohort Segments

Every active wallet on Hyperliquid is classified into two cohorts at once: one by size (perp equity) and one by performance (all-time perp PnL). Active means non-zero perp volume in the last 30 days or an open position.

### Size-Based Cohorts (by Perp Equity)
| ID | Name | Perp Equity |
|----|------|-------------|
| 16 | Shrimp | $0 - $250 |
| 1 | Fish | $250 - $10K |
| 2 | Dolphin | $10K - $50K |
| 3 | Apex Predator | $50K - $100K |
| 4 | Small Whale | $100K - $500K |
| 5 | Whale | $500K - $1M |
| 6 | Tidal Whale | $1M - $5M |
| 7 | Leviathan | $5M+ |

### PnL-Based Cohorts (by All-Time Perp PnL)
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

All 16 cohorts use `/segment/{segmentId}`. Call `GET /segments` to confirm the latest ID mapping.

**Do not sum across both axes.** Every position belongs to one size cohort (1-7, 16) and one PnL cohort (8-15), so it appears in both. Summing all 16 rows of a per-coin breakdown doubles counts and notional. Sum within one axis only (IDs 8-15, or IDs 1-7 plus 16).

A separate `/position-size-bucket/{sizeBucketId}` endpoint (IDs 1-10) groups individual positions by their own size, independent of wallet cohorts.

Cohort membership moves as PnL and equity change. When you compare two snapshots, part of a cohort's change can come from wallets entering or leaving the cohort, not from trading.

---

## REST Endpoints

### Cohort Intelligence

**GET /segments**: All 16 cohort definitions with `id`, `name`, `category`, `criteria` and `emoji`. Call first to confirm segment IDs.

**GET /segments/{segmentId}/bias-history**: Bias history for one cohort, exchange-wide across all coins. Params: `segmentId` (path), `start`, `end`, `limit` (max 1000), `nextCursor`, `positionRecencyTimeframe` (`24h`, `7d`, `30d`, `all`; default `all`). `start` is required whenever `limit`, `end` or `nextCursor` is set, otherwise 400 `"'start' query param is required for 'end', 'nextCursor' and 'limit' query params"`. With no params it returns the last ~60 days at 2-hour spacing. The `history` field is an array of arrays whose column order is given by `historySnapshotStructure`: `[timestamp, bias, exposureRatio, openValue, openLongValue, openShortValue, activePerpEquity]`. Rows are newest first. `bias = (openLongValue - openShortValue) / activePerpEquity` (signed, positive = net long, can exceed 1 in magnitude); `exposureRatio = openValue / activePerpEquity`. This is a different scale from the per-coin `bias` in `/positions/heatmap`. Call once per segment ID to cover all cohorts.

**GET /segments/{segmentId}/summary**: Per-cohort snapshot of currently open positions. Params: `segmentId` (path), `positionAge` (`all`, `24h`, `7d`, `30d`; default `all`). Returns `segment`, `openPerpsSummary` (`perpBias`, `exposureRatio`, `countOpenPositions`, `countTradersInPosition`, `countTradersInProfit`, `totalValue`, `totalLongValue`, `totalActivePerpEquity`, `bySide`, `totalPerpEquity`, `countAssets`) and `summary` (`countTraders`, `countTradersInPosition`, `perpBias`, `positionValue`, `positionLongValue`, `positionShortValue`, `exposureRatio`, `activePerpEquity`, `perpEquity`). Served via redirect to a pre-signed file. `positionAge` is not validated: an unknown value redirects to a missing file (S3 404). The `24h`/`7d`/`30d` files omit `countTraders`, `perpEquity`, `totalPerpEquity` and `countAssets`.

**GET /position-metrics/coin/{coin}/segment/{segmentId}**: Per-coin, per-cohort time series. Works for all 16 segments and for HIP-3 coins (`xyz:GOLD`). Params: `coin`, `segmentId` (path), `start` (**required**), `end`, `limit`, `nextCursor`, `positionRecencyTimeframe` (`all`, `24h`, `7d`, `30d`; default `all`; counts only positions opened within that window at each snapshot). Returns `{metrics: [...]}`, newest first. Each row: `createdAt`, `coin`, `segmentId`, `positionCount`, `positionCountLong`, `totalPositionValue`, `totalPositionValueLong`, `totalPositionSize`, `totalPositionSizeLong`, `totalFunding`, `totalUnrealizedPnl`. Long fraction = `totalPositionValueLong / totalPositionValue` (equals the heatmap's per-cohort `bias`).

**GET /state/summary**: Exchange snapshot that powers the HyperTracker homepage: `countTraders`, `countActiveTraders`, `countTraders24HoursAgo`, `segments` (plus `segments24h`, `segments7d`, `segments30d`), `perpPositionsMetrics` (`count`, `openInterest`), `perpVolume` and 24-hours-ago comparisons. Current snapshot only. Served via redirect to a pre-signed file.

### Positions & Market Exposure

**GET /positions**: Positions with pre-computed cohort data. Params: `start` (**required**), `end`, `coin`, `segmentId`, `address` (repeat for multiple: `address=0x1...&address=0x2...`), `open` (`"true"`/`"false"`; omit for both), `limit` (default and max 1000), `nextCursor`. **`start` filters on each position's `openTime`**: a position opened before `start` is excluded even if it is still open. To get every currently open position, set `start` before the oldest position you care about (e.g. `2025-04-04T00:00:00.000Z`). Results are sorted by `openTime` ascending. Each position appears once, as one consolidated record (not a state-by-state history). Fields: `id`, `address`, `coin`, `dex`, `side` (`"long"`/`"short"`), `size`, `entryPrice`, `markPrice`, `midPrice`, `premiumPrice`, `positionValue`, `liquidationPrice`, `unrealizedPnl`, `funding`, `crossLeverage`, `isolatedLeverage`, `maxLeverage`, `assetMaxLeverage`, `szDecimals`, `openTime`, `closeTime` (`null` while open), `createdAt`, `updatedAt`, `profile` (`{address, segments}`, where `segments` holds the wallet's two cohort IDs). Positions are captured at state updates, so very short-lived positions can be missing: use `/closed-trades` for trade counts, win rate, hold time or realized PnL.

**GET /positions/coins**: Market-wide summary per coin: `totalValue`, `totalValueLong`, `totalValueShort`, `count`, `countLong`, `countShort`, sorted by `totalValue` desc. No params. `totalValueLong` equals `totalValueShort` at this level because every long has a matched short; use `countLong`/`countShort` for crowding and per-cohort data (`/positions/heatmap`) for directional notional. Also a quick way to list every coin, HIP-3 markets included.

**GET /positions/open/coin/{coin}**: Latest open-position snapshot for a coin as CSV (main exchange and HIP-3). 302 redirect to a pre-signed file. Columns: `id, address, coin, side, dex, size, value, entryPrice, unrealizedPnl, funding, liquidationPrice, liquidationProgress, crossLeverage, isolatedLeverage, openTime`, plus wallet columns prefixed `profile_` (`profile_totalEquity`, `profile_perpEquity`, `profile_countOpenPositions`, `profile_pnl`, `profile_balance`, `profile_perpPnlSegmentId`, `profile_sizeSegmentId`). Refreshed each state update. Large coins produce files over 10 MB.

**GET /coin/{coin}/open-positions/history**: Point-in-time open-position snapshot files for a coin. Params: `coin` (path), `start`, `end`, `nextCursor`. Each response holds **one** snapshot: `{coin, snapshot: {snapshotId, coin, stateVersion, rowCount, status, format, createdAt, completedAt, downloadUrl}, nextCursor}`. Returns the newest snapshot at or before `end`, then pages backward in time. `downloadUrl` expires after about 120 seconds. Earliest snapshot: March 25, 2026. For positions back to April 2025, use `GET /positions`.

**GET /position-metrics/general**: Exchange-level OI and position counts over time. Params: `start` (**required**), `end`, `limit`, `nextCursor`. Rows: `createdAt`, `count`, `countLong`, `countShort`, `openInterest`, `openInterestLong`, `openInterestShort`, `perpEquity`, `countInProfit`.

**GET /position-metrics/coin/{coin}**: Per-coin long/short breakdown over time (all cohorts combined). Params: `coin` (path), `start` (**required**), `end`, `limit`, `nextCursor`. Same row fields as the per-cohort endpoint without `segmentId`.

**GET /position-metrics/coin/{coin}/position-size-bucket/{sizeBucketId}**: Per-coin metrics by individual position size bucket (IDs 1-10, from under $1K to over $2.5M), independent of cohorts. Params: `coin`, `sizeBucketId` (path), `start` (**required**), `end`, `limit`, `nextCursor`.

**GET /perps/coin/{coin}/segment-metrics**: All 16 cohorts for one coin in a single call: `{coin, segments: [{segment, metrics: [...]}]}`. `metrics[0]` is the current snapshot; the following entries are 12-hour snapshots covering about 7 days. Rows carry no timestamp (`positionCount`, `positionCountLong`, `totalPositionValue`, `totalPositionValueLong`, `bias`); use `/exports/coins/{coin}/segment-metrics` when you need the times. Main-exchange coins only: the path coin is uppercased, so HIP-3 coins return 404 (`"XYZ:GOLD not found"`); use `/position-metrics/coin/{coin}/segment/{segmentId}` for them. Remember the two-axis rule above before summing.

### Position Heatmap

**GET /positions/heatmap**: Per-coin, per-cohort positioning across the whole exchange in one call. Params: `openedWithin` (`24h`, `7d`, `30d`, `all`; default `all`). Returns `{heatmap: [...]}` with one entry per coin (~330 coins): `coin`, `totalValue`, `totalLongValue`, `totalShortValue`, `count`, `countLong`, `countShort`, and a `segments` array with one row per cohort that holds the coin (up to 16; cohorts with no position are omitted). Each segment row has `segmentId`, `totalValue`, `totalLongValue`, `totalShortValue`, `count`, `countLong`, `countShort` and `bias`. Per-cohort `bias` is a long fraction in `[0, 1]`: `totalLongValue / (totalLongValue + totalShortValue)`, where `0.5` is neutral. Current snapshot only. The `coin` query param is ignored, so filter client-side. The response is close to 1 MB; if your environment caps response size (e.g. ChatGPT Custom GPT Actions), call `/position-metrics/coin/{coin}/segment/{segmentId}` per cohort with a 1-hour window instead and compute `totalPositionValueLong / totalPositionValue`.

### Order Flow

**GET /orders/5m-snapshots/latest**: The most recent 5-minute snapshot of every open order. Params: `coin`, `address`, `oid`, `orderType`, `start`, `end`, `limit` (default 100, max 1000), `nextCursor`. `orderType` enum: `Limit`, `Stop Limit`, `Stop Market`, `Take Profit Limit`, `Take Profit Market` (URL-encode the spaces). Default ordering returns the oldest orders first: pages of GTC limits and triggers from 2023-2024 that never filled. For fresh order flow, pass `start` set to a recent timestamp (e.g. 24 hours ago). `start`/`end` filter each order's placement `timestamp`, not `snapshotTs`. An unfiltered snapshot can exceed 350,000 orders. `side` is the order side (`B` buy, `A` sell), not the position side: a sell stop with `reduceOnly: true` protects a long, a buy stop with `reduceOnly: true` protects a short. Use `triggerPx` for stop and take-profit levels.

**GET /orders/5m-snapshots/{snapshotTime}**: Historical snapshot at a specific time. Params: `snapshotTime` (path, ISO 8601 on a 5-minute boundary, within the last 30 days, not in the future), plus the same filters as `/latest`. Timestamps older than ~30 days pass validation but return an empty list.

**GET /orders/5m-snapshots/latest-snapshot-timestamp**: The newest available snapshot timestamp, as a bare ISO string. Poll this to detect new 5-minute intervals.

**GET /orders/5m-snapshots/coins/{coin}/download**: Download link for the **latest** 5-minute open-orders snapshot of one coin. Returns `{downloadUrl}` pointing to a gzip-compressed JSON array of orders (several MB for BTC), served as `application/gzip` without a `Content-Encoding` header, so HTTP clients do not decompress it automatically: gunzip the bytes before parsing. The link expires after about 240 seconds.

**GET /orders/5m-snapshots/{snapshotTime}/download**: Download link for a full historical 5-minute snapshot as an LZ4-compressed JSON file (`.json.lz4`). `snapshotTime` must be on a 5-minute boundary. Files currently exist only for about January 19 to March 10, 2026; later timestamps return 404 `"Snapshot file is not available at the moment..."`. For recent history use `/orders/5m-snapshots/{snapshotTime}` (last 30 days) or the per-coin latest download.

### Liquidation Data

**GET /fills/liquidation**: Raw liquidation fills across Hyperliquid. Without `start` the newest fills come first (all markets); **with `start` results run oldest first from `start`**. Params: `coin` (single string; `coin[]` returns 400), `address` (single string, any case), `side` (`A`/`B`), `start`, `end` (only together with `start`, at most 3 months after it; defaults to 3 months after `start`, capped at now), `limit` (default 500, max 1000), `nextCursor`. Returns `{fills: [...]}`; each fill carries the normal fill fields plus `liquidatedUser`, `liquidationMarkPx` and `liquidationMethod`. Only the liquidated wallet's fill is returned (`address == liquidatedUser` on every row), so no counterparty filtering is needed. A liquidated long shows `dir: "Close Long"`, `side: "A"`. Covers HIP-3 markets (`xyz:MSTR`, `cash:HOOD`). Data from July 27, 2025.

**GET /{segmentId}/assets/liquidation-risk**: Per-coin liquidation exposure for one cohort. Params: `segmentId` (path), `offset`, `limit` (up to 500). Returns `{totalCount, items: [{coin, totalValue, riskValue, percentRisk}]}`. `percentRisk` is the share of the cohort's open value on that coin that sits within 75% of its liquidation threshold; `riskValue` is that value in USD. Sorted by `percentRisk` descending, so majors with low risk can sit deep in the list: page with `offset` until your coin appears. A coin missing from page 1 does not mean zero exposure.

**GET /exports/coins/{coin}/liquidation-heatmap**: Price bins of potential liquidations for a coin (`liquidationValue`, `positionsCount`, `mostImpactedSegment`). Redirects to a pre-signed file.

### Leaderboards

**GET /leaderboards/perp-pnl**: Traders ranked by perp PnL. Params: `rankBy`, `orderBy`, `order` (`asc`/`desc`, default `desc`), `limit` (25, 50 or 100; default 25), `offset`. `rankBy`/`orderBy` enum: `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay` (both default to `pnlAllTime`; set both, see Critical Rule 10). Returns `{totalCount, data: [...]}` with `address`, `rank`, `previousRank`, `perpEquity`, `openValue`, `openValueLong`, `exposureRatio`, `bias`, `pnlDay`/`pnlWeek`/`pnlMonth`/`pnlAllTime`, `volume*` and `pnlPercent*`. The per-trader `bias` is not bounded to [-1, 1] and is not comparable to cohort bias. The ranking covers hundreds of thousands of wallets; page deeper with `offset`.

**GET /leaderboards/all-pnl**: Traders ranked by total PnL across perps, spot and vaults. Params: `rankBy`, `orderBy`, `order` (all **required**; same enums as above), `limit` (1-100, default 100), `offset`. Returns `totalCount`, `sumPnl`, `assetsDistribution` and `data` (`address`, `age` as an ISO timestamp of the wallet's first activity, `totalValue`, `stableValue`, `topHolding`, `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay`, `rank`, `previousRank`, `profile`).

**GET /leaderboards/perp-pnl/{period}/download**: Full perp-PnL leaderboard file for a period. `period` (path): `all`, `30d`, `7d`, `24h`. Returns `{downloadUrl}`; capped at 25,000 rows per period.

**GET /leaderboards/biggest-positions**: The largest open perp positions on Hyperliquid, ranked by absolute USD notional. Params: `offset` (0-based), `limit` (1-100, default 100), `openedWithin` (`24h`, `7d`, `30d`, `all`). Returns `{totalCount, items: [...]}`. `value` is signed (positive = long, negative = short) and ranking uses `abs(value)`, so a -$31M short ranks above a +$22M long. Each item includes `side`, `address`, `dex`, `coin`, `size`, `entryPrice`, `markPrice`, `unrealizedPnl`, `funding`, `liquidationPrice`, `liquidationProgress`, `crossLeverage`, `isolatedLeverage`, `openTime` and a full `profile` (`totalEquity`, `perpEquity`, `pnl`, `segments`, `walletLeverage`, `displayName`, `verified`). Includes HIP-3 markets.

### Trader & Wallet Data

**GET /wallets**: Active wallets with profile data. Params: `offset`, `limit` (default 100, max 500), `order` (`asc`/`desc`), `orderBy` (`address`, `totalEquity`, `earliestActivityAt`, `perpPnl`, `perpEquity`, `perpBias`, `openValue`, `sumUpnl`, `closestLiqProgress`, `countOpenPositions`, `exposureRatio`), `segmentIds` (array), `hasOpenPositions` (`"true"`/`"false"`), `address` (lowercase). Returns `{totalCount, items}`; each item has `segments` (`[sizeCohortId, pnlCohortId]`), `totalEquity`, `perpEquity`, `perpPnl`, `perpBias`, `exposureRatio`, `closestLiq` (`{coin, progress}`) and profile fields such as `displayName` and `verified`. Only active wallets are included (perp volume in the last 30 days or an open position). An inactive or unknown address returns 200 `{"totalCount": 0, "items": []}`, not 404; fall back to `/closed-trades/summary?address=` for its history.

**GET /fills**: Trade executions for specific wallets. Params: `address[]` (**required**, 1 to 10 wallets), `start` (**required**), `end` (same UTC calendar day; defaults to now), `coin[]` (array), `builder`, `side` (`A` sell, `B` buy), `limit` (default 500, max 1000), `nextCursor`. Returns `{fills, nextCursor}`, including spot fills (spot coins appear as `@142` with `fullCoinName` and `fillType`). History from July 2025.

**GET /fundings**: Funding payments received or paid by a wallet. Params: `address` (**required**, any case), `coin` (HIP-3 supported), `startTime`, `endTime` (at most 1 month apart; defaults to the last 7 days), `limit` (default 100, max 500), `nextCursor`. Returns `{fundings: [{time, blockNumber, address, coin, fundingAmount, szi, fundingRate}], nextCursor}`. `fundingAmount` is positive when received and negative when paid. History from September 27, 2025.

### Closed Trades

HyperTracker reconstructs complete closed trades from every raw Hyperliquid fill, about 10 seconds after a trade's final fill. History from July 2025. A closed trade is one position lifecycle on one coin (opened from flat, closed back to flat); scale-ins and partial exits are folded into that one trade.

**GET /closed-trades**: Closed trades for a wallet. Params: `address` (**required**), `startTime`, `endTime` (close-time window, at most 1 month apart; defaults to the last 7 days), `limit` (default 100, max 500), `nextCursor`. For full history, loop over consecutive windows of 30 days or less, paginate each with `nextCursor`, and dedupe on `id`.

**GET /closed-trades/summary**: Aggregate analytics for a wallet's closed trades, overall and per coin. Params: `address` (**required**; any case is accepted), `interval` (`all`, `365d`, `180d`, `90d`, `30d`, `last50`; default `all`). Returns `address`, `range` (`allTime`, `last365Days`, `last180Days`, `last90Days`, `last30Days` or `last50Trades`), `updatedAt`, a `summary` object and a `coins` array with the same metrics per asset (only coins traded within the interval). Metrics: trade counts (`totalTrades`, `wins`, `losses`, `longTrades`, `shortTrades`), `winRate` (0-1 float), durations (`avgDuration`, `medianDuration` in milliseconds), PnL (`totalWinningPnl`, `totalLosingPnl`, `netPnl`), gain/loss stats (`avgGain`, `avgLoss`, `medianGain`, `medianLoss`), quality ratios (`profitFactor`, `payoffRatio`, `expectancy`, `expectancyPct`) and size/cost stats (`avgTradeSize`, `medianSizeUsd`, `totalFeesPaid`, `totalVolumeUsd`). Each `coins[]` entry also has `volumeSharePct`. `coins[]` is sorted by `totalTrades` descending. Null rules: with zero trades, `winRate`, durations and every ratio are `null`; with zero wins, `avgGain`/`medianGain` are `null`; with zero losses, `avgLoss`/`medianLoss`/`profitFactor`/`payoffRatio` can be `null`. Guard for nulls. The summary does not expose fill counts: a wallet that never goes flat can show a handful of "trades" built from thousands of fills, so check `countFills` on `/closed-trades` before treating a win rate as a discretionary track record.

**GET /closed-trades/{hash}**: One closed trade by hash. Params: `hash` (path, **required**).

**GET /closed-trades/{hash}/fills**: The fills behind one closed trade. Params: `hash` (path, **required**), `startTime`, `endTime`, `limit` (default 100), `nextCursor`. Returns `{fills, nextCursor}`; liquidation fills carry `liquidatedUser`, `liquidationMarkPx`, `liquidationMethod`.

### Volume & Stats

**GET /metrics/perp-volume**: Exchange-wide perp volume over time (one total, not per coin). Params: `start` (**required**), `end`, `limit`, `nextCursor`. Returns `{metrics: [{id, createdAt, volume}], nextCursor}`, roughly hourly.

**GET /exports/total-wallets-equity-chart-data**: Total, perp, spot, staking and vault equity history across all wallets, with ATH and 24-hours-ago values. Redirects to a pre-signed file.

### $HYPE Token

**GET /hype/holders**: HYPE holders with balances, staking and comparisons. Params: `offset`, `limit` (max 500), `order`, `orderBy` (e.g. `totalAmount`), `rankBy`, `rankOrder`. Returns `{items, totalCount}`.

### Builders

**GET /builders/list/timeframe/{timeframe}**: Every builder on Hyperliquid for a timeframe, ordered by revenue desc, with previous-period comparisons (`revenuePrev`, `volumePrev`, `usersPrev`). `timeframe` (path): `24h`, `7d`, `30d`, `all`. Redirects to a pre-signed file.

**GET /builders/{builder}/profile**: Full profile for a builder address: identity, revenue, fee rates and analytics for 24h, 7d, 30d and all time.

**GET /builders/all-time-revenue**: Daily revenue and user counts across all builders. Columnar: `{columns: ["revenue", "timestamp", "countUsers"], data: [[...], ...]}`, newest first. Redirects to a pre-signed file.

**GET /builders/{builder}/fills**: Fills routed through a builder code. Params: `builder` (path), `start` (**required**; keep the window inside one UTC calendar day), `end`, `coin[]` and `address[]` (arrays), `fillType` (`perp`, `spot`), `side` (`A`/`B`), `limit`, `nextCursor`.

**GET /builders/{builder}/users**: Wallets that traded through a builder code. Params: `builder` (path), `offset`, `limit`, `order`, `orderBy` (e.g. `pnl`, `volume`, `builderFee`, `equity`), `period` (`24h`, `7d`, `30d`, `all`; default `all`). Returns `{items, totalCount}`.

### File Exports

All exports redirect to a pre-signed file. Per-coin files expire after about 30 seconds, global files after about 120 seconds.

**GET /exports/{file}**: `file` (path): `segments-bias-charts-data-24h` (every cohort's bias over a ~72-hour rolling window, 24h position-age filter), `total-wallets-equity-chart-data`.

**GET /exports/coins/{coin}/{file}**: Coin-specific files. `file` (path):
- `segment-metrics`, `segment-metrics-24h`, `segment-metrics-7d`, `segment-metrics-30d`: per-cohort metrics for the last ~7 days at 12-hour intervals plus the latest snapshot (the suffix is the position-age filter).
- `position-metrics`: columnar coin metrics at 1-hour intervals for about 14 days (latest snapshot first). The `columns` header includes `coin` but each row omits it, so drop `coin` before zipping columns to rows.
- `position-breakdown-by-size`, `-24h`, `-7d`, `-30d`: positions grouped by size bucket (`positionCount`, `pastPositionCount`, `totalPositionValue`, `totalPositionValueLong`, `valueCloseToLiquidation`, `bias`).
- `position-breakdown-by-cohort`, `-24h`, `-7d`, `-30d`: the same breakdown grouped by cohort.
- `liquidation-heatmap`: price bins of potential liquidations.

### Address Management

Manage your own tracked-address list (useful for watchlists).

**GET /addresses**: List your tracked addresses. Params: `offset`, `limit` (default 100), `addresses` (array filter). Returns `{items, totalCount}`.

**POST /addresses/bulk**: Add addresses. Body: `{ "addresses": ["0x...", "0x..."] }`.

**DELETE /addresses/bulk**: Remove addresses. Body: `{ "addresses": ["0x...", "0x..."] }`.

**PUT /addresses/sync**: Replace your whole list. Body: `{ "addresses": ["0x...", "0x..."] }`.

### Hyperliquid Info Proxy

**POST /info**: Proxy to Hyperliquid's `/info` API with higher rate limits. Body: `{ "type": "<infoType>", "user": "0x..." }` plus optional `dex` (for HIP-3, e.g. `"xyz"`) and `builder`. **`user` is required by validation for every type**, including global ones like `meta` (pass any valid address). Accepted `type` values: `meta`, `spotMeta`, `clearinghouseState`, `spotClearinghouseState`, `openOrders`, `frontendOpenOrders`, `exchangeStatus`, `liquidatable`, `activeAssetData`, `maxMarketOrderNtls`, `vaultSummaries`, `userVaultEquities`, `leadingVaults`, `extraAgents`, `subAccounts`, `userFees`, `userRateLimit`, `spotDeployState`, `perpDeployAuctionStatus`, `delegations`, `delegatorSummary`, `maxBuilderFee`, `userToMultiSigSigners`, `userRole`, `perpsAtOpenInterestCap`, `validatorL1Votes`, `marginTable`, `perpDexs`, `webData2`. Market data types such as `candleSnapshot`, `l2Book` and `allMids` are not proxied; call Hyperliquid directly for those.

### System Status

**GET /hypertracker/state/status**: Data freshness: `{lastUpdate, nextUpdate, nextUpdateThreshold}`. Use it to schedule polling, or pair it with the state webhook.

---

## Infrastructure: Real-Time & Push Delivery

Beyond REST, HyperTracker runs production Hyperliquid data infrastructure that builders can plug into directly: live WebSocket streams, server-side alerts delivered to your own webhook, state-update webhooks, and dedicated infrastructure for enterprise teams. Use these instead of polling when you need data as it happens.

### Real-Time WebSocket Streams

Live Hyperliquid fills, account events, TWAP updates and order events over WebSocket or SSE (Centrifugo protocol). The pricing table lists WebSocket streams on the Stream plan.

| Purpose | URL |
|---------|-----|
| WebSocket | `wss://ws.hypertracker.io/connection/websocket` |
| SSE | `https://ws.hypertracker.io/connection/sse` |

| Data | Channel | Filter field | Replay |
|------|---------|--------------|--------|
| Every trade fill | `rooms:fills` | `tf` | Yes (often only seconds, high volume) |
| Account events: deposits, withdrawals, transfers, delegations, vault activity, liquidations, funding | `rooms:misc_events` | `tf` | Yes |
| TWAP status (`activated` to `finished`/`terminated`) | `rooms:twaps` | `tf` | Yes |
| Every order event (open, filled, canceled, triggered, ...) | `orders:feed` | `data` (`{"filter": ...}`) | No, live only |

**Protocol (plain WebSocket):**
1. Connect with the header `Authorization: Bearer <token>` (browsers: send `{"id":1,"connect":{"data":{"token":"<token>"}}}` instead). Never send the token on subscribe.
2. Send `{"id": 1, "connect": {}}` first.
3. Subscribe: `{"id": 2, "subscribe": {"channel": "rooms:fills", "tf": <filter>}}`. For `orders:feed`, put the filter in `data`: `{"id": 2, "subscribe": {"channel": "orders:feed", "data": {"filter": <filter>}}}`.
4. Events arrive as `{"push": {"channel": "...", "pub": {"data": {...}, "offset": 42}}}`.
5. Reply `{}` to every `{}` ping, and split each frame on `\n` before parsing (one frame can hold several messages).

**Filters:** `{"op": "", "key": "coin", "cmp": "eq", "val": "BTC"}`, combined with `{"op": "and" | "or" | "not", "nodes": [...]}`. `cmp`: `eq`, `neq`, `in`, `nin` (use `vals`), `ex`, `nex`, `sw`, `ew`, `ct`, `gt`, `gte`, `lt`, `lte`. Tags are text; boolean-looking tags are `"true"`/`"false"`, and numeric comparisons parse the text. Fill tags: `address`, `coin`, `px`, `sz`, `side`, `dir`, `isBuilder`, `isLiquidation`, `twapid`, `builder`, `liquidation.user`, `liquidation.method`. Order tags: `address`, `coin`, `side`, `oid`, `limitPx`, `sz`, `origSz`, `tif`, `cloid`, `orderType`, `triggerCondition`, `isTrigger`, `reduceOnly`, `isPositionTpsl`, `status`. Account-event tags: `eventType` (e.g. `LedgerUpdate.deposit`, `LedgerUpdate.liquidation`, `Funding`), `user`. TWAP tags: `status`, `user`, `coin`, `twapId` (fills use the lowercase tag `twapid` for the same value). `orders:feed` `orderType` values: `Limit`, `Market`, `Stop Market`, `Stop Limit`, `Take Profit Market`, `Take Profit Limit`, `Vault Close`.

**Stream rules:**
- Always filter `orders:feed` narrowly (usually by `address`). Without a filter every order is delivered and the server closes the connection with `3008 slow` within seconds. Exclude `Funding` from `rooms:misc_events` unless you need it: it spikes to tens of thousands of events every hour.
- Every event carries `id` (the dedupe key), `blockNumber`, `blockTime`, `localTime` and `sentTime`. Events can arrive more than once. `id` is text for fills, orders and TWAPs (never parse order IDs); for account events it is a 64-bit number that loses precision in JavaScript `JSON.parse`, so dedupe on the raw string or use a big-int-safe parser.
- Replay covers only a few minutes and a few hundred events (fills: often seconds). Save the channel `epoch` and each `offset`, then resubscribe with `"recover": true, "epoch": ..., "offset": ...` after a short drop (`recovered: false` means the gap was not filled; no error is returned). Streams cannot backfill history: use REST (`/fills`, `/fills/liquidation`, `/closed-trades`) for anything older. `3010` means the gap is too large; subscribe fresh.
- A liquidation produces two tagged fills, one for the liquidated wallet and one for the counterparty. To total liquidations, count only fills where `address == liquidation.liquidatedUser`.
- Prices and sizes are decimal strings. `blockTime`, `localTime`, `sentTime` and fill `time` are epoch milliseconds; the TWAP stream's `time` is an ISO 8601 string and account-event `time` is an ISO string without a `Z` suffix (treat it as UTC).
- SDKs: `centrifuge-js` (JavaScript/TypeScript) and `centrifuge-python` handle pings, reconnects and replay. Some Python SDK versions don't expose `tf`; use a plain WebSocket for `rooms:*` filters.

### Server-Side Alerts (Events API, Beta)

Define what to watch, give HyperTracker an HTTPS URL, and each match is POSTed to your server as JSON. No polling. Available on all plans, including Free. Every alert-management request and every successful delivery uses one usage token; failed attempts, retries and paused or suspended skips are not billed. The API contract is stable; the product is labelled Beta.

**Routes** (same base URL and Bearer token as REST):

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/events/endpoints` | Register a webhook endpoint. Body: `endpoint` (HTTPS URL), `secretKey` (signing secret, strongly recommended), `description` |
| GET | `/events/endpoints` | List endpoints: `{items}` |
| GET / PATCH / DELETE | `/events/endpoints/{id}` | Read (incl. `deliveryStatus`, `suspendedUntil`, `lastDeliveryFailureReason`), update (`endpoint`, `secretKey`, `description`, `paused`), delete (409 while alert rules still reference it) |
| POST | `/events` | Create an alert rule. Body: `eventType`, `webhookEndpointId`, optional `addresses`, optional `filters` |
| GET | `/events` | List rules: `{items, totalCount}`. Params: `offset`, `limit` (default 100, max 1000), `eventType`, `webhookEndpointId` |
| GET / PATCH / DELETE | `/events/{id}` | Read, partially update (incl. `paused`), delete |

Create the endpoint first; its `id` becomes the rule's `webhookEndpointId`. The rule's `id` arrives on every delivery as `eventId`.

**Event types:**

| `eventType` | Fires when | `addresses` | `filters` |
|-------------|-----------|-------------|-----------|
| `position_activity` | A tracked wallet makes a (non-TWAP) perp fill | Required, 1-1000 | `coin` (array) |
| `twap_execution` | A tracked wallet's TWAP fills a slice | Required, 1-1000 | `coin` (array) |
| `twap_lifecycle` | A TWAP starts, finishes, is cancelled or errors | Optional, max 1000 (blank = exchange-wide) | `coin` (array) |
| `ledger_update` | A deposit or withdrawal happens | Optional (blank = exchange-wide) | `types` (`deposit`, `withdraw`), `amount` (`{gte, gt, lte, lt, eq}`) |
| `liquidation` | A position is liquidated | Optional (blank = every liquidation) | `thresholdUsd`, `markets` (array), `side` (`long`, `short`, `both`) |
| `price_crossing` | A market's price crosses your threshold | Not used | `market` (string, required), `threshold` (required), `direction` (`above`, `below`, `both`; default `both`) |
| `large_market_order` | Anyone trades above your USD threshold | Not supported (exchange-wide) | `thresholdUsd` (required, at least 50000), `markets` (array), `direction` (`buy`, `sell`, `both`) |

**Gotchas:**
- The signing field is `secretKey`. A field named `secret` is accepted without an error but does not set a signing secret, so deliveries arrive unsigned. An empty `secretKey` also creates an unsigned endpoint.
- `addresses` is a top-level field, never inside `filters`. Addresses need the `0x` prefix.
- All numeric filter values are decimal strings: `"thresholdUsd": "1000000"`, `"threshold": "65000.00"`.
- The market key differs by type: `market` (string) for `price_crossing`; `markets` (array) for `liquidation` and `large_market_order`; `coin` (array) for `position_activity`, `twap_execution`, `twap_lifecycle`. Market lists hold up to 100 entries.
- Tickers are not validated: `"btc"` or a misspelled coin is accepted and never fires. Use exact case and HIP-3 prefixes (`xyz:NVDA`).
- PATCH replaces the whole `filters` object, so resend every filter you want to keep.
- `price_crossing` fires only when price moves across the threshold after the rule exists; touching it is not enough.
- Exchange-wide rules (blank addresses on `liquidation`, `ledger_update`, `twap_lifecycle`; any `large_market_order`) can produce high delivery volume, and each delivery uses a token. Start with a high `thresholdUsd`.

**Deliveries:** each POST body is `{deliveryId, consumerId, webhookEndpointId, eventId, eventType, occurredAt, data}` with headers `x-event-id`, `x-webhook-event`, `x-webhook-delivery-id` and, when a `secretKey` is set, `x-webhook-signature: v1=<hex HMAC-SHA256 of the raw body>`. Verify the signature over the raw bytes before parsing JSON, store each delivery once using `deliveryId` as the unique key (delivery is at-least-once), then return 2xx. Responses 408, 409, 425, 429 and 5xx are retried, honoring `Retry-After`; any other status (e.g. 400, 401, 404) is not retried and the delivery is lost, so return 2xx for an already-stored `deliveryId`. Ten failures within five minutes suspend the endpoint for five minutes up to one hour, and events skipped during suspension are not replayed. Deliveries for one rule are processed in order within a batch; there is no ordering across rules, so sort by payload timestamps. `position_activity` delivers raw fills without "opened/closed" interpretation. There is no cohort-based event type: build cohort alerts by polling cohort endpoints (see recipes).

### State Webhooks

Configure in the API Dashboard (Webhook States card, then Add Webhook URL; `https://` only, optional Bearer header). After each state refresh (roughly every 15 to 30 minutes) HyperTracker POSTs `{"event": "stateUpdated", "timestamp": "...", "data": {}}`. The ping carries no data; use it to trigger your REST refresh instead of polling. Check the pricing page for which plans include webhooks.

### Enterprise & Dedicated Infrastructure

For teams that outgrow the Stream plan, HyperTracker offers custom rate limits, dedicated API infrastructure, multi-region deployment and white-label solutions with direct technical support. Contact support@coinmarketman.com or the HyperTracker Telegram group.

### Hyperliquid Node Peering (Planned)

A planned, SLA-backed peering service for teams running their own Hyperliquid non-validating node: allowlisted peer connectivity, monitoring and onboarding support, 99.9% monthly peering uptime, $500 per month per allowlisted connecting-node IP, the same terms for every customer. It is a separate infrastructure product: it does not include REST, WebSocket, webhook or cohort data, and API plans are not required. Activation is by manual onboarding once the service launches; register interest at support@coinmarketman.com (subject "Hyperliquid Node Peering"). Peering improves connection stability; it does not guarantee latency.

---

## Response Examples

### /segments/{segmentId}/bias-history (with `start`)
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
Rows are newest first. `nextCursor`, `pageStart` and `pageEnd` appear only when `start` is passed.

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

### /leaderboards/all-pnl
```json
{
  "totalCount": 150000,
  "sumPnl": 45230000.50,
  "assetsDistribution": [...],
  "data": [
    {"address": "0xabc1...", "age": "2024-12-04T22:42:00.059Z", "totalValue": 5200000.00, "stableValue": 1200000.00, "topHolding": "BTC", "pnlAllTime": 15230000.50, "pnlMonth": 1230000.00, "pnlWeek": 450000.00, "pnlDay": 85000.00, "rank": 1, "previousRank": 2, "profile": {...}}
  ]
}
```

### /leaderboards/biggest-positions
```json
{
  "totalCount": 428497,
  "items": [
    {
      "id": "45883cd1...",
      "side": "short",
      "address": "0x5b5d...",
      "dex": "main",
      "coin": "ETH",
      "value": -282311627.00,
      "size": 104540.5025,
      "entryPrice": 2304.07,
      "markPrice": 2700.5,
      "unrealizedPnl": -41443433.46,
      "funding": 3145323.51,
      "liquidationPrice": 4183.41,
      "liquidationProgress": 21.09,
      "crossLeverage": 5,
      "isolatedLeverage": 0,
      "openTime": "2026-07-09T07:57:47.000Z",
      "closeTime": null,
      "profile": {"totalEquity": 244750462.07, "perpEquity": 168593145.34, "pnl": 86700403.31, "segments": [7, 8], "walletLeverage": 5.08, "displayName": null, "verified": false}
    }
  ]
}
```

### /fills/liquidation
```json
{
  "fills": [
    {
      "address": "0x738a...",
      "coin": "SUI",
      "fillType": "perp",
      "px": 1.262,
      "sz": 173.4,
      "side": "B",
      "dir": "Close Short",
      "time": "2026-10-04T15:47:13.441Z",
      "startPosition": -173.4,
      "closedPnl": -16.63,
      "fee": 0.098,
      "hash": "0x5006...",
      "liquidatedUser": "0x738a...",
      "liquidationMarkPx": 1.2612,
      "liquidationMethod": "market"
    }
  ],
  "nextCursor": "eyJ..."
}
```

### /fundings
```json
{
  "fundings": [
    {"time": "2026-10-04T16:00:00.013Z", "blockNumber": 1171594303, "address": "0x8def...", "coin": "HYPE", "fundingAmount": 117.77, "szi": -104699.13, "fundingRate": 0.0000125}
  ],
  "nextCursor": "eyJ..."
}
```
`szi` is the signed position size (negative = short). Positive `fundingAmount` = received.

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
`duration` is in milliseconds (`closeTime - openTime`). `side` is `"long"` or `"short"`. `partial` indicates whether the trade was partially closed. `avgEntry`/`avgExit` are averages across all fills of the trade. `id` is a string in both the list and the single-trade endpoint. Fees and funding are reported in their own fields (`feeUsd`, `fundingUsd`). Use `hash` with `/closed-trades/{hash}` and `/closed-trades/{hash}/fills`. A high `countFills` (this example has 12,080) usually means algorithmic execution rather than one discretionary decision.

### /closed-trades/summary
```json
{
  "address": "0xa5b0edf6b55128e0ddae8e51ac538c3188401d41",
  "range": "allTime",
  "updatedAt": "2026-05-28T13:51:17.145Z",
  "summary": {
    "totalTrades": 300,
    "wins": 206,
    "losses": 94,
    "winRate": 0.6867,
    "longTrades": 289,
    "shortTrades": 11,
    "avgDuration": 78823930,
    "medianDuration": 43200000,
    "totalWinningPnl": 1250000.00,
    "totalLosingPnl": -420000.00,
    "netPnl": 830000.00,
    "avgGain": 6067.96,
    "avgLoss": -4468.09,
    "medianGain": 4200.50,
    "medianLoss": -3100.75,
    "profitFactor": 2.98,
    "payoffRatio": 1.36,
    "expectancy": 2766.67,
    "expectancyPct": 0.0325,
    "totalFeesPaid": 21000.00,
    "avgTradeSize": 85000.00,
    "medianSizeUsd": 79000.50,
    "totalVolumeUsd": 25500000.00
  },
  "coins": [
    {
      "coin": "BTC",
      "totalTrades": 42,
      "wins": 29,
      "losses": 13,
      "winRate": 0.6905,
      "longTrades": 21,
      "shortTrades": 21,
      "avgDuration": 43200000,
      "medianDuration": 36000000,
      "totalWinningPnl": 320000.00,
      "totalLosingPnl": -95000.00,
      "netPnl": 225000.00,
      "avgGain": 11034.48,
      "avgLoss": -7307.69,
      "medianGain": 8200.25,
      "medianLoss": -5200.50,
      "profitFactor": 3.37,
      "payoffRatio": 1.51,
      "expectancy": 5357.14,
      "expectancyPct": 0.0429,
      "totalFeesPaid": 4500.00,
      "avgTradeSize": 125000.00,
      "medianSizeUsd": 118000.25,
      "totalVolumeUsd": 5250000.00,
      "volumeSharePct": 0.2059
    }
  ]
}
```
`winRate` is a 0-1 float (multiply by 100 for a percentage). Durations are milliseconds. Formulas (verified against prod): `profitFactor = totalWinningPnl / abs(totalLosingPnl)`, `payoffRatio = avgGain / abs(avgLoss)`, `expectancy = netPnl / totalTrades` (average dollar PnL per trade; the docs write it as `winRate * avgGain + (1 - winRate) * avgLoss`, which is the same when there are no break-even trades), `expectancyPct = expectancy / avgTradeSize`, `volumeSharePct = coin totalVolumeUsd / summary totalVolumeUsd`. `updatedAt` is `null` for wallets with no closed trades.

### Paginated responses
Paginated endpoints return a named array plus `nextCursor`. The array key varies (`positions`, `fills`, `orders`, `trades`, `fundings`, `metrics`, `items`).
```json
{
  "positions": [...],
  "nextCursor": "eyJsYXN0SWQiOiAxMjM0NX0="
}
```

---

## Rate Limits & Pricing

| Plan | Price | Usage tokens | Rate limit | Included delivery |
|------|-------|--------------|------------|-------------------|
| Free | $0 | 100/day | n/a | REST, server-side alerts |
| Pulse | $179/mo | 50,000/mo | 60 req/min | REST, server-side alerts |
| Surge | $399/mo | 150,000/mo | 100 req/min | REST, server-side alerts |
| Flow | $799/mo | 400,000/mo | 200 req/min | REST, server-side alerts |
| Stream | $1,999/mo | 2,000,000/mo | 500 req/min | REST, server-side alerts, WebSocket streams |
| Enterprise | Custom | Custom | Custom | Dedicated infrastructure, multi-region, white-label |

Usage is metered in tokens shared across the whole API. Server-side alerts use one token per management request and per successful delivery. The per-minute rate limit counts requests. Webhook availability by plan is shown on the pricing page: https://app.coinmarketman.com/hypertracker/api

On `429`, the body is `{"error": "rate_limit_exceeded", "message": "...", "retry_after": 42}`. Wait `retry_after` seconds (or the `Retry-After` header when present), then retry with exponential backoff. Pace bulk sweeps (e.g. one request every 0.2 to 0.5 seconds) and cache responses: most data only changes on each state update.

---

## Code Patterns

### Python: Auth + Request
```python
import requests

BASE = "https://ht-api.coinmarketman.com/api/external"
HEADERS = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

data = requests.get(f"{BASE}/segments/9/bias-history", headers=HEADERS).json()
```

### JavaScript: Auth + Request (ES module, for top-level `await`)
```javascript
const BASE = "https://ht-api.coinmarketman.com/api/external";
const response = await fetch(`${BASE}/segments/9/bias-history`, {
  headers: { Authorization: "Bearer YOUR_JWT_TOKEN" },
});
const data = await response.json();
```

### ISO 8601 Dates (Python)
```python
from datetime import datetime, timezone, timedelta

def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

now = datetime.now(timezone.utc)
params = {"start": iso(now - timedelta(hours=1)), "end": iso(now)}
```

### Cursor Pagination
```python
def fetch_all(path, params, key):
    rows, cursor = [], None
    while True:
        p = dict(params)
        if cursor:
            p["nextCursor"] = cursor          # not "cursor"
        resp = requests.get(f"{BASE}{path}", headers=HEADERS, params=p).json()
        rows.extend(resp[key])
        cursor = resp.get("nextCursor")
        if not cursor:
            return rows

# one wallet's open positions; without "address" this pages through every open BTC position (many calls)
positions = fetch_all("/positions", {"start": "2025-04-04T00:00:00.000Z", "address": "0xabc...", "open": "true"}, "positions")
```

### Fills for a wallet, one UTC day at a time
```python
from datetime import datetime, timezone, timedelta

ADDRESS = "0xabc..."  # lowercase
day = datetime(2026, 9, 20, tzinfo=timezone.utc)
for _ in range(5):
    params = {
        "address[]": [ADDRESS],                      # required, 1-10 wallets
        "coin[]": ["BTC"],                           # optional, must be an array
        "start": iso(day),
        "end": day.strftime("%Y-%m-%dT23:59:59.999Z"),   # last instant of the same UTC calendar day
        "limit": 1000,
    }
    fills = fetch_all("/fills", params, "fills")     # follows nextCursor for busy wallets
    day += timedelta(days=1)
```

### Full closed-trade history (30-day windows)
```python
def all_closed_trades(address, since, until):
    trades, seen = [], set()
    window_start = since
    while window_start < until:
        window_end = min(window_start + timedelta(days=30), until)
        cursor = None
        while True:
            params = {"address": address, "startTime": iso(window_start), "endTime": iso(window_end), "limit": 500}
            if cursor:
                params["nextCursor"] = cursor
            resp = requests.get(f"{BASE}/closed-trades", headers=HEADERS, params=params).json()
            for t in resp["trades"]:
                if t["id"] not in seen:
                    seen.add(t["id"])
                    trades.append(t)
            cursor = resp.get("nextCursor")
            if not cursor:
                break
        window_start = window_end
    return trades
```
Closed trades never change once written, so cache them and re-query only from your newest `closeTime`.

### Follow a redirect / download link
```python
r = requests.get(f"{BASE}/positions/open/coin/BTC", headers=HEADERS)  # requests follows the 302
csv_text = r.text

import gzip, json

link = requests.get(f"{BASE}/orders/5m-snapshots/coins/BTC/download", headers=HEADERS).json()["downloadUrl"]
raw = requests.get(link).content          # download right away, the link expires
# the file is served as application/gzip without Content-Encoding, so decompress it yourself
orders = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
```

### 429 backoff
```python
import time

def get(path, params=None, tries=5):
    for attempt in range(tries):
        r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params)
        if r.status_code != 429:
            r.raise_for_status()
            return r.json()
        try:
            body = r.json()
        except ValueError:
            body = {}
        wait = r.headers.get("Retry-After") or (body.get("retry_after") if isinstance(body, dict) else None)
        try:
            wait = float(wait)
        except (TypeError, ValueError):     # missing, or an HTTP-date Retry-After
            wait = 2 ** attempt
        time.sleep(wait)
    raise RuntimeError("rate limited")
```

### WebSocket: live liquidations (Python)
```python
import asyncio, json, websockets

FILTER = {"op": "", "key": "isLiquidation", "cmp": "eq", "val": "true"}

async def main():
    async with websockets.connect(
        "wss://ws.hypertracker.io/connection/websocket",
        additional_headers={"Authorization": "Bearer YOUR_JWT_TOKEN"},  # websockets < 12: extra_headers
        max_size=None,
    ) as ws:
        await ws.send(json.dumps({"id": 1, "connect": {}}))
        seen = set()
        async for frame in ws:
            for line in str(frame).split("\n"):
                if not line:
                    continue
                msg = json.loads(line)
                if msg == {}:                                   # ping
                    await ws.send("{}")
                elif msg.get("id") == 1:                        # connected
                    await ws.send(json.dumps({"id": 2, "subscribe": {"channel": "rooms:fills", "tf": FILTER}}))
                elif msg.get("push", {}).get("pub"):
                    fill = msg["push"]["pub"]["data"]
                    if fill["id"] in seen:
                        continue
                    seen.add(fill["id"])
                    liq = fill.get("liquidation") or {}
                    if fill["address"] == liq.get("liquidatedUser"):   # count the liquidated side only
                        print(fill["coin"], fill["dir"], float(fill["sz"]) * float(fill["px"]))

asyncio.run(main())
```

### Server-side alert: whale liquidations to your webhook
```bash
BASE=https://ht-api.coinmarketman.com/api/external
: "${TOKEN:?set TOKEN}" "${SECRET:?set SECRET, e.g. SECRET=$(openssl rand -hex 32)}"
EP=$(curl -s -X POST "$BASE/events/endpoints" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"endpoint":"https://yourapp.com/webhooks/hypertracker","secretKey":"'"$SECRET"'","description":"liquidation alerts"}' | jq -er .id) || exit 1

curl -s -X POST "$BASE/events" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"eventType":"liquidation","webhookEndpointId":'"$EP"',"filters":{"thresholdUsd":"1000000","markets":["BTC","ETH"],"side":"both"}}'
```

### Verify a delivery signature (Python, Flask)
```python
import hashlib, hmac, json, os
from flask import Flask, request, abort

SECRET = os.environ["HYPERTRACKER_WEBHOOK_SECRET"].encode()
app = Flask(__name__)

@app.post("/webhooks/hypertracker")
def receive():
    raw = request.get_data()                                  # raw bytes, before JSON parsing
    header = request.headers.get("x-webhook-signature", "")
    expected = "v1=" + hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(header.lower(), expected):
        abort(401)
    event = json.loads(raw)                                   # parse the same bytes you verified
    store_once(event["deliveryId"], event)                     # your idempotent storage; return 503 if it fails
    return "", 204
```

### 5-Minute Boundary Alignment
```python
def align_to_5min(dt):
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)
```

### Reverse Lookup: Match a PnL share card to wallets

A Hyperliquid PnL share card shows coin, side, leverage, entry price, mark price and ROI. Find candidate wallets like this:

```python
def find_positions_matching_card(coin, side, leverage, entry_price,
                                  entry_tolerance_pct=0.0005, start="2025-04-04T00:00:00.000Z"):
    # start filters on openTime: keep it early so older open positions are included
    matches, cursor = [], None
    while True:
        params = {"coin": coin, "open": "true", "start": start, "limit": 1000}   # "true" as a string
        if cursor:
            params["nextCursor"] = cursor
        r = requests.get(f"{BASE}/positions", headers=HEADERS, params=params).json()
        for p in r["positions"]:
            if p["side"] != side.lower():                       # "long" / "short"
                continue
            lev = float(p.get("crossLeverage") or p.get("isolatedLeverage") or 0)
            if abs(lev - leverage) > 0.5:
                continue
            if abs(float(p["entryPrice"]) - entry_price) > entry_price * entry_tolerance_pct:
                continue
            matches.append(p)
        cursor = r.get("nextCursor")
        if not cursor:
            return matches

def lookup_wallet(address):
    r = requests.get(f"{BASE}/wallets", headers=HEADERS, params={"address": address.lower()}).json()
    return r["items"][0] if r.get("items") else None   # None = not an active wallet; try /closed-trades/summary
```

**Match dimensions on each position:** `side` (`"long"`/`"short"`), `crossLeverage`/`isolatedLeverage`, `entryPrice`, `size`, `openTime`, `unrealizedPnl`, `profile.segments` (the wallet's two cohort IDs).

**ROI from a card (short):** `(entry - mark) / entry * leverage * 100`. Long: `(mark - entry) / entry * leverage * 100`. Use it to sanity-check a candidate, not to match on, since the card's mark price is frozen at share time.

**Tolerances worth trying:** `entry_tolerance_pct` of 0.0005 (0.05%, tight), 0.005 (0.5%, loose), 0.01 (1%, last resort). A relative tolerance works across cheap and expensive coins alike.

**Disambiguating multiple matches:** surface all matches with size and open time rather than auto-picking. The candidate whose current `markPrice` is closest to the card's mark is the strongest match.

**Shortcut:** cohort IDs are on the position itself (`profile.segments`). Call `/wallets` only when you also need equity, PnL or display name.

---

## Example Prompts

### For Vibe Coders (no dev experience needed)

**"I want to see what smart money is doing right now. Build me something simple."**
Endpoints: `/segments`, `/segments/{segmentId}/bias-history`
Fetch the latest bias for each cohort and show a simple long/short indicator per cohort. Green for net long, red for net short. One-page HTML.

**"Show me which coins have the most positions close to liquidation"**
Endpoints: `/{segmentId}/assets/liquidation-risk`
Fetch liquidation risk for a few cohorts, sort by `percentRisk`, and show a ranked list with colors by severity.

**"Show me the biggest positions on Hyperliquid right now and who holds them"**
Endpoints: `/leaderboards/biggest-positions?limit=25`
List the 25 largest open positions with coin, side, size, entry, unrealized PnL, liquidation progress and the holder's cohorts (from `profile.segments`). Highlight anything with `liquidationProgress` above 80.

**"What should I be watching today? Rank coins by where the most interesting activity is happening."**
Endpoints: `/positions/heatmap`, `/orders/5m-snapshots/latest?start={24h ago}`, `/{segmentId}/assets/liquidation-risk`, `/fills/liquidation`
Score each coin by smart money conviction (heatmap bias of cohorts 8 and 9), fresh order clustering, liquidation exposure and recent liquidations. Surface the top 5 with a one-line reason each.

**"Am I about to get liquidated? Check if my position is safe."**
Endpoints: `/positions?address={address}&open=true&start=2025-04-04T00:00:00.000Z`, `/exports/coins/{coin}/liquidation-heatmap`
Pull the user's open positions, compare each `liquidationPrice` with `markPrice`, and show where the big liquidation clusters sit on that coin. Give a plain-English safety rating.

**"Show me a fear/greed gauge for Hyperliquid right now"**
Endpoints: `/segments/{segmentId}/bias-history`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`
Composite score from cohort bias, liquidation exposure and OI trend. Display as a gauge with color-coded zones. One-page HTML.

**"Show me what whales are doing vs retail on BTC"**
Endpoints: `/position-metrics/coin/BTC/segment/7?start={1h ago}`, `/position-metrics/coin/BTC/segment/9?start={1h ago}`, `/position-metrics/coin/BTC/segment/16?start={1h ago}`
Compare Leviathan (7) and Smart Money (9) against Shrimp (16). Show who's long, who's short, and whether they agree.

**"How are the smart money cohorts positioned on gold and the S&P 500?"**
Endpoints: `/position-metrics/coin/xyz:GOLD/segment/{segmentId}?start={1h ago}`, `/position-metrics/coin/xyz:SP500/segment/{segmentId}?start={1h ago}`
HIP-3 markets work like any coin; keep the lowercase `xyz:` prefix. Compare cohorts 8 and 9 with cohorts 12 to 15.

### Dashboards

**"Build a Hyperliquid market dashboard with cohort positioning, order flow, and liquidation risk"**
Endpoints: `/positions/heatmap`, `/orders/5m-snapshots/latest?start={24h ago}`, `/{segmentId}/assets/liquidation-risk`, `/position-metrics/general?start={24h ago}`, `/hypertracker/state/status`
Refresh when `/hypertracker/state/status` reports a new `lastUpdate` (or on the state webhook) instead of on a fixed timer.

**"Track my positions and compare them against smart money"**
Endpoints: `/wallets?address={address}`, `/positions?address={address}&open=true&start=2025-04-04T00:00:00.000Z`, `/position-metrics/coin/{coin}/segment/9?start={24h ago}`

### Trading Signals

**"Alert me when two cohorts diverge on any coin"**
Endpoints: `/positions/heatmap`, `/position-metrics/coin/{coin}/segment/{segmentId}`
Poll the heatmap once per state update, detect coins where Smart Money (9) and Exit Liquidity (12) lean opposite ways, and pull coin-level history to confirm the split is persistent. Cohort alerts are not a server-side event type, so this runs as a polling job.

**"Mean-reversion alert when a cohort's bias hits an extreme and reverses"**
Endpoints: `/segments/{segmentId}/bias-history?start={30d ago}`
Track the bias series, define extremes from the cohort's own history (e.g. its 90th/10th percentile), and fire when the pullback starts.

**"Contrarian signal: go opposite of Exit Liquidity and Giga-Rekt"**
Endpoints: `/positions/heatmap`, `/position-metrics/coin/{coin}/segment/12`, `/position-metrics/coin/{coin}/segment/15`
When Exit Liquidity (12) and Giga-Rekt (15) are heavily positioned one way, flag the opposite direction. Use 24-hour averages rather than a single snapshot.

### Order Flow

**"Map BTC orders by price level and type. Show where stops, TPs, and limits cluster."**
Endpoints: `/orders/5m-snapshots/latest?coin=BTC&start={24h ago}`
Page through fresh orders, bucket by `limitPx` (or `triggerPx` for stops and take-profits), count by `orderType`, and plot against the current price. Use `side` plus `reduceOnly` to tell which positions each stop protects.

### Liquidation

**"How much got liquidated on Hyperliquid in the last hour, and who got hit?"**
Endpoints: `/fills/liquidation?start={1h ago}`
Page through liquidation fills for the window (each row is the liquidated side), total `px * sz` by coin and by side (`dir` of `Close Long` = long liquidated), and list the largest. With `start`, results arrive oldest first, so sort by `px * sz` client-side. Look up the biggest liquidated wallets with `/wallets?address={liquidatedUser}` for cohort context.

**"Liquidation risk monitor across all coins, ranked and auto-refreshing"**
Endpoints: `/{segmentId}/assets/liquidation-risk`, `/position-metrics/coin/{coin}`
Rank by `percentRisk`, pull OI for the riskiest coins, color-code severity, refresh on each state update.

### Leaderboard

**"Watchlist from today's top 25 traders. Alert me when they trade."**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlDay&orderBy=pnlDay&order=desc&limit=25`, `POST /events/endpoints`, `POST /events` (`position_activity`)
Fetch today's leaders, then create one `position_activity` alert rule with their addresses so every non-TWAP fill is pushed to your webhook (add a `twap_execution` rule for TWAP slices). No polling.

### Closed Trades: Basic Queries

**"Pull this wallet's full closed trade history and compute their win rate and average hold."**
Endpoints: `/closed-trades/summary?address={address}`, `/closed-trades?address={address}&startTime=...&endTime=...`
Use `/summary` for `winRate`, `wins`, `losses`, `totalTrades`, `avgDuration`, `profitFactor`, `expectancy`. Use `/closed-trades` in 30-day windows for per-trade detail (entry, exit, realized PnL, fill count).

**"Show me the most profitable closed trades on Hyperliquid this month, by wallet."**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=25`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}&startTime={30d ago}`
Monthly leaders give candidates; pull each one's summary, then their largest trades by `realizedPnlUsd`.

**"Build a wallet-follow feed for a wallet"**
Endpoints: `POST /events` (`position_activity`), `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`
Push every non-TWAP fill from the watched wallets to your webhook with a `position_activity` rule (add `twap_execution` for TWAP slices). Use `/closed-trades` afterwards to reconcile completed trades and their realized PnL.

### Closed Trades: Wallet Discovery

The per-coin breakdown in `/closed-trades/summary` (`coins[]`) turns the endpoint into a wallet-discovery engine. Each coin entry has its own `winRate`, `profitFactor`, `expectancy` and `netPnl`, so you can find traders who are good on a specific asset.

**"Find the best [COIN] traders on Hyperliquid"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=100`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}&startTime={30d ago}`
Pull the top 100 monthly wallets. For each, find the target coin in `coins[]` and keep specialists: `totalTrades > 20`, `winRate > 0.6`, `profitFactor > 2`, `expectancyPct > 0.02`. Then vet survivors: check `countFills` on their recent trades (dozens or thousands of fills per trade usually means an execution algorithm, not a copyable decision), and confirm recent performance with `interval=30d`, since a strong all-time record can hide a losing month. Rank by per-coin `expectancy` or `netPnl`. Add cohort context from `/wallets?address={address}`.

**"Build a follow watchlist for [COIN] specialists"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=100`, `/closed-trades/summary?address={address}`, `POST /events` (`position_activity` with `filters.coin`)
Use the specialist filter and vetting above to pick 5-10 wallets, then create one `position_activity` rule with those addresses and `"filters": {"coin": ["{COIN}"]}`. Show each delivery with the wallet's per-coin track record.

**"Find high-volume wallets with a losing track record to fade"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=asc&limit=100`, `/closed-trades/summary?address={address}`, `/positions?address={address}&open=true&start=2025-04-04T00:00:00.000Z`
Filter to `totalTrades > 100`, `winRate < 0.4`, `profitFactor < 0.8`, `totalVolumeUsd > 10000000`. Most fall into Exit Liquidity (12), Full Rekt (14) or Giga-Rekt (15). Return them as a fade list with their current open positions.

### Reverse Lookup

**"Whose wallet is behind this Hyperliquid PnL share card?" / "Identify this trader"**
Endpoints: `/positions?coin={coin}&open=true&start=2025-04-04T00:00:00.000Z`, `/wallets?address={address}`
Extract coin, side, leverage, entry price, mark price and ROI from the card. Pull open positions for the coin (keep `start` early, since it filters on open time), filter by side and leverage (±0.5), and rank by entry-price proximity. Tighten to an exact entry match first; widen if there are no hits. Multiple matches are normal. Look up matches via `/wallets?address={address}` (lowercase) for cohorts, equity and PnL.

**"I only have the coin, side, and ROI, no entry price"**
Endpoints: `/positions?coin={coin}&open=true&start=2025-04-04T00:00:00.000Z`, `/wallets?address={address}`
Filter by coin, side and leverage, then rank by how closely each candidate's computed ROI matches the card. Present several candidates; this is a fuzzy match.

**"The card doesn't match any currently open positions"**
Endpoints: `/positions?coin={coin}&open=false&start=...`, `/coin/{coin}/open-positions/history`, `/closed-trades?address={address}`
The card may show a closed trade. Search closed positions over a wider window, or pull an older open-positions snapshot file (available from March 25, 2026). Entry price is still the strongest match dimension.

**"Which cohort is behind a given share card?"**
Endpoints: `/positions?coin={coin}&open=true&start=2025-04-04T00:00:00.000Z`
Match candidates as above and read `profile.segments` on each (one size cohort, one PnL cohort). If every candidate shares a cohort, that's the answer; otherwise show the distribution.

**"Biggest money behind this trade idea, not the specific share card"**
Endpoints: `/leaderboards/biggest-positions?openedWithin=7d`, `/positions?coin={coin}&open=true&start=2025-04-04T00:00:00.000Z`, `/position-metrics/coin/{coin}/segment/{segmentId}`
List the largest open positions on that coin and side, then add the cohort breakdown to show which segments are positioned this way.

### Backtesting

**"Backtest: how did Smart Money positioning on BTC predict price moves since February?"**
Endpoints: `/position-metrics/coin/BTC/segment/9?start=2026-02-19T00:00:00.000Z`
Per-coin cohort metrics run from February 19, 2026. Compute Smart Money's long fraction at each snapshot, correlate changes with subsequent BTC moves, and report hit rate and average return per signal. Compare flows with `totalPositionSize` (coin units) so price moves don't read as buying or selling.

**"Compare all 8 PnL cohorts as predictors of BTC direction over the last 3 months"**
Endpoints: `/position-metrics/coin/BTC/segment/{segmentId}` (IDs 8-15), `/segments/{segmentId}/bias-history?start={90d ago}`
For each cohort, pull 3 months of positioning, correlate exposure changes with subsequent price, and rank cohorts by predictive accuracy.

### Market Regime

**"Is the market in risk-on or risk-off mode right now based on cohort behavior?"**
Endpoints: `/segments/{segmentId}/bias-history`, `/state/summary`, `/{segmentId}/assets/liquidation-risk`
Risk-on: Smart Money and Money Printer net long, low liquidation exposure, rising OI. Risk-off: strong cohorts reducing exposure, rising liquidation exposure, falling OI. Classify and show the supporting data.

**"Daily market regime report: combine cohort bias, OI, and liquidation risk into one summary"**
Endpoints: `/segments/{segmentId}/bias-history`, `/position-metrics/general?start={24h ago}`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`, `/fills/liquidation?start={24h ago}`
Classify as risk-on, risk-off or neutral. Show the 3 strongest supporting signals and 1 contradicting signal.

### Multi-Endpoint

**"Coin screener ranking assets by smart money conviction, order flow health, and liquidation risk"**
Endpoints: `/positions/heatmap`, `/orders/5m-snapshots/latest?start={24h ago}`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`

### Use Case Recipes

Larger end-to-end workflows. Each lists the exact endpoints to call and how to combine them.

**"Give me a 60-second morning market brief on Hyperliquid"**
Endpoints: `/positions/heatmap`, `/position-metrics/general?start={24h ago}&end={now}`, `/leaderboards/perp-pnl?rankBy=pnlDay&orderBy=pnlDay&order=desc&limit=25`, `/orders/5m-snapshots/latest?coin=BTC&start={24h ago}`, `/fills/liquidation?start={24h ago}`
Per-cohort positioning from the heatmap, market health from `/position-metrics/general` (long/short ratio, OI, position count), today's top performers, overnight liquidations, and BTC stop/TP clusters (pass `start` to skip stale 2023-2024 orders). Summarize in plain English: market mood, what the strong cohorts are doing, what today's winners hold, and where BTC order-flow tension is building.

**"What are today's top-earning traders doing differently from everyone else?"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlDay&orderBy=pnlDay&order=desc&limit=100`, `/positions/heatmap`, `/position-metrics/general?start={24h ago}&end={now}`
Pull the top 100 daily wallets. Compare their `pnlWeek` and `pnlMonth` to separate consistent winners from one-day luck. Cross-reference the heatmap to see whether Money Printer (8) and Smart Money (9) are aligned with or against where the leaderboard is positioned.

**"Find the most crowded trade on Hyperliquid right now"**
Endpoints: `/positions/heatmap` (one bulk call), or `/position-metrics/coin/{coin}/segment/{segmentId}?start={1h ago}&end={now}` per coin and cohort
For each coin and PnL cohort (8-15), read the long fraction (`bias` on the heatmap, or `totalPositionValueLong / totalPositionValue`). Flag a cohort as crowded above 0.8 or below 0.2, weight by `totalValue`, and score each coin by how many cohorts crowd the same side. The higher-conviction signal is a disagreement: Smart Money leaning one way while several weaker cohorts lean the other.

**"Build a personal portfolio auditor for my wallet"**
Endpoints: `/wallets?address={address}`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`, `/fundings?address={address}`
Equity, exposure and cohorts from `/wallets`; win rate, profit factor, expectancy and the per-coin breakdown from the summary; per-trade detail and execution quality from `/closed-trades` and its fills; and total funding paid or received per coin from `/fundings` (month by month). Show which assets the wallet is actually good at and what funding cost it.

**"Alpha screener: find and vet top traders before following them"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=100`, `/wallets?address={address}`, `/positions?address={address}&open=true&start=2025-04-04T00:00:00.000Z`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`
Discover candidates from the monthly leaderboard. For each, pull equity and liquidation proximity from `/wallets`, current exposure and leverage from `/positions`, and the track record from `/closed-trades/summary`. Vet with `countFills` and the `30d` interval before ranking by per-coin `expectancy` or `profitFactor`.

**"Macro sentiment and smart money cohort radar"**
Endpoints: `/segments`, `/positions/heatmap`, `/position-metrics/general?start={ISO}&end={now}`, `/position-metrics/coin/{coin}?start={ISO}&end={now}`, `/position-metrics/coin/{coin}/segment/{segmentId}?start={ISO}&end={now}`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`
Cohort definitions from `/segments`, the global directional grid from the heatmap, market health from `/position-metrics/general`, per-coin concentration from `/position-metrics/coin/{coin}`, and per-cohort trend shifts (one point per state update, roughly every 15 to 30 minutes) from the per-cohort series. Add liquidation exposure and network context. Isolate coins where smart money is fading the retail crowd.

**"Systematic exposure analysis and backtesting pipeline"**
Endpoints: `/hypertracker/state/status`, `/positions?start={ISO}`, `/position-metrics/general?start={ISO}&end={now}`, `/position-metrics/coin/{coin}?start={ISO}&end={now}`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`, `/exports/coins/{coin}/liquidation-heatmap`
Check freshness with `/hypertracker/state/status`. Pull positioning from `/positions` (paginate with `nextCursor`), macro OI from `/position-metrics/general` and per-coin exposure from `/position-metrics/coin/{coin}`. Build performance baselines from `/closed-trades/summary`, open/close pairs from `/closed-trades` (30-day windows) and slippage from `/closed-trades/{hash}/fills`. Download liquidation price bins from `/exports/coins/{coin}/liquidation-heatmap`.

**"Structural order flow and liquidation cluster mapper"**
Endpoints: `/orders/5m-snapshots/latest-snapshot-timestamp`, `/orders/5m-snapshots/latest`, `/orders/5m-snapshots/{snapshotTime}`, `/orders/5m-snapshots/coins/{coin}/download`, `/{segmentId}/assets/liquidation-risk`, `/positions/heatmap`, `/exports/coins/{coin}/liquidation-heatmap`
Poll `latest-snapshot-timestamp` to detect each new 5-minute interval, then ingest resting orders from `/latest` (always pass `start` to skip zombie orders) or grab the full coin file from `/coins/{coin}/download`. Compare against snapshots from earlier in the last 30 days. Overlay liquidation exposure and liquidation price bins.

**"Real-time liquidation monitor for my desk"**
Endpoints: WebSocket `rooms:fills` with `{"key": "isLiquidation", "cmp": "eq", "val": "true"}`, `/fills/liquidation` (history), `/wallets?address={liquidatedUser}`
Stream liquidation fills live and count only the liquidated side (`address == liquidation.liquidatedUser`). Aggregate notional per coin and side over rolling 1-minute and 1-hour windows, flag cascades, and enrich large liquidations with the wallet's cohorts. Backfill the time before you connected from `/fills/liquidation`, since stream replay only covers seconds.

**"Whale alerts to Telegram or Discord without running a poller"**
Endpoints: `POST /events/endpoints`, `POST /events` (`liquidation`, `large_market_order`, `ledger_update`)
Register a signed webhook endpoint (your relay), then create rules: liquidations above $1M (`thresholdUsd: "1000000"`), market orders above $5M (`large_market_order`, `thresholdUsd: "5000000"`), and deposits above $10M (`ledger_update`, `types: ["deposit"]`, `amount: {"gte": "10000000"}`). Verify each delivery's signature, dedupe on `deliveryId`, and forward a formatted message to the chat.

**"Price alerts across majors and HIP-3 markets"**
Endpoints: `POST /events` (`price_crossing`)
One rule per level: `{"eventType": "price_crossing", "webhookEndpointId": ID, "filters": {"market": "xyz:GOLD", "threshold": "4200.00", "direction": "both"}}`. Rules fire only on a cross after creation; there is no cooldown, so pause or delete a rule once it has fired if you want one-shot behavior.

**"Push-based wallet-follow feed for a list of wallets"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=100`, `/closed-trades/summary?address={address}`, `POST /events` (`position_activity`, `twap_execution`)
Pick wallets with the discovery recipes, then create one `position_activity` rule (up to 1000 addresses) and a `twap_execution` rule for TWAP slices. Each delivery groups fills by wallet and coin; interpret open/close from `dir` and `startPosition` yourself.

**"Wallet funding audit: how much has funding cost this trader?"**
Endpoints: `/fundings?address={address}&startTime=...&endTime=...`, `/closed-trades?address={address}`
Pull funding month by month (each window at most 1 month), total `fundingAmount` per coin, and compare with realized PnL per coin from closed trades. Flag positions where funding paid ate most of the gain.

**"Keep a dashboard in sync without polling"**
Endpoints: state webhook (`stateUpdated`), `/hypertracker/state/status`, any REST endpoints
Register a state webhook in the API dashboard. On each `stateUpdated` ping, re-fetch the endpoints your dashboard shows. Use `/hypertracker/state/status` as a fallback check if a ping is missed.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 401 Unauthorized | Check the token is valid and sent as `Authorization: Bearer <token>`. On WebSocket, a bad token is refused with `Bad jwt token`. |
| 429 Too Many Requests | Wait `retry_after` seconds, back off exponentially, and pace bulk sweeps. |
| 400 on `/fills` | `address` is required as an array of 1-10 (`address[]=0x...`), `coin` must be an array (`coin[]=BTC`), and `start`/`end` must fall on the same UTC calendar day. |
| 400 `start should not be empty` / `start must be a valid ISO 8601 date string` | `start` is required on `/positions`, `/position-metrics/*` (general, coin, segment, size bucket), `/metrics/perp-volume`, `/fills` and `/builders/{builder}/fills`. |
| Empty list instead of data | Check case: coins are case-sensitive (`BTC`, `xyz:GOLD`), addresses must be lowercase on `/wallets` and `/positions`, and booleans must be the strings `"true"`/`"false"`. |
| Open positions missing from `/positions` | `start` filters on `openTime`; set it earlier (e.g. `2025-04-04T00:00:00.000Z`). |
| Leaderboard shows the wrong period | Set `orderBy` to the same value as `rankBy` and `order=desc`. |
| Same page returned forever | Paginate with `nextCursor`, not `cursor`. |
| Closed trades empty or 400 | Use `startTime`/`endTime` (not `start`/`end`), keep the window at 1 month or less, and remember the default is the last 7 days. |
| Empty order snapshots | Paginated snapshots cover the last 30 days only, on 5-minute boundaries. |
| Snapshot download returns 404 "not available" | Historical files exist only for about January 19 to March 10, 2026; use `/orders/5m-snapshots/{snapshotTime}` (last 30 days) or the per-coin latest download. |
| 0-byte response or broken download | The endpoint redirected to a pre-signed file. Follow redirects (`curl -L`) and fetch `downloadUrl` immediately; links can expire in as little as 30 seconds. |
| `/wallets` returns no items for a real address | Only active wallets are listed (perp volume in the last 30 days or an open position), and the address must be lowercase. Use `/closed-trades/summary` for history. |
| A coin is missing from liquidation risk | Results are sorted by `percentRisk`; page with `offset`. |
| Data looks stale | Most data updates on Hyperliquid state updates (roughly every 15 to 30 minutes). Read `createdAt` and check `/hypertracker/state/status`. |
| Cohort totals look doubled | You summed size and PnL cohorts together. Sum within one axis only. |
| `POST /info` returns 400 "Invalid Hyperliquid wallet address" | Include `user` in the body for every `type`. |
| WebSocket closes with `3008 slow` | Your filter is too broad (always filter `orders:feed`), or your handler is too slow. |
| WebSocket reconnect lost events (`recovered: false` or `3010`) | Replay covers only seconds to minutes. Backfill the gap from REST. |
| Alert rule never fires | Check exact ticker case and prefix (`BTC`, `xyz:NVDA`), that numbers are strings, that `addresses` is top-level, and that the endpoint is not paused or suspended. |
| Deliveries arrive unsigned | Set `secretKey` (not `secret`) on the webhook endpoint. |
| Reverse lookup: no matches | Widen `entry_tolerance_pct` (0.005, then 0.01), check `start` is early enough, and retry with `open=false` for closed positions. |
| Reverse lookup: too many matches | Narrow `entry_tolerance_pct` to 0.0005 and compare each candidate's ROI with the card's ROI. |

## Links

- Dashboard & API key: https://app.coinmarketman.com/hypertracker/api-dashboard?utm_source=skill&utm_medium=ai&utm_campaign=skill-launch
- Plans & pricing: https://app.coinmarketman.com/hypertracker/api
- Docs: https://docs.coinmarketman.com
- WebSocket streams: https://docs.coinmarketman.com/real-time-websocket-streams
- Server-side alerts: https://docs.coinmarketman.com/server-side-alerts
