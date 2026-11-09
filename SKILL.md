---
name: hypertracker
description: Query HyperTracker's pre-computed analytics layer for Hyperliquid. Use when the user asks about Hyperliquid wallets, cohort positioning (Money Printer, Smart Money, Whales, etc.), order flow, closed trades, fundings, liquidations, leaderboards, builder codes, real-time WebSocket streams (including BBO, L2 and L4 order books), server-side alerts or webhooks, or wants to analyze any address or position on Hyperliquid perps (including HIP-3 markets). Requires a JWT bearer token from the HyperTracker API dashboard.
---

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

All REST paths below are relative to this base URL. WebSocket streams use `wss://jp-ws.hypertracker.io/connection/websocket` (see Infrastructure).

## Critical Rules

1. **Dates MUST be ISO 8601.** Example: `2026-02-25T00:00:00.000Z`. Never epoch milliseconds.
2. **Coins are case-sensitive strings.** Main-exchange perps are uppercase tickers: `"BTC"`, `"ETH"`, `"HYPE"`. No USDT suffix. HIP-3 markets (equities, commodities, indices) carry a lowercase dex prefix: `xyz:GOLD`, `xyz:SP500`. Pass them exactly as written; the colon does not need URL encoding. Wrong case (`btc`, `XYZ:GOLD`) returns an empty list, not an error. Position and cohort data cover the dexes listed by `/positions/coins`; some dexes (e.g. `cash:`) appear in fills and liquidations but return empty position data. Exceptions: `/perps/coin/{coin}/segment-metrics` uppercases the coin and only works for main-exchange coins; `/exports/coins/{coin}/*` and `/orders/5m-snapshots/coins/{coin}/download` normalize case (`btc`, `XYZ:gold` work; an unknown coin gives an S3 404 XML body or a 404 "may still be processing" message); `/positions/open/coin/{coin}` and `/coin/{coin}/open-positions/history` take the bare ticker (`GOLD`, not `xyz:GOLD`); `/candles` returns 404 `"Coin btc not found"` for wrong case.
3. **Lowercase wallet addresses.** `/wallets` and `/positions` match addresses case-sensitively: a checksummed or uppercase address returns an empty result. (`/closed-trades/summary`, `/fundings` and `/fills/liquidation` accept any case.)
4. **Boolean query params are lowercase strings.** Send `open=true`, not `open=True`. Python `requests` serializes `True` as `True`, which the API reads as false: `open=True` returns closed positions and `hasOpenPositions=True` returns wallets with no open positions. Pass `"true"`/`"false"` as strings.
5. **Some params must be arrays.** On `/fills` and `/builders/{builder}/fills`, `address` and `coin` (and `builder` on `/fills`) must be sent as arrays of 1 to 10 values: `address[]=0xabc...&coin[]=BTC&builder[]=0x1924...`, or repeat the key (`address=0x1...&address=0x2...`). A single scalar `address=0x...`, `coin=BTC` or `builder=0x...` returns 400 `"... must be an array"`. On `/positions`, repeat `address` for multiple wallets.
6. **`/fills` requires `address` (1 to 10 wallets) and a window inside one UTC calendar day.** There is no market-wide fill pull in REST. A window that crosses midnight UTC returns 400 `"End date must be within the same day as the start date"`. For exchange-wide fills use the WebSocket `rooms:fills` stream; for liquidations use `/fills/liquidation`.
7. **Closed trades and fundings use `startTime`/`endTime`, not `start`/`end`.** The window between them can be at most one month (400 `"endTime - startTime can not be longer then 1 month"` on closed trades, `"... cannot be longer than 1 month"` on fundings). `start`/`end` are silently ignored. The missing bound defaults to now (or now minus 7 days), so passing only a `startTime` more than a month back fails and passing only an `endTime` older than 7 days returns an empty list: set both. The limit is one calendar month, not 30 days (February 1 to March 2 fails), so for longer history loop over consecutive windows of 28 days or less.
8. **Paginate with `nextCursor`.** Pass the response's `nextCursor` back as the `nextCursor` query param. A param named `cursor` is silently ignored and returns page 1 forever. When `nextCursor` is `null` or absent, you have every page.
9. **Default page size varies by endpoint.** 50 for HYPE holders; 100 for orders, closed trades, closed-trade fills, fundings, wallets, builder users and tracked addresses; 250 for liquidation risk; 500 for fills, builder fills, liquidation fills and cohort bias history; 1000 for positions and position metrics; 25 for the perp-PnL leaderboard; 100 for the all-PnL and biggest-positions leaderboards. `/candles` takes `limit` 1-601 and has no cursor. Most endpoints cap `limit` at 1000; closed trades, closed-trade fills, fundings, wallets, liquidation risk and HYPE holders cap at 500; `/leaderboards/perp-pnl` accepts only 25, 50 or 100, while `/leaderboards/all-pnl` and `/leaderboards/biggest-positions` accept 1 to 100.
10. **Leaderboards: set `orderBy` to the same value as `rankBy`.** `orderBy` controls the sort and defaults to `pnlAllTime`; `rankBy` only controls the `rank` number. `?rankBy=pnlDay&limit=25` alone returns the all-time top, not today's. Use `?rankBy=pnlDay&orderBy=pnlDay&order=desc&limit=25`.
11. **Follow redirects and download immediately.** Several endpoints answer with a 302 to a pre-signed S3 file, or return a `downloadUrl` (CSV/JSON exports, snapshot summaries, builder lists, and `/hypertracker/state/status`, whose `status.json` link expires after about 120 seconds). `requests` and `fetch` follow redirects by default; with curl use `-L`. Pre-signed links expire after 30 to 240 seconds (30 seconds for per-coin exports and `/segments/{id}/summary`). A 0-byte body usually means the redirect was not followed.
12. **Most data refreshes on each Hyperliquid state update (about every 30 minutes).** Order snapshots refresh every 5 minutes; see Data Freshness below. Polling faster than the cadence uses your usage allowance without returning new data.

---

## Data Freshness

| Data | Update cadence |
|------|----------------|
| Order snapshots (`/orders/5m-snapshots/*`) | Every 5 minutes |
| Exchange-wide position metrics (`/position-metrics/general`) | About every 10 minutes |
| State, positions, per-coin and per-cohort metrics, heatmap, open-position CSVs | Each state update, about every 30 minutes. Check `GET /hypertracker/state/status` (`lastUpdate`, `nextUpdate`) or subscribe to the state webhook. |
| Cohort bias history (`/segments/{id}/bias-history`) | Stored every 2 hours by default (about every 30 minutes with `positionRecencyTimeframe=24h` and a `start`; a call without `start` is always 2-hourly) |
| Closed trades | About 10 seconds after a trade's final fill |
| 1-second candles (`/candles`) | Near real time (the current second is included and may still be forming) |
| WebSocket streams, server-side alerts | Real time |

Always read the `createdAt` (or snapshot timestamp) on each row instead of assuming the newest row is "now".

---

## Historical Data Availability

| Data | Available from |
|------|----------------|
| Positions (`/positions`) | April 2025 (earliest `openTime` April 7, 2025). Liquidation prices before September 2, 2025 are stored as static values. |
| Exchange-wide position metrics | May 2025 |
| Per-coin metrics, all cohorts (`/position-metrics/coin/{coin}`) | Rolling ~31 days. For older data use the per-cohort endpoint or `/exports/coins/{coin}/position-metrics`. |
| 1-second candles (`/candles`) | May 25, 2025 for main-exchange perps; HIP-3 markets from listing |
| Fills, closed trades, builder fills | July 2025 |
| Liquidation fills (`/fills/liquidation`) | July 27, 2025, queried in windows of up to 3 months |
| Fundings (`/fundings`) | September 27, 2025 |
| Exchange perp volume (`/metrics/perp-volume`) | August 25, 2025 |
| Cohort bias history | July 9, 2025 (`all`); December 1, 2025 for `24h`/`7d`/`30d`. A call with no `start` returns the last ~60 days of `all` data at 2-hour spacing; pass `start`/`end` for older ranges. |
| Per-coin cohort metrics (`/position-metrics/coin/{coin}/segment/{id}`) | February 19, 2026 (`positionRecencyTimeframe=all`); March 19, 2026 for `24h`/`7d`/`30d` |
| Open-position snapshot files (`/coin/{coin}/open-positions/history`) | March 25, 2026 |
| Order snapshots, paginated (`/orders/5m-snapshots/{snapshotTime}`) | Rolling 30-day window. Older timestamps return an empty list. |
| Wallet equity history (`/exports/total-wallets-equity-chart-data`) | January 8, 2026, about one point per day |
| Leaderboards | Live endpoints return the current snapshot; past snapshots are available as CSV files via `/leaderboards/{leaderboard}/{timeframe}/snapshots/history` |
| Heatmap, liquidation risk, wallet profiles | Current snapshot only (wallet profiles carry trailing 24h/7d/30d/all-time performance fields) |

---

## Cohort Segments

HyperTracker classifies each active wallet on Hyperliquid into two cohorts at once: one by size (perp margin equity, `perpMarginEquity`) and one by performance (all-time perp PnL). Active means non-zero perp volume in the last 30 days or an open position.

### Size-Based Cohorts (by Perp Margin Equity)
| ID | Name | Perp Margin Equity |
|----|------|-------------|
| 16 | Shrimp | $0 - $250 |
| 1 | Fish | $250 - $10K |
| 2 | Dolphin | $10K - $50K |
| 3 | Apex Predator | $50K - $100K |
| 4 | Small Whale | $100K - $500K |
| 5 | Whale | $500K - $1M |
| 6 | Tidal Whale | $1M - $5M |
| 7 | Leviathan | $5M+ |

Size bands apply to `perpMarginEquity`, which can exceed plain `perpEquity` when spot USDC backs a unified account. `perpEquity` is plain perp equity across all dexes and can be far lower (often `0`) for a wallet in a high size cohort.

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

**GET /segments/{segmentId}/bias-history**: Bias history for one cohort, exchange-wide across all coins. Params: `segmentId` (path), `start`, `end`, `limit` (max 1000), `nextCursor`, `positionRecencyTimeframe` (`24h`, `7d`, `30d`, `all`; default `all`). `start` is required whenever `limit`, `end` or `nextCursor` is set, otherwise 400 `"'start' query param is required for 'end', 'nextCursor' and 'limit' query params"`. `limit` defaults to 500 (max 1000). Without `start` the call returns the last ~60 days of `all` data at 2-hour spacing: `positionRecencyTimeframe` is ignored even though the response echoes it, and the response's `start`/`end` hold the newest and oldest row times. Pass `start` to apply a timeframe. A segment ID outside 1-16 returns 500. The `history` field is an array of arrays whose column order is given by `historySnapshotStructure`: `[timestamp, bias, exposureRatio, openValue, openLongValue, openShortValue, activePerpEquity]`. Rows are newest first. `bias = (openLongValue - openShortValue) / activePerpEquity` (signed, positive = net long, can exceed 1 in magnitude); `exposureRatio = openValue / activePerpEquity`. This is a different scale from the per-coin `bias` in `/positions/heatmap`. Call once per segment ID to cover all cohorts.

**GET /segments/{segmentId}/summary**: Per-cohort snapshot of currently open positions. Params: `segmentId` (path), `positionAge` (`all`, `24h`, `7d`, `30d`; default `all`). Returns `segment`, `openPerpsSummary` (`perpBias`, `exposureRatio`, `countOpenPositions`, `countTradersInPosition`, `countTradersInProfit`, `totalValue`, `totalLongValue`, `totalActivePerpEquity`, `bySide`, `totalPerpEquity`, `countAssets`) and `summary` (`countTraders`, `countTradersInPosition`, `perpBias`, `positionValue`, `positionLongValue`, `positionShortValue`, `exposureRatio`, `activePerpEquity`, `perpEquity`). Both blocks also carry margin-equity variants computed the same way with margin equity as the denominator: `totalActivePerpMarginEquity`, `totalPerpMarginEquity`, `marginPerpBias`, `marginExposureRatio` in `openPerpsSummary`; `segmentId`, `activePerpMarginEquity`, `perpMarginEquity`, `marginPerpBias`, `marginExposureRatio` in `summary`. Served via redirect to a pre-signed file. `positionAge` and `segmentId` are not validated: an unknown value redirects to a missing file (S3 404 XML). The `24h`/`7d`/`30d` files omit `countTraders`, `perpEquity`, `perpMarginEquity`, `totalPerpEquity`, `totalPerpMarginEquity` and `countAssets`.

**GET /position-metrics/coin/{coin}/segment/{segmentId}**: Per-coin, per-cohort time series. Works for all 16 segments and for HIP-3 coins (`xyz:GOLD`). Params: `coin`, `segmentId` (path), `start` (**required**), `end`, `limit`, `nextCursor`, `positionRecencyTimeframe` (`all`, `24h`, `7d`, `30d`; default `all`; counts only positions opened within that window at each snapshot). Returns `{metrics: [...]}`, newest first. Each row: `createdAt`, `coin`, `segmentId`, `positionCount`, `positionCountLong`, `totalPositionValue`, `totalPositionValueLong`, `totalPositionSize`, `totalPositionSizeLong`, `totalFunding`, `totalUnrealizedPnl`. Long fraction = `totalPositionValueLong / totalPositionValue` (equals the heatmap's per-cohort `bias`). One row per state update (about 30 minutes). Wrong-case coins and segment IDs outside 1-16 return 200 with an empty `metrics` array.

**GET /state/summary**: Exchange snapshot that powers the HyperTracker homepage: `countTraders`, `countActiveTraders`, `countTraders24HoursAgo`, `segments` (plus `segments24h`, `segments7d`, `segments30d`), `perpPositionsMetrics` (`count`, `openInterest`), `perpVolume` and 24-hours-ago comparisons. `segments` rows: `segmentId`, `segment`, `countTraders`, `countTradersInPosition`, `perpBias`, `positionValue`, `positionLongValue`, `positionShortValue`, `perpEquity`, `activePerpEquity`, `exposureRatio`, plus `perpMarginEquity`, `activePerpMarginEquity`, `marginPerpBias`, `marginExposureRatio`. The `segments24h`/`7d`/`30d` rows omit `segment`, `countTraders`, `perpEquity` and `perpMarginEquity`. `perpPositionsMetrics24HoursAgo` adds `perpEquity`, `perpMarginEquity` and `countInProfit`. Current snapshot only. Served via redirect to a pre-signed file (about 120 seconds).

### Positions & Market Exposure

**GET /positions**: Positions with pre-computed cohort data. Params: `start` (**required**), `end`, `coin`, `segmentId`, `address` (repeat for multiple: `address=0x1...&address=0x2...`), `open` (`"true"`/`"false"`; omit for both), `limit` (default and max 1000), `nextCursor`. **`start` filters on each position's `openTime`**: a position opened before `start` is excluded even if it is still open. To get every currently open position, set `start` before the oldest position you care about (e.g. `2025-04-04T00:00:00.000Z`). Results are sorted by `openTime` ascending. Each position appears once, as one consolidated record (not a state-by-state history). Fields: `id`, `address`, `coin`, `dex`, `side` (`"long"`/`"short"`), `size`, `entryPrice`, `markPrice`, `midPrice`, `premiumPrice`, `positionValue`, `liquidationPrice`, `unrealizedPnl`, `funding`, `crossLeverage`, `isolatedLeverage`, `maxLeverage`, `assetMaxLeverage`, `szDecimals`, `openTime`, `closeTime` (`null` while open), `createdAt`, `updatedAt`, `profile` (`{address, segments}`, where `segments` holds the wallet's two cohort IDs). Positions are captured at state updates, so very short-lived positions can be missing: use `/closed-trades` for trade counts, win rate, hold time or realized PnL.

**GET /positions/coins**: Market-wide summary per coin: `totalValue`, `totalValueLong`, `totalValueShort`, `count`, `countLong`, `countShort`, sorted by `totalValue` desc. No params. `totalValueLong` equals `totalValueShort` at this level because every long has a matched short; use `countLong`/`countShort` for crowding and per-cohort data (`/positions/heatmap`) for directional notional. Also a quick way to list every coin, HIP-3 markets included.

**GET /positions/open/coin/{coin}**: Latest open-position snapshot for a coin as CSV. 302 redirect to a pre-signed file (about 120 seconds). The path `coin` is the bare ticker, case-insensitive, and the file holds that ticker on every dex (`GOLD` returns `xyz:GOLD` rows; `AAPL` returns `xyz:AAPL` and `io:AAPL`), so filter on the `coin`/`dex` columns. A dex-prefixed coin (`xyz:GOLD`) returns 404. Columns: `id, address, coin, side, dex, size, value, entryPrice, unrealizedPnl, funding, liquidationPrice, liquidationProgress, crossLeverage, isolatedLeverage, openTime`, plus wallet columns prefixed `profile_` (`profile_totalEquity`, `profile_perpEquity`, `profile_countOpenPositions`, `profile_pnl`, `profile_balance`, `profile_perpPnlSegmentId`, `profile_sizeSegmentId`). Refreshed each state update. Large coins produce files over 10 MB.

**GET /coin/{coin}/open-positions/history**: Point-in-time open-position snapshot files for a coin. Params: `coin` (path), `start`, `end`, `nextCursor`. Use the bare ticker (`GOLD`; the prefixed form returns `snapshot: null`). `start`/`end` match each snapshot's `completedAt`; `limit` is ignored. A new snapshot lands about every 30 minutes. Each response holds **one** snapshot: `{coin, snapshot: {snapshotId, coin, stateVersion, rowCount, status, format, createdAt, completedAt, downloadUrl}, nextCursor}`. Returns the newest snapshot at or before `end`, then pages backward in time. `downloadUrl` expires after about 120 seconds. Earliest snapshot: March 25, 2026. For positions back to April 2025, use `GET /positions`.

**GET /position-metrics/general**: Exchange-level OI and position counts over time. Params: `start` (**required**), `end`, `limit`, `nextCursor`. Rows: `createdAt`, `count`, `countLong`, `countShort`, `openInterest`, `openInterestLong`, `openInterestShort`, `perpEquity`, `countInProfit`.

**GET /position-metrics/coin/{coin}**: Per-coin long/short breakdown over time (all cohorts combined). Params: `coin` (path, exact case, HIP-3 prefix required), `start` (**required**), `end`, `limit` (max 1000), `nextCursor`. Same row fields as the per-cohort endpoint without `segmentId`, plus `id`. Rolling retention of about 31 days.

**GET /position-metrics/coin/{coin}/position-size-bucket/{sizeBucketId}**: Per-coin metrics by individual position size bucket (IDs 1-10, from under $1K to over $2.5M), independent of cohorts. Params: `coin`, `sizeBucketId` (path), `start` (**required**), `end`, `limit`, `nextCursor`, `positionRecencyTimeframe` (`24h`, `7d`, `30d`, `all`; default `all`; same meaning as on the per-cohort endpoint).

**GET /candles**: 1-second OHLCV candles for one perp market, built from Hyperliquid fills (summed to a minute they match Hyperliquid's 1m candles, trade count included). Params: `coin` (**required**; exact case: `BTC`, `xyz:GOLD`, `io:AAPL`), `start` (**required**, inclusive), `end` (**required**, exclusive), `limit` (1-601; default the whole range; keeps the first N candles from `start`). `start`/`end` need a timezone (`Z` or `+00:00`): a value without one, a date-only value or epoch milliseconds returns 400 `"start must carry a timezone, e.g. a trailing Z"`. The window is at most 600 seconds (400 `"1s candles cover at most 600 seconds per request..."`) and `end` must be after `start`. Resolution is fixed at 1 second: there is no interval param (unknown params are ignored) and no cursor, so loop over consecutive 600-second windows for longer ranges and aggregate client-side. Bounds off whole seconds are widened, so a 600-second window can return 601 candles. A future `end` is clamped to now, but the 600-second check uses the `end` you sent. Returns `{candles: [...]}` sorted by `dateOpen` ascending. Each candle: `dateOpen`, `dateClose` (ISO, second precision), `open`, `high`, `low`, `close`, `volumeBase` (coin units), `volumeQuote` (USD), `tradeCount`, `synthetic`. A second without trades has `synthetic: true`, OHLC equal to the previous close and zero volume. Wrong case or an unknown coin returns 404 `"Coin btc not found"`; spot pairs (`@107`, `HYPE/USDC`) are not supported. Delisted or untracked markets, ranges before the data start (May 25, 2025 for main-exchange perps) and ranges entirely in the future return 200 with an empty list.

**GET /perps/coin/{coin}/segment-metrics**: All 16 cohorts for one coin in a single call: `{coin, segments: [{segment, metrics: [...]}]}`. `metrics[0]` is the current snapshot; the following entries are 12-hour snapshots covering about 7 days. Rows carry no timestamp (`positionCount`, `positionCountLong`, `totalPositionValue`, `totalPositionValueLong`, `bias`); use `/exports/coins/{coin}/segment-metrics` when you need the times. Main-exchange coins only: the path coin is uppercased, so HIP-3 coins return 404 (`"XYZ:GOLD not found"`); use `/position-metrics/coin/{coin}/segment/{segmentId}` for them. Remember the two-axis rule above before summing.

### Position Heatmap

**GET /positions/heatmap**: Per-coin, per-cohort positioning across the whole exchange in one call. Params: `openedWithin` (`24h`, `7d`, `30d`, `all`; default `all`). Returns `{heatmap: [...]}` with one entry per coin (~350, HIP-3 markets included, sorted by `totalValue` desc): `coin`, `totalValue`, `totalLongValue`, `totalShortValue`, `count`, `countLong`, `countShort`, and a `segments` array with one row per cohort that holds the coin (up to 16; cohorts with no position are omitted). Each segment row has `segmentId`, `coin`, `totalValue`, `totalLongValue`, `totalShortValue`, `count`, `countLong`, `countShort` and `bias`. Per-cohort `bias` is a long fraction in `[0, 1]`: `totalLongValue / (totalLongValue + totalShortValue)`, where `0.5` is neutral. At coin level with `openedWithin=all`, `totalLongValue` equals `totalShortValue` (matched open interest); use the segment rows for direction. An invalid `openedWithin` returns 400. Current snapshot only. The `coin` query param is ignored, so filter client-side. The response is close to 1 MB; if your environment caps response size (e.g. ChatGPT Custom GPT Actions), call `/position-metrics/coin/{coin}/segment/{segmentId}` per cohort with a 1-hour window instead and compute `totalPositionValueLong / totalPositionValue`.

### Order Flow

**GET /orders/5m-snapshots/latest**: The most recent 5-minute snapshot of every open order. Params: `coin`, `address`, `oid`, `orderType`, `start`, `end`, `limit` (default 100, max 1000), `nextCursor`. `orderType` enum: `Limit`, `Stop Limit`, `Stop Market`, `Take Profit Limit`, `Take Profit Market` (URL-encode the spaces). Default ordering returns the oldest orders first: pages of GTC limits and triggers from 2023-2024 that never filled. For fresh order flow, pass `start` set to a recent timestamp (e.g. 24 hours ago). `start`/`end` filter each order's placement `timestamp`, not `snapshotTs`. An unfiltered snapshot can exceed 350,000 orders. `side` is the order side (`B` buy, `A` sell), not the position side: a sell stop with `reduceOnly: true` protects a long, a buy stop with `reduceOnly: true` protects a short. Use `triggerPx` for stop and take-profit levels.

**GET /orders/5m-snapshots/{snapshotTime}**: Historical snapshot at a specific time. Params: `snapshotTime` (path, ISO 8601 on a 5-minute boundary, within the last 30 days, not in the future), plus the same filters as `/latest`. Timestamps older than ~30 days pass validation but return an empty list.

**GET /orders/5m-snapshots/latest-snapshot-timestamp**: The newest available snapshot timestamp, as a bare ISO string. Poll this to detect new 5-minute intervals.

**GET /orders/5m-snapshots/coins/{coin}/download**: Download link for the **latest** 5-minute open-orders snapshot of one coin. Returns `{downloadUrl}` pointing to a gzip-compressed JSON array of orders (several MB for BTC), served as `application/gzip` without a `Content-Encoding` header, so HTTP clients do not decompress it automatically: gunzip the bytes before parsing. The link expires after about 240 seconds. The coin is case-insensitive; HIP-3 needs the prefix (`xyz:GOLD`). Rows carry `snapshotTime` and `timestamp` as epoch milliseconds (not ISO) and no `snapshotTs`. An unknown coin returns the same 404 "may still be processing" message as a missing file.

**GET /orders/5m-snapshots/{snapshotTime}/download**: Download link for a full historical 5-minute snapshot as an LZ4-compressed JSON file (`.json.lz4`, an LZ4 frame of about 24 MB holding a JSON array with epoch-millisecond `snapshotTime`/`timestamp`). `snapshotTime` must be on a 5-minute boundary. `snapshotTime` must be on or after 2026-01-19 11:05 UTC, and files currently exist only for about January 19 to March 12, 2026; later timestamps return 404 `"Snapshot file is not available at the moment..."`. For recent history use `/orders/5m-snapshots/{snapshotTime}` (last 30 days) or the per-coin latest download.

### Liquidation Data

**GET /fills/liquidation**: Raw liquidation fills across Hyperliquid. Without `start` the newest fills come first (all markets); **with `start` results run oldest first from `start`**. Params: `coin` (single string; `coin[]` returns 400), `address` (single string, any case), `side` (`A`/`B`), `start`, `end` (only together with `start`, at most 3 months after it; defaults to 3 months after `start`, capped at now), `limit` (default 500, max 1000), `nextCursor`. Returns `{fills: [...]}`; each fill carries the normal fill fields plus `liquidatedUser`, `liquidationMarkPx` and `liquidationMethod`. Only the liquidated wallet's fill is returned (`address == liquidatedUser` on every row), so no counterparty filtering is needed. A liquidated long shows `dir: "Close Long"`, `side: "A"`. Covers HIP-3 markets (`xyz:MSTR`, `cash:HOOD`). Data from July 27, 2025.

**GET /{segmentId}/assets/liquidation-risk**: Per-coin liquidation exposure for one cohort. Params: `segmentId` (path), `offset`, `limit` (up to 500). Returns `{totalCount, items: [{coin, totalValue, riskValue, percentRisk}]}` (HIP-3 coins included; an unknown `segmentId` returns an empty list). `percentRisk` is a percentage (`4.82` = 4.82%): the share of the cohort's open value on that coin that sits within 75% of its liquidation threshold; `riskValue` is that value in USD. Sorted by `percentRisk` descending, so majors with low risk can sit deep in the list: page with `offset` until your coin appears. A coin missing from page 1 does not mean zero exposure.

**GET /exports/coins/{coin}/liquidation-heatmap**: Price bins of potential liquidations for a coin. Redirects to a pre-signed file (about 30 seconds). Returns `{coin, heatmap: [{priceBinIndex, priceBinStart, priceBinEnd, liquidationValue, positionsCount, mostImpactedSegment}]}`; `mostImpactedSegment` is a cohort ID. Bins are about 0.6% of the mark price wide, from 0 to about twice the mark, and empty bins are omitted. HIP-3 needs the prefix (`xyz:GOLD`).

### Leaderboards

**GET /leaderboards/perp-pnl**: Traders ranked by perp PnL. Params: `rankBy`, `orderBy`, `order` (`asc`/`desc`, default `desc`), `limit` (25, 50 or 100; default 25), `offset`. `rankBy`/`orderBy` enum: `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay` (both default to `pnlAllTime`; set both, see Critical Rule 10). Returns `{totalCount, data: [...]}` with `address`, `rank`, `previousRank`, `perpEquity` (plain perp equity), `perpMarginEquity`, `openValue`, `openValueLong`, `exposureRatio` (`openValue / perpMarginEquity`), `bias`, `pnlDay`/`pnlWeek`/`pnlMonth`/`pnlAllTime`, `volume*` and `pnlPercent*`. The per-trader `bias` is not bounded to [-1, 1] and is not comparable to cohort bias. The ranking covers hundreds of thousands of wallets; page deeper with `offset`.

**GET /leaderboards/all-pnl**: Traders ranked by total PnL across perps, spot and vaults. Params: `rankBy`, `orderBy`, `order` (all **required**; same enums as above), `limit` (1-100, default 100), `offset`. Returns `totalCount`, `sumPnl`, `assetsDistribution` and `data` (`address`, `age` as an ISO timestamp of the wallet's first activity, `totalValue`, `stableValue`, `topHolding`, `pnlAllTime`, `pnlMonth`, `pnlWeek`, `pnlDay`, `rank`, `previousRank`, `profile`).

**GET /leaderboards/perp-pnl/{period}/download**: Full perp-PnL leaderboard file for a period. `period` (path): `all`, `30d`, `7d`, `24h`. Returns `{downloadUrl}` (link valid about 240 seconds) to a JSON array of up to 25,000 rows sorted by that period's PnL desc (row order is the rank). Row fields: `address`, `perpEquity` (plain), `openValue`, `openValueLong`, `pnlDay`/`pnlWeek`/`pnlMonth`/`pnlAllTime`, `volume*` and `pnlPercent*`; no `rank`, `bias`, `exposureRatio` or `perpMarginEquity`.

**GET /leaderboards/{leaderboard}/{timeframe}/snapshots/history**: Past leaderboard snapshots as CSV files. `leaderboard` (path): `perp_pnl`, `all_pnl`, `avg_daily_perp_pnl`, `biggest_positions`, `top_claimed`, `referrals`, `hype_holders`, `rich_list`, `most_favorited`, `vaults`, `builders`. `timeframe` (path): `24h`, `7d`, `30d`, `all`. Optional `start`, `end`, `nextCursor`. Without params it returns the latest completed snapshot; with them, each call returns one snapshot (the newest at or before `end`) plus a `nextCursor` that pages back in time. Returns `{leaderboard, timeframe, snapshot: {snapshotId, leaderboard, timeframe, snapshotAt, stateVersion, rowCount, status, format: "csv", createdAt, completedAt, downloadUrl}, nextCursor}`. `downloadUrl` is a short-lived pre-signed link, so download it right away. The `perp_pnl`/`all` file holds 10,000 rows.

**GET /leaderboards/biggest-positions**: The largest open perp positions on Hyperliquid, ranked by absolute USD notional. Params: `offset` (0-based), `limit` (1-100, default 100), `openedWithin` (`24h`, `7d`, `30d`, `all`). Returns `{totalCount, items: [...]}`. `value` is signed (positive = long, negative = short) and ranking uses `abs(value)`, so a -$31M short ranks above a +$22M long. Each item includes `rank`, `previousRank`, `side`, `address`, `dex`, `coin`, `size`, `entryPrice`, `markPrice`, `midPrice`, `premiumPrice`, `unrealizedPnl`, `funding`, `liquidationPrice`, `liquidationProgress`, `crossLeverage`, `isolatedLeverage`, `openTime` and a full `profile` (`totalEquity`, `balance` (equals `totalEquity`), `perpEquity` (plain), `perpMarginEquity`, `countOpenPositions`, `pnl`, `segments`, `walletLeverage` (open value / `perpEquity`), `marginWalletLeverage` (open value / `perpMarginEquity`, comparable to the `/wallets` `exposureRatio`), `displayName`, `showName`, `verified`). Includes HIP-3 markets. `order` is ignored; an invalid `openedWithin` or `limit` above 100 returns 400.

### Trader & Wallet Data

**GET /wallets**: Wallet profiles, balances, performance and risk for active wallets, one call for a single wallet or a whole cohort. Params: `address` (lowercase), `segmentIds` (integers; repeat the key or use `segmentIds[]=` for several cohorts, which returns their union; a comma list returns 400), `hasOpenPositions` (`"true"`/`"false"`), `orderBy` (`address`, `totalEquity`, `earliestActivityAt`, `perpPnl`, `perpEquity`, `perpMarginEquity`, `perpBias`, `openValue`, `sumUpnl`, `closestLiqProgress`, `countOpenPositions` (sorts by `countOpenPerps`), `exposureRatio`; default `openValue`), `order` (`asc`/`desc`, default `desc`; ignored unless `orderBy` is set), `offset`, `limit` (default 100, max 500). Returns `{totalCount, items}`. Item fields:
- Identity: `address`, `segments` (`[sizeCohortId, pnlCohortId]`), `displayName`, `showName` (`{text, emoji}`), `emoji`, `xUserId`, `verified`, `favoriteCount`, `earliestActivityAt`, `walletAge` (whole days), `vault`.
- Equity (USD): `totalEquity`; `perpEquity` (plain perp equity across all dexes); `perpMarginEquity` (margin equity, can exceed `perpEquity` when spot USDC backs a unified account; the basis for size cohorts); `spotEquity`, `stakeEquity`, `vaultEquity`; one `<dex>Equity` per HIP-3 dex (`xyzEquity`, `cashEquity`, ...; new dexes add keys, `0` when empty).
- Exposure: `openValue`, `sumUpnl`, `exposureRatio` (`openValue / perpMarginEquity`), signed `perpBias`, `closestLiq` (`{coin, progress}`).
- Performance, each with the suffix `24h`, `7d`, `30d` or `All`: `perpPnlUsd*`, `perpPnlPercent*`, `combinedPnlUsd*`, `combinedPnlPercent*`, `perpVolume*`, `combinedVolume*`, `peakPerpEquity*`, `peakCombinedEquity*` (`combined*` covers the whole wallet; `perpPnl` equals `perpPnlUsdAll`). Percent fields are already percentages (`6.67` means 6.67%), unlike the 0-1 `winRate` on `/closed-trades/summary`. These fields cannot be used in `orderBy` (400); rank by period with `/leaderboards/perp-pnl`.
- Activity: `countOpenPerps`, `countHoldings` (nonzero spot tokens, outcome tokens excluded), `countOutcomes`, `countFills30d` (previous 30 complete UTC days), `countOpenOrders` (from the 5-minute order snapshot), `refCode`, `countReferrals`.

Treat `null` as unavailable, never as zero: `perpBias` and `exposureRatio` are `null` without open positions, `closestLiq` is `{coin: null, progress: null}`, and percent fields are `null` when the base is zero. Only active wallets are included (perp volume in the last 30 days or an open position). An inactive or unknown address returns 200 `{"totalCount": 0, "items": []}`, not 404; fall back to `/closed-trades/summary?address=` for its history.

**Wallets in a cohort** (same endpoint): `segmentIds=8` lists the Money Printers, `segmentIds=5` the Whales, with no other filter required. Leave `hasOpenPositions` unset for a complete watchlist (members without positions are included, so you see them when they next trade). For a stable full list use `orderBy=address&order=asc&limit=500` and raise `offset` by `items.length` until it reaches `totalCount`; dedupe addresses. Membership changes with each state update, so refetch the full list on the state webhook (see Code Patterns: Cohort watchlist).

**GET /fills**: Trade executions for specific wallets. Params: `address[]` (**required**, 1 to 10 wallets), `start` (**required**), `end` (same UTC calendar day; defaults to now), `coin[]` (array, at most 10), `builder[]` (array, 1 to 10 builder addresses), `side` (`A` sell, `B` buy), `limit` (default 500, max 1000), `nextCursor`. Returns `{fills, nextCursor}`, including spot fills (spot coins appear as `@142` with `fullCoinName` and `fillType`). History from July 2025.

**GET /fundings**: Funding payments received or paid by a wallet. Params: `address` (**required**, any case), `coin` (HIP-3 supported), `startTime`, `endTime` (at most one calendar month apart, so use windows of 28 days or less; defaults to the last 7 days), `limit` (default 100, max 500), `nextCursor`. Returns `{fundings: [{time, blockNumber, address, coin, fundingAmount, szi, fundingRate}], nextCursor}`. `fundingAmount` is positive when received and negative when paid. History from September 27, 2025.

### Closed Trades

HyperTracker reconstructs complete closed trades from every raw Hyperliquid fill, about 10 seconds after a trade's final fill. History from July 2025. A closed trade is one position lifecycle on one coin (opened from flat, closed back to flat); scale-ins and partial exits are folded into that one trade.

**GET /closed-trades**: Closed trades for a wallet. Params: `address` (**required**), `startTime`, `endTime` (close-time window, at most one calendar month apart; defaults to the last 7 days), `limit` (default 100, max 500), `nextCursor`. For full history, loop over consecutive windows of 28 days or less (the limit is one calendar month), paginate each with `nextCursor`, and dedupe on `id`. Returns `{trades, nextCursor}`. Each trade: `address`, `hash`, `id`, `firstFillId`, `lastFillId` (all strings), `side`, `coin`, `avgEntry`, `avgExit`, `duration` (ms), `openTime`, `closeTime`, `partial`, `totalSize`, `totalUsd`, `realizedPnlUsd`, `countFills`, `fee`, `feeUsd`, `fundingUsd`, plus price excursion: `maePrice`/`mfePrice` (worst and best price reached while the trade was open: low/high for a long, high/low for a short) and `maePercent`/`mfePercent` (that move as a percent of `avgEntry`, never negative, `5` means 5%). The four excursion fields are `null` when price-path data is unavailable.

**GET /closed-trades/summary**: Aggregate analytics for a wallet's closed trades, overall and per coin. Params: `address` (**required**; any case is accepted), `interval` (`all`, `365d`, `180d`, `90d`, `30d`, `last50`; default `all`). Returns `address`, `range` (`allTime`, `last365Days`, `last180Days`, `last90Days`, `last30Days` or `last50Trades`), `updatedAt`, a `summary` object and a `coins` array with the same metrics per asset (only coins traded within the interval). Metrics: trade counts (`totalTrades`, `wins`, `losses`, `longTrades`, `shortTrades`), `winRate` (0-1 float), durations (`avgDuration`, `medianDuration` in milliseconds), PnL (`totalWinningPnl`, `totalLosingPnl`, `netPnl`), gain/loss stats (`avgGain`, `avgLoss`, `medianGain`, `medianLoss`), quality ratios (`profitFactor`, `payoffRatio`, `expectancy`, `expectancyPct`) and size/cost stats (`avgTradeSize`, `medianSizeUsd`, `totalFeesPaid`, `totalVolumeUsd`). Each `coins[]` entry also has `volumeSharePct`. `coins[]` is sorted by `totalTrades` descending. `interval=last50` also returns `dateRange: {fromOpenTime, toCloseTime}`, which is absent for every other interval. Null rules (verified on prod): with zero wins, `avgGain`, `medianGain`, `payoffRatio`, `expectancy` and `expectancyPct` are `null` and `profitFactor` is `0`; with zero losses, `avgLoss`, `medianLoss`, `profitFactor`, `payoffRatio`, `expectancy` and `expectancyPct` are `null`; with zero trades, `winRate`, durations, every ratio, `avgTradeSize` and `medianSizeUsd` are `null` and `coins` is `[]`. Guard for nulls. The summary does not expose fill counts: a wallet that never goes flat can show a handful of "trades" built from thousands of fills, so check `countFills` on `/closed-trades` before treating a win rate as a discretionary track record.

**GET /closed-trades/{hash}**: One closed trade by hash. Params: `hash` (path, **required**). Returns the same object as a `/closed-trades` item, without a wrapper. A malformed hash returns 400 `"Invalid trade hash"`; a well-formed hash that does not exist returns 404.

**GET /closed-trades/{hash}/fills**: The fills behind one closed trade. Params: `hash` (path, **required**), `startTime`, `endTime`, `limit` (default 100, max 500), `nextCursor`. Returns `{fills, nextCursor}` with the normal fill fields plus `createdAt`, `id`, `blockNumber` and `twapId` (integer, `0` on non-TWAP fills); liquidation fills carry `liquidatedUser`, `liquidationMarkPx`, `liquidationMethod`.

### Volume & Stats

**GET /metrics/perp-volume**: Exchange-wide perp volume over time (one total, not per coin). Params: `start` (**required**), `end`, `limit`, `nextCursor`. Returns `{metrics: [{id, createdAt, volume}], nextCursor}`, roughly hourly. History from August 25, 2025.

**GET /exports/total-wallets-equity-chart-data**: Equity history across all wallets. Redirects (about 120 seconds) to JSON with `athData` and `data24HoursAgo` (`{columns, data}` over `totalWalletsEquity`, `perpWalletsEquity`, `spotWalletsEquity`, `stakingWalletsEquity`, `vaultWalletsEquity`, `perpMarginWalletsEquity`) and `history` (`timestamp` plus the same six columns, about one point per day, from January 8, 2026).

### $HYPE Token

**GET /hype/holders**: HYPE holders with balances, staking and comparisons. Params: `address` (array; look up one or more wallets' HYPE position, e.g. `?address=0x...` returns `totalCount: 1`), `offset`, `limit` (default 50, max 500), `order` (`asc`/`desc`, default `desc`), `orderBy` (`totalAmount`, `spotAmount`, `stakedAmount`, `totalAmountUsd`, `spotAmountUsd`, `stakedAmountUsd`, `accountValue`, `earliestActivityAt`), `rankBy` (same values), `rankOrder` (default `desc`). Set `rankBy` to the same field as `orderBy`, otherwise `rank` keeps the `totalAmount` ranking. Returns `{items, totalCount}`; items carry `address`, `spotAmount`, `stakedAmount`, `totalAmount` (HYPE) with `*Usd` values, `accountValue`, `earliestActivityAt`, `percentOfCirculatingSupply` (percent units), `rank`, `previousRank`, a `wallet` profile (can be absent) and `history` with `24h` and `7d` balance snapshots for change calculations.

### Builders

**GET /builders/list/timeframe/{timeframe}**: All Hyperliquid builders for a timeframe, sorted by `revenue` desc. `timeframe` (path): `24h`, `7d`, `30d`, `all` (anything else returns 400 `Invalid timeframe`). Returns `{builders: [{refCode, address, revenue, timeJoined, createdAt, usageFee, users, volume, revenuePrev, volumePrev, usersPrev, previousRank}]}`. The `*Prev` fields are absent on `all`, and `refCode` is often `null`. Redirects to a pre-signed file (about 120 seconds).

**GET /builders/{builder}/profile**: Full profile for a builder address (any case). Redirects to a pre-signed file (about 240 seconds); an unknown builder returns 404 with an S3 XML body. Keys: `info` (`address`, `code`, `name`, `url`, `xUrl`, `xUserId`, `xUser`, `firstActivityAt`, `revenue`), `hyperliquidVolume24h`, `fee`, `biggestDay` (`{revenue, date}`), `revenueMilestones` (`[{revenue, label, done, date, progressPercent}]`); columnar `{columns, data}` blocks per `24h`/`7d`/`30d`/`all`: `analytics` (`[revenue, users, timestamp]`; hourly for 24h, daily otherwise, newest first), `coinVolumeDistribution` (`[coin, volume, numWallets, exchangeType]`, top 8), `userVolumeDistribution` (`[numWallets, volume, minVolume, maxVolume, percentileGroup]`); then `totalAnalytics` (`1h`/`24h`/`7d`/`30d`/`all` of `{revenue, volume, countUsers}`), `totalAnalyticsPrev` (`1h`/`24h`/`7d`/`30d`) and `numProfitableUsers` (`24h`/`7d`/`30d`/`all`).

**GET /builders/all-time-revenue**: Daily revenue and user counts across all builders. Columnar: `{columns: ["revenue", "timestamp", "countUsers"], data: [[...], ...]}`, newest first; the first row is today's partial day and the series starts October 27, 2024. Redirects to a pre-signed file (about 120 seconds).

**GET /builders/{builder}/fills**: Fills routed through a builder code. Params: `builder` (path), `start` (**required**, ISO 8601), `end` (defaults to now), `coin[]` and `address[]` (arrays of 1 to 10; a scalar returns 400 `must be an array`), `fillType` (`perp`, `spot`), `side` (`A`/`B`), `limit` (default 500, max 1000), `nextCursor`. The docs limit the window to one UTC calendar day; prod currently accepts longer windows (unlike `/fills`), so a one-day window is the safe choice. Returns `{fills, nextCursor}` ascending by `time`; `nextCursor` is `null` on the last page. Fill fields: `oid`, `address`, `coin`, `fullCoinName`, `fillType`, `px`, `sz`, `side`, `time`, `startPosition`, `dir`, `closedPnl`, `hash`, `crossed`, `fee`, `builderFee`, `tid`, `feeToken`, `builder`.

**GET /builders/{builder}/users**: Wallets that traded through a builder code. Params: `builder` (path), `offset`, `limit` (default 100, max 1000), `order` (`asc`/`desc`, default `desc`), `orderBy` (`pnl`, `perpPnl`, `closedPnl`, `volume`, `builderFee`, `equity`, `address`; default sorts by volume), `period` (`24h`, `7d`, `30d`, `all`; default `all`). Offset pagination only (`nextCursor` is ignored). Returns `{items: [{address, builderFee, volume, closedPnl, perpPnl, pnl, equity, wallet}], totalCount}`. Item metrics cover `period`; `wallet` is the wallet's current profile (segments, totalEquity, all-time perpPnl, ...) and can be absent.

### File Exports

All exports redirect to a pre-signed file. Per-coin files expire after about 30 seconds, global files after about 120 seconds.

**GET /exports/{file}**: `file` (path): `segments-bias-charts-data-24h`, `total-wallets-equity-chart-data`. `segments-bias-charts-data-24h` is an array of 16 `{segmentId, columns: ["timestamp", "bias", "marginBias"], data}`, about hourly over ~72 hours, oldest first, 24h position-age filter; `bias` is the signed `perpBias` scale of `/segments/{id}/bias-history` (not the heatmap's long fraction).

**GET /exports/coins/{coin}/{file}**: Coin-specific files. `file` (path):
- `segment-metrics`, `segment-metrics-24h`, `segment-metrics-7d`, `segment-metrics-30d`: per-cohort metrics for the last ~7 days at 12-hour intervals plus the latest snapshot (the suffix is the position-age filter). Shape: `{coin, data: [{segment, metrics: {columns: [positionCount, positionCountLong, totalPositionValue, totalPositionValueLong, bias, timestamp], data}}]}`, 16 rows per cohort, newest first; `bias` is a long fraction by value.
- `position-metrics`: columnar coin metrics at 1-hour intervals for about 14 days (latest snapshot first). The `columns` header includes `coin` but each row omits it, so drop `coin` before zipping columns to rows.
- `position-breakdown-by-size`, `-24h`, `-7d`, `-30d`: positions grouped by size bucket: `{coin, createdAt, breakdownBySize: [{sizeSegmentId, size, minSize, maxSize, positionCount, pastPositionCount, totalPositionValue, pastTotalPositionValue, totalPositionValueLong, valueCloseToLiquidation, bias}]}`. Rows are not ordered (sort on `sizeSegmentId`), `size` labels use en dashes and comma decimals (`$1m–$2,5m`), and `bias` is the long fraction of value.
- `position-breakdown-by-cohort`, `-24h`, `-7d`, `-30d`: the same breakdown grouped by cohort: `{coin, cohortMetrics: [{segment, positionCount, pastPositionCount, totalPositionValue, pastTotalPositionValue, totalPositionValueLong, valueCloseToLiquidation, bias, timestamp}]}`.
- `liquidation-heatmap`: price bins of potential liquidations: `{coin, heatmap: [{priceBinIndex, priceBinStart, priceBinEnd, liquidationValue, positionsCount, mostImpactedSegment}]}`.

### Address Management

Manage your own tracked-address list (useful for watchlists).

**GET /addresses**: List your tracked addresses. Params: `offset`, `limit` (default 100, max 1000), `addresses[]` (array filter of 1 to 10; a scalar `addresses=` returns 400). Returns `{items: [{createdAt, updatedAt, address}], totalCount}`.

**POST /addresses/bulk**: Add addresses. Body: `{ "addresses": ["0x...", "0x..."] }`.

**DELETE /addresses/bulk**: Remove addresses. Body: `{ "addresses": ["0x...", "0x..."] }`.

**PUT /addresses/sync**: Replace your whole list. Body: `{ "addresses": ["0x...", "0x..."] }`.

### Hyperliquid Info Proxy

**POST /info**: Proxy to Hyperliquid's `/info` API with higher rate limits. Body: `{ "type": "<infoType>", "user": "0x..." }` plus optional `dex` (for HIP-3, e.g. `"xyz"`) and `builder`. **`user` is required by validation for every type**, including global ones like `meta` (pass any valid address). Supported `type` values: `meta`, `spotMeta`, `clearinghouseState`, `spotClearinghouseState`, `openOrders`, `frontendOpenOrders`, `exchangeStatus`, `maxMarketOrderNtls`, `vaultSummaries`, `userVaultEquities`, `leadingVaults`, `extraAgents`, `subAccounts`, `userFees`, `userRateLimit`, `spotDeployState`, `perpDeployAuctionStatus`, `delegations`, `delegatorSummary`, `maxBuilderFee`, `userToMultiSigSigners`, `userRole`, `perpsAtOpenInterestCap`, `validatorL1Votes`, `perpDexs`, `webData2`. **Never send `liquidatable`, `activeAssetData` or `marginTable`:** validation accepts them, but they cannot work through the proxy. Any valid address works for global types (e.g. the zero address). Fields other than `type`, `user`, `dex` and `builder` are dropped, so `activeAssetData` (needs `coin`) and `marginTable` (needs `id`) return 422 `Failed to deserialize`, and `liquidatable` returns 422 because Hyperliquid no longer supports it; call Hyperliquid directly for the first two. `maxBuilderFee` needs `builder` and returns an integer in tenths of a basis point. An unknown `dex` returns 500. Market data and history types (`candleSnapshot`, `l2Book`, `allMids`, `metaAndAssetCtxs`, `recentTrades`, `userFills`, `userFillsByTime`, `historicalOrders`, `userFunding`, `fundingHistory`, `vaultDetails`, `portfolio`) are rejected with 400; call Hyperliquid directly or use the HyperTracker equivalents (`/fills`, `/fundings`, `/candles`, the order book streams).

### System Status

**GET /hypertracker/state/status**: Data freshness. Redirects (302, link valid about 120 seconds) to `status.json` with `{lastUpdate, nextUpdate, nextUpdateThreshold}`. Use it to schedule polling, or pair it with the state webhook.

---

## Infrastructure: Real-Time & Push Delivery

Beyond REST, HyperTracker runs production Hyperliquid data infrastructure that builders can plug into directly: live WebSocket streams, server-side alerts delivered to your own webhook, state-update webhooks, and dedicated infrastructure for enterprise teams. Use these instead of polling when you need data as it happens.

### Real-Time WebSocket Streams

Live Hyperliquid order books (BBO, L2, L2 diffs and L4), trades, per-market and all-market mids, fills, account events, TWAP updates and order events over WebSocket or SSE (Centrifugo protocol). Surge, Flow and Stream include WebSocket access as soon as the plan is active. Free and Pulse tokens are refused on connect (HTTP 403 on the handshake; the docs list error `1080`, `WS_NOT_ENTITLED`). See plan access below.

| Purpose | URL |
|---------|-----|
| WebSocket | `wss://jp-ws.hypertracker.io/connection/websocket` |
| SSE | `https://jp-ws.hypertracker.io/connection/sse` |
| SSE command emulation | `https://jp-ws.hypertracker.io/emulation` (used by the SDK; Node needs it as an absolute `emulationEndpoint`) |

The older host `ws.hypertracker.io` still answers; new integrations should use `jp-ws.hypertracker.io`.

| Data | Channel | Filter field | Replay |
|------|---------|--------------|--------|
| Every trade fill | `rooms:fills` | `tf` | Yes (last 5,000 messages, up to 10 minutes; often only seconds of fills) |
| Account events: deposits, withdrawals, transfers, sends, delegations, vault activity, liquidations, funding | `rooms:misc_events` | `tf` | Yes |
| TWAP status (`activated` to `finished`/`terminated`/error) | `rooms:twaps` | `tf` | Yes |
| Order events (open, filled, canceled, triggered, ...) for the addresses you filter on | `orders:feed` | `data` (`{"filter": ...}`); an `address` filter with `eq` or `in` is **required** (else `1084`), and each address counts as one subscription | No, live only |

**Order book and market streams.** One channel per market, named `<namespace>:<COIN>` (e.g. `l2book:BTC`, `bbo:xyz:GOLD`, spot `trades:@107`). Market names are canonical and case-sensitive. Subscribe with no filter: `{"id": 2, "subscribe": {"channel": "l2book:BTC"}}`. These channels take no tag filters and have no replay (never send `recover`, `epoch`, `offset` or `since`), and their messages carry no `id`, `blockNumber` or `sentTime`: order by `height` where present. A delisted market is rejected with `1084`, a market without a book with `1071`.

| Data | Channel | Plans | Payload (`pub.data`) |
|------|---------|-------|----------------------|
| Best bid and offer | `bbo:{COIN}` | Surge, Flow, Stream | `{channel: "bbo", data: {coin, time, bbo: [bid, ask]}}`, each level `{px, sz, n}` (`n` = order count), `null` for an empty side. Published only on change, so nothing arrives on subscribe until the next change. |
| L2 book (aggregated levels) | `l2book:{COIN}` | Surge, Flow, Stream | `{channel: "l2Book", data: {coin, time, levels: [bids, asks]}}` (no `height`), each level `{px, sz, n}`, 20 levels per side by default. A full snapshot every block (about 15 per second) even when unchanged: replace your book, never merge. Slow clients skip to the latest. |
| L2 diffs | `l2bookdiff:{COIN}` | Surge, Flow, Stream | `{channel: "l2BookDiff", data: {snapshot, coin, time, height, levels}}`. The first message is a full snapshot (`snapshot: true`); later messages carry only changed levels, and `sz: "0"` with `n: 0` deletes a level (also when it leaves the `nLevels` window). Drop a diff whose `height` is not above the last applied one. A later `snapshot: true` (resubscribe, selector change, server recovery) replaces local state. Never skips while subscribed: a client that falls behind loses the subscription. |
| Trades | `trades:{COIN}` | Surge, Flow, Stream | `{channel: "trades", data: [{coin, side, px, sz, hash, time, tid, users}]}`. `side` is the aggressor, `users` is `[buyer, seller]`. Best effort: skipped trades are reported on the same channel as `{data: [], gap: {fromHeight, toHeight, dropped?}}`. Dedupe on `coin` + `tid` (`tid` joins to the two `rooms:fills` fills). |
| Mid price | `mids:{COIN}` | Surge, Flow, Stream | `{channel: "mids", data: {coin, time, mid}}`; `mid` is (best bid + best ask) / 2, or the last trade price for an empty or one-sided book. Published only when it changes. |
| All mids | `allmids:stream` | Not in any plan by default; enabled on request (`1084` until then) | `{channel: "allMids", data: {mids: {"BTC": "63100.5", ...}}}`, no `time`. A full map on subscribe, then a complete replacement map whenever any mid changes; markets without a derivable mid are omitted. |
| L4 book (every individual order, with its wallet) | `l4book:{COIN}` | Stream only (`1084` on Surge and Flow) | Each `data` holds one key. Starts with either one `Snapshot` (`{coin, time, height, levels: [bids, asks]}`, rows are full orders: `user`, `coin`, `side`, `limitPx`, `sz`, `oid`, `timestamp`, `triggerCondition`, `isTrigger`, `triggerPx`, `isPositionTpsl`, `reduceOnly`, `orderType`, `tif`, `cloid`; best price first, queue order within a price) or, when the snapshot exceeds 3,000,000 encoded bytes (BTC, about 7 parts), back-to-back `SnapshotPart` messages (`{coin, time, height, seq, total, bids, asks}`, `seq` 0-based; append `bids`/`asks` in `seq` order and apply updates only after the last part). Then one `Updates` message per active block: `{time, height, order_statuses, book_diffs}`. Handle both snapshot forms. |

**L4 updates.** Keys inside `Updates` are snake_case. `order_statuses[]` is `{time, user, status, order}`: `time` is an ISO string with nanoseconds and no `Z`, and the nested `order.user` is `null`, so read the sibling `user`. Apply `book_diffs[]` (`{user, oid, px, coin, raw_book_diff}`) in array order. `raw_book_diff` is `{"new": {"sz"}}` (append at the back of the level), `{"new": {"sz", "insertBefore": oid}}` (insert ahead of that order), `{"update": {"origSz", "newSz"}}` (size change, keeps queue place) or `"remove"`. For `new`, take the other fields from the latest `open` (or `triggered`) `order_statuses` entry with the same `oid`; price and size come from the diff. Treat `status`, `orderType`, `tif` and `triggerCondition` as open strings, and compare prices numerically (`"63100"` in a snapshot can be `"63100.0"` in an update). Untriggered stop and take-profit orders are excluded; fired triggers show `isTrigger: false, triggerCondition: "Triggered"`. On any gap, inconsistent part or ended subscription, discard the book and resubscribe.

**L2 selectors** (`l2book` and `l2bookdiff` only, sent in the subscribe `data`): `nSigFigs` 2-5 (omit for full precision), `mantissa` 2 or 5 (only with `nSigFigs: 5`), `nLevels` 1-100 levels per side (default 20, counted after bucketing), optional `coin` (must match the channel). Example: `{"id": 3, "subscribe": {"channel": "l2book:ETH", "data": {"nSigFigs": 5, "mantissa": 5, "nLevels": 100}}}`. Omit defaults: an explicit `nLevels: 20`, zero, negative or decimal values and unknown fields are rejected with `1071`. Bucket size = 10^(integer digits - `nSigFigs`) x `mantissa`; bids round down, asks round up, and levels in a bucket sum `sz` and `n`. Depth is the same on every plan. One selector set per channel per connection (`105` if you subscribe twice); a second set needs a second connection, which counts toward your limits.

**Plan access and limits:**

| | Surge | Flow | Stream | Enterprise |
|---|---|---|---|---|
| Concurrent connections | 10 | 50 | 250 | Custom |
| Active subscriptions | 100 | 1,000 | 10,000 | Custom |
| Client messages per minute (account-wide, e.g. subscribe requests) | 300 | 1,500 | 6,000 | Custom |
| Order book streams | 5 | 25 | 100 | Custom |
| `bbo`, `l2book`, `l2bookdiff`, `mids`, `trades`, `rooms:*`, `orders:feed` | Yes | Yes | Yes | Per contract |
| `l4book` | No (`1084`) | No (`1084`) | Yes | Per contract |
| `allmids:stream` | On request | On request | On request | Per contract |

One order book stream is one market on one channel on one connection: `bbo`, `l2book`, `l2bookdiff` and `l4book` count, `mids`, `trades` and `allmids` do not, and selectors do not change the count. Limits are per account, summed across your connections; the same market on two connections counts twice. Bursts up to your subscription limit are allowed when resubscribing after a reconnect. New connections are capped at twice your connection limit per minute (`1088`). Closed connections and subscriptions free their slots about 2.5 minutes later. Plan changes reach open connections within about 2 minutes. Fills, account events and TWAPs are enabled together. Free and Pulse cannot open a WebSocket connection. For extra channels, market-wide feeds or dedicated capacity, contact the team via Telegram, Discord or support@coinmarketman.com (see Enterprise below).

**Protocol (plain WebSocket):**
1. Connect with the header `Authorization: Bearer <token>` (browsers: send `{"id":1,"connect":{"data":{"token":"<token>"}}}` instead). Never send the token on subscribe.
2. Send `{"id": 1, "connect": {}}` first.
3. Subscribe: `{"id": 2, "subscribe": {"channel": "rooms:fills", "tf": <filter>}}`. For `orders:feed`, put the filter in `data`: `{"id": 2, "subscribe": {"channel": "orders:feed", "data": {"filter": <filter>}}}`. Success is `{"id": 2, "subscribe": {}}` (`rooms:*` replies also carry `recoverable`, `epoch` and `offset`); failure is `{"id": 2, "error": {"code", "message", "temporary"?}}`. Match replies by `id`, since a publication can share a frame with a reply.
4. Events arrive as `{"push": {"channel": "...", "pub": {"data": {...}, "offset": 42}}}`. `rooms:*` publications also carry `pub.tags`; `orders:feed` tags are filter-only and are not sent.
5. Reply `{}` to every `{}` ping, and split each frame on `\n` before parsing (one frame can hold several messages).

**Filters:** `{"op": "", "key": "coin", "cmp": "eq", "val": "BTC"}`, combined with `{"op": "and" | "or" | "not", "nodes": [...]}`. `cmp`: `eq`, `neq`, `in`, `nin` (use `vals`), `ex`, `nex`, `sw`, `ew`, `ct`, `gt`, `gte`, `lt`, `lte`. Tags are text; boolean-looking tags are `"true"`/`"false"`, and numeric comparisons parse the text. Values are case-sensitive and addresses are lowercase hex. Only the documented tags below are filterable; a malformed filter is rejected with `1071`. Fill tags: `address`, `coin`, `px`, `sz`, `side`, `dir`, `isBuilder`, `isLiquidation`, `twapid`, `builder`, `liquidation.user`, `liquidation.method`. Order tags: `address`, `coin`, `side`, `oid`, `limitPx`, `sz`, `origSz`, `tif`, `cloid`, `orderType`, `triggerCondition`, `isTrigger`, `reduceOnly`, `isPositionTpsl`, `status`. Account-event tags: `eventType` (e.g. `LedgerUpdate.deposit`, `LedgerUpdate.liquidation`, `Funding`; `{"key": "eventType", "cmp": "sw", "val": "LedgerUpdate"}` matches all ledger updates), `user`. TWAP tags: `status`, `user`, `coin`, `twapId` (fills use the lowercase tag `twapid` for the same value). `orders:feed` `orderType` values: `Limit`, `Market`, `Stop Market`, `Stop Limit`, `Take Profit Market`, `Take Profit Limit`, `Vault Close`.

**Error codes:** `105` already subscribed on this connection; `1071` bad channel, market, selector or filter (do not retry unchanged); `1072` initial state timeout (retry with backoff); `1073` denied (read the message); `1074` auth service unavailable (retry); `1080` not entitled to WebSocket; `1081`, `1082`, `1083` connection, subscription and order-book-stream limits (temporary); `1084` channel not in your plan, delisted market or `orders:feed` without an address; `1086` access check unavailable (temporary); `1087` message rate (temporary; 600 rejected messages in a minute closes the connection with `4586`); `1088` connect rate. Close `4585`: the plan lost WebSocket access. Unsubscribe push `2000`: the channel is no longer allowed. On `l2book`, `l2bookdiff`, `l4book`, `allmids` and `orders`, the SDK does not auto-retry after `1081`-`1083`, `1086` or `1087`: retry yourself.

**Stream rules:**
- `orders:feed` requires an `address` filter (`eq` or `in`); without one the subscribe is rejected with `1084`. Narrow further with `coin` or `status`. Exclude `Funding` from `rooms:misc_events` unless you need it: it spikes to tens of thousands of events every hour.
- Events on `rooms:*` and `orders:feed` carry `id` (the dedupe key), `blockNumber`, `blockTime`, `localTime` and `sentTime`, and can arrive more than once. `id` is a string on all streams (account events used to send a number); keep it as text and never parse order IDs. Transfers arrive once per `user` with the same `id`.
- Replay covers the last 5,000 channel messages, up to 10 minutes, all or nothing; filters do not extend it, so high-volume `rooms:fills` can cover only seconds. Save the channel `epoch` and each processed `offset`, then resubscribe with `"recover": true, "epoch": ..., "offset": ...`. Recovered publications arrive inline in the subscribe reply (`subscribe.publications`). `recovered: false` (no error is returned) or a changed `epoch` means the gap stands; `3010 insufficient state` means subscribe fresh. SDKs replay automatically; use `since` (centrifuge-js) only after an app restart. Streams cannot backfill history: use REST (`/fills`, `/fills/liquidation`, `/closed-trades`) for anything older.
- A liquidation produces two tagged fills, one for the liquidated wallet and one for the counterparty. To total liquidations, count only fills where `address == liquidation.liquidatedUser`.
- Prices and sizes are decimal strings. `blockTime`, `localTime`, `sentTime` and fill `time` are epoch milliseconds; TWAP and account-event `time` are ISO strings with nanoseconds and no `Z` (treat them as UTC). A TWAP error can arrive with `status` as an object (`{"error": "..."}`).
- Each connection has a 64 MB outgoing buffer; overflow closes it with `3008 slow`. A full BTC L4 snapshot (about 17 MB) fits. Do heavy work off the receive loop.
- Order book stream caps are enforced per account (see Plan access and limits). Over the cap the subscribe fails with `1083` (`WS_ORDERBOOK_LIMIT`, temporary); free a slot (released about 2.5 minutes after close) and retry yourself.
- Known issue: after you unsubscribe from `l2book`, `l2bookdiff` or `l4book`, the server pushes `{"unsubscribe": {"code": 2500, "reason": "insufficient state"}}`, and `centrifuge-js` treats 2500 as a resubscribe signal, so the stream comes back. Call `client.removeSubscription(sub)` right after `sub.unsubscribe()`, and remove the old subscription before creating one with new parameters. Plain WebSocket clients can ignore the push.
- SDKs: `centrifuge-js` (JavaScript/TypeScript) and `centrifuge-python` handle pings, reconnects and replay. In centrifuge-js, pass `tagsFilter` for `tf`, `data: {filter}` for `orders:feed` and `since` for replay after a restart. Some Python SDK versions don't expose `tf`; use a plain WebSocket for `rooms:*` filters.
- API keys do not expire, and generating a new key does not revoke the old one; report a leaked key to support.

### Server-Side Alerts (Events API, Beta)

Define what to watch, give HyperTracker an HTTPS URL, and each match is POSTed to your server as JSON. No polling. Available on all plans, including Free. Alert-management requests and successful deliveries use one usage token each; failed attempts, retries and paused or suspended skips are not billed. The API contract is stable; the product is labeled Beta.

**Routes** (same base URL and Bearer token as REST):

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/events/endpoints` | Register a webhook endpoint. Body: `endpoint` (HTTPS URL), `secretKey` (signing secret, strongly recommended), `description` |
| GET | `/events/endpoints` | List endpoints: `{items}` |
| GET / PATCH / DELETE | `/events/endpoints/{id}` | Read (incl. `deliveryStatus`, `suspendedUntil`, `lastDeliveryFailureAt`, `lastDeliveryFailureReason`), update (`endpoint`, `secretKey`, `description`, `paused`), delete (409 `{"message": "Webhook endpoint is used by existing signals"}` while alert rules still reference it) |
| POST | `/events` | Create an alert rule. Body: `eventType`, `webhookEndpointId`, optional `addresses`, optional `filters` |
| GET | `/events` | List rules: `{items, totalCount}`. Params: `offset`, `limit` (default 100, max 1000), `eventType`, `webhookEndpointId` |
| GET / PATCH / DELETE | `/events/{id}` | Read, partially update (incl. `paused`), delete |

Create the endpoint first; its `id` becomes the rule's `webhookEndpointId`. The rule's `id` arrives on every delivery as `eventId`.

**Event types:**

| `eventType` | Fires when | `addresses` | `filters` |
|-------------|-----------|-------------|-----------|
| `position_activity` | A tracked wallet makes a (non-TWAP) perp fill | Required, 1-1000 | `coin` (array) |
| `twap_execution` | A tracked wallet's TWAP fills a slice | Required, 1-1000 | `coin` (array) |
| `twap_lifecycle` | A non-spot TWAP is activated, finishes, is terminated or errors (source errors arrive as `status: "error"` with the text in `description`) | Optional, max 1000 (blank = exchange-wide) | `coin` (array) |
| `ledger_update` | A deposit or withdrawal happens | Optional, max 1000 (blank = exchange-wide) | `types` (`deposit`, `withdraw`; omitted = both), `amount` (`{gte, gt, lte, lt, eq}`) |
| `liquidation` | A position is liquidated | Optional, max 1000 (blank = every liquidation) | `thresholdUsd` (optional, above 0), `markets` (array), `side` (`long`, `short`, `both`; default `both`) |
| `price_crossing` | A market's price crosses your threshold | Not used | `market` (string, required), `threshold` (required), `direction` (`above`, `below`, `both`; default `both`) |
| `large_market_order` | Anyone trades above your USD threshold (liquidations excluded; aggregated per wallet, market and `orderId`) | Not supported (exchange-wide) | `thresholdUsd` (required, at least 50000), `markets` (array), `direction` (`buy`, `sell`, `both`) |

An omitted `coin` filter means all perp markets.

**Delivery `data` per type** (fields get added over time, so validate only the ones you use):
- `position_activity`: `{address, coin, fillCount, liquidationCount, firstFillAt, lastFillAt, fills[]}`
- `twap_execution`: `{address, coin, twapId, fillCount, firstFillAt, lastFillAt, fills[]}`
- `twap_lifecycle`: `{address, coin, twapId, status, description, side, size, executedSize, executedNotional, minutes, reduceOnly, randomize, timestamp}`
- `ledger_update`: `{address, type, amount, time (epoch ms as a string), hash, users, delta}`
- `liquidation`: `{liquidations: [{address, market, side, size, usdNotional, executionPrice, fills, sourceEventId, eventTime}]}`
- `price_crossing`: `{market, threshold, direction, previousPrice, triggerPrice, eventTime}`
- `large_market_order`: `{orders: [{address, market, direction, positionEffect, orderId, aggregatedSize, usdNotional, averageExecutionPrice, fills, eventTime}]}`

**Gotchas:**
- The signing field is `secretKey`. A field named `secret` is accepted without an error but does not set a signing secret, so deliveries arrive unsigned. An empty `secretKey` also creates an unsigned endpoint.
- `addresses` is a top-level field, never inside `filters`. Addresses need the `0x` prefix.
- All numeric filter values are decimal strings: `"thresholdUsd": "1000000"`, `"threshold": "65000.00"`.
- The market key differs by type: `market` (string) for `price_crossing`; `markets` (array) for `liquidation` and `large_market_order`; `coin` (array) for `position_activity`, `twap_execution`, `twap_lifecycle`. Market lists hold up to 100 entries.
- Tickers are not validated: `"btc"` or a misspelled coin is accepted and never fires. Use exact case and HIP-3 prefixes (`xyz:NVDA`).
- PATCH is partial at the top level (omitted fields stay unchanged), but `filters` is replaced as a whole, so resend every filter you want to keep. Send `"addresses": []` to clear address targeting where allowed. Changing `eventType` revalidates the whole rule, so leftover filters can make it fail.
- `price_crossing` fires only when price moves across the threshold after the rule exists; touching it is not enough.
- Exchange-wide rules (blank addresses on `liquidation`, `ledger_update`, `twap_lifecycle`; any `large_market_order`) can produce high delivery volume, and each delivery uses a token. Start with a high `thresholdUsd`.

**Deliveries:** each POST body is `{deliveryId, consumerId, webhookEndpointId, eventId, eventType, occurredAt, data}` with headers `x-event-id`, `x-webhook-event`, `x-webhook-delivery-id` and, when a `secretKey` is set, `x-webhook-signature: v1=<hex HMAC-SHA256 of the raw body>`. Verify the signature over the raw bytes before parsing JSON, store each delivery once using `deliveryId` as the unique key (delivery is at-least-once), then return 2xx. Responses 408, 409, 425, 429 and 5xx and network transport failures are retried, honoring a valid `Retry-After` up to the configured maximum backoff; any other status (e.g. 400, 401, 404) is not retried and the delivery is lost, so return 2xx for an already-stored `deliveryId`. A failure is recorded once a delivery's retries are exhausted, and error responses count. Ten failures within five minutes suspend the endpoint for five minutes up to one hour; one success clears the window, a later real event acts as the probe after a suspension, and events skipped during suspension are not replayed. Fill-based types group deliveries by rule, address and coin and split large batches, and `ledger_update` sends one delivery per affected address, so delivery count (and token cost) is not occurrence count. Deliveries for one rule are processed in order within a batch; there is no ordering across rules, so sort by payload timestamps. `position_activity` delivers raw fills without "opened/closed" interpretation. There is no cohort-based event type: build cohort alerts by polling cohort endpoints (see recipes). For white-label alerts, create one rule per end customer and route deliveries by the verified body's `eventId`, never by the unsigned `x-event-id` header. There is no delivery-history endpoint (a dropped delivery cannot be refetched) and no custom reference ID on rules, and `price_crossing` does not name its price feed.

### State Webhooks

Configure in the API Dashboard (Webhook States card, then Add Webhook URL; `https://` only, optional Bearer header). After each state refresh (about every 30 minutes) HyperTracker POSTs `{"event": "stateUpdated", "timestamp": "...", "data": {}}`. The ping carries no data; use it to trigger your REST refresh instead of polling. Check the pricing page for which plans include webhooks.

### Enterprise & Dedicated Infrastructure

For teams that outgrow the Stream plan, HyperTracker offers custom limits, dedicated API infrastructure, SLAs, multi-region deployment and white-label solutions with direct technical support. Contact support@coinmarketman.com, the HyperTracker Telegram group or Discord.

### Hyperliquid Node Peering (Planned)

A planned, SLA-backed peering service for teams running their own Hyperliquid non-validating node: allowlisted peer connectivity, monitoring and onboarding support, 99.9% monthly peering uptime, $500 per month per allowlisted connecting-node IP, the same terms for every customer. It is a separate infrastructure product: it does not include REST, WebSocket, webhook or cohort data, and API plans are not required. Activation is by manual onboarding once the service launches; register interest at support@coinmarketman.com (subject "Hyperliquid Node Peering") or on Telegram. Requirements: a static public IP, peer ports `4001` and `4002` publicly reachable, one allowlisted IP per subscription. Scheduled maintenance is announced 48 hours ahead and excluded from the SLA. Peering improves connection stability; it does not guarantee latency, data completeness or trading outcomes.

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
  "totalCount": 421131,
  "items": [
    {
      "id": "45883cd1...",
      "rank": 1,
      "previousRank": 1,
      "side": "short",
      "address": "0x5b5d...",
      "dex": "main",
      "coin": "ETH",
      "value": -212697818.95,
      "size": 92465.2519,
      "entryPrice": 2322.72,
      "markPrice": 2300.3,
      "midPrice": 2300.35,
      "unrealizedPnl": 2073059.96,
      "funding": 4548795.67,
      "liquidationPrice": 3666.38,
      "liquidationProgress": 0,
      "crossLeverage": 5,
      "isolatedLeverage": 0,
      "openTime": "2026-07-09T07:57:47.000Z",
      "closeTime": null,
      "profile": {"totalEquity": 200035652.94, "balance": 200035652.94, "perpEquity": 136663276.79, "perpMarginEquity": 149094518.23, "countOpenPositions": 28, "pnl": 216491228.98, "segments": [7, 8], "walletLeverage": 4.73, "marginWalletLeverage": 4.34, "displayName": null, "showName": {"text": "crisp-copper-banner", "emoji": null}, "verified": false}
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
      "hash": "bIUSUWzlZp01EToRyouN4yL9hPYAAAAAAhahrwAAAZ2TOTDU",
      "id": "35037615",
      "firstFillId": "3820340536112316430",
      "lastFillId": "4124009116374926635",
      "side": "long",
      "coin": "ETH",
      "avgEntry": 2012.115,
      "avgExit": 2373.061,
      "duration": 5594052669,
      "openTime": "2026-02-10T04:23:59.383Z",
      "closeTime": "2026-04-15T22:18:12.052Z",
      "partial": false,
      "totalSize": 50000.0059,
      "totalUsd": 100605773.22,
      "realizedPnlUsd": 17325569.46,
      "countFills": 12080,
      "fee": 86246.79,
      "feeUsd": 86246.79,
      "fundingUsd": -635458.53,
      "maePrice": 1797.2,
      "maePercent": 10.68,
      "mfePrice": 2413.9,
      "mfePercent": 19.97
    }
  ],
  "nextCursor": null
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
`winRate` is a 0-1 float (multiply by 100 for a percentage). Durations are milliseconds. Formulas (verified against prod): `profitFactor = totalWinningPnl / abs(totalLosingPnl)`, `payoffRatio = avgGain / abs(avgLoss)`, `expectancy = winRate * avgGain + (1 - winRate) * avgLoss` (average dollar PnL per trade; when both wins and losses are above 0 it equals `netPnl / totalTrades`, and when either is 0 the API returns `null`, see the null rules under `/closed-trades/summary`), `expectancyPct = expectancy / avgTradeSize`, `volumeSharePct = coin totalVolumeUsd / summary totalVolumeUsd`. `updatedAt` is `null` for wallets with no closed trades.

### /candles
```json
{
  "candles": [
    {"dateOpen": "2026-11-02T12:00:24Z", "dateClose": "2026-11-02T12:00:25Z", "open": 77863, "high": 77863, "low": 77863, "close": 77863, "volumeBase": 0.12843, "volumeQuote": 9999.94509, "tradeCount": 1, "synthetic": false},
    {"dateOpen": "2026-11-02T12:00:25Z", "dateClose": "2026-11-02T12:00:26Z", "open": 77863, "high": 77863, "low": 77863, "close": 77863, "volumeBase": 0, "volumeQuote": 0, "tradeCount": 0, "synthetic": true}
  ]
}
```
`synthetic: true` marks a second with no trades (OHLC carry the previous close). There is no cursor: request the next 600-second window yourself.

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
| Surge | $399/mo | 150,000/mo | 100 req/min | REST, server-side alerts, WebSocket streams (up to 5 order book streams) |
| Flow | $799/mo | 400,000/mo | 200 req/min | REST, server-side alerts, WebSocket streams (up to 25 order book streams) |
| Stream | $1,999/mo | 2,000,000/mo | 500 req/min | REST, server-side alerts, WebSocket streams (up to 100 order book streams, L4) |
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

### Full closed-trade history (28-day windows)
```python
def all_closed_trades(address, since, until):
    trades, seen = [], set()
    window_start = since
    while window_start < until:
        window_end = min(window_start + timedelta(days=28), until)  # the limit is one calendar month
        cursor = None
        while True:
            params = {"address": address, "startTime": iso(window_start), "endTime": iso(window_end), "limit": 500}
            if cursor:
                params["nextCursor"] = cursor
            r = requests.get(f"{BASE}/closed-trades", headers=HEADERS, params=params)
            r.raise_for_status()
            resp = r.json()
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
        "wss://jp-ws.hypertracker.io/connection/websocket",
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
: "${TOKEN:?set TOKEN}" "${SECRET:?set SECRET first, e.g. with openssl rand -hex 32}" &&
EP=$(curl -s -X POST "$BASE/events/endpoints" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"endpoint":"https://yourapp.com/webhooks/hypertracker","secretKey":"'"$SECRET"'","description":"liquidation alerts"}' | jq -er .id) &&
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

### Cohort watchlist: every wallet in a cohort, kept current
```python
def cohort_addresses(segment_id):
    out, offset = set(), 0
    while True:
        page = requests.get(f"{BASE}/wallets", headers=HEADERS, params={
            "segmentIds": segment_id, "orderBy": "address", "order": "asc",
            "offset": offset, "limit": 500}).json()
        out.update(w["address"] for w in page["items"])
        offset += len(page["items"])
        if not page["items"] or offset >= page["totalCount"]:
            return out

watch = cohort_addresses(8)                    # Money Printers; segmentIds=[8, 9] returns the union
# On each state webhook ("stateUpdated") or every 30-60 minutes: refetch and diff
fresh = cohort_addresses(8)
joined, left = fresh - watch, watch - fresh    # update WebSocket address filters / alert rules with these
```
Leave `hasOpenPositions` unset so members without open positions stay on the list. Feed the addresses to `orders:feed` or `rooms:fills` filters (`{"op": "", "key": "address", "cmp": "in", "vals": [...]}`) or to `position_activity` alert rules (up to 1000 addresses per rule).

### 1-second candles for a longer range
```python
from datetime import datetime, timedelta, timezone

def candles(coin, start, end):
    rows, t = [], start
    while t < end:
        t2 = min(t + timedelta(seconds=600), end)
        r = requests.get(f"{BASE}/candles", headers=HEADERS, params={
            "coin": coin, "start": t.isoformat().replace("+00:00", "Z"),
            "end": t2.isoformat().replace("+00:00", "Z")})
        r.raise_for_status()
        rows.extend(r.json()["candles"])
        t = t2
    return rows                                 # one row per second; aggregate client-side for 1m/5m bars

end = datetime.now(timezone.utc).replace(microsecond=0)
btc = candles("BTC", end - timedelta(hours=1), end)   # 6 calls
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

**"Give me a list of every Money Printer wallet so I can track them"**
Endpoints: `/wallets?segmentIds=8&orderBy=address&order=asc&limit=500`
Page with `offset` until `totalCount`, export the addresses as CSV with `perpMarginEquity`, `perpPnlUsd30d` and `countOpenPerps`. Refresh after each state update.

**"Show me the last 10 minutes of BTC second by second"**
Endpoints: `/candles?coin=BTC&start={now - 600s}&end={now}`
Plot the 1-second candles with volume bars; mark seconds with `synthetic: true` as gaps in trading.

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
Use `/summary` for `winRate`, `wins`, `losses`, `totalTrades`, `avgDuration`, `profitFactor`, `expectancy`. Use `/closed-trades` in 28-day windows for per-trade detail (entry, exit, realized PnL, fill count).

**"Show me the most profitable closed trades on Hyperliquid this month, by wallet."**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=25`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}&startTime={28d ago}`
Monthly leaders give candidates; pull each one's summary, then their largest trades by `realizedPnlUsd`.

**"Build a wallet-follow feed for a wallet"**
Endpoints: `POST /events` (`position_activity`), `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`
Push every non-TWAP fill from the watched wallets to your webhook with a `position_activity` rule (add `twap_execution` for TWAP slices). Use `/closed-trades` afterwards to reconcile completed trades and their realized PnL.

### Closed Trades: Wallet Discovery

The per-coin breakdown in `/closed-trades/summary` (`coins[]`) turns the endpoint into a wallet-discovery engine. Each coin entry has its own `winRate`, `profitFactor`, `expectancy` and `netPnl`, so you can find traders who are good on a specific asset.

**"Find the best [COIN] traders on Hyperliquid"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=100`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}&startTime={28d ago}`
Pull the top 100 monthly wallets. For each, find the target coin in `coins[]` and keep specialists: `totalTrades > 20`, `winRate > 0.6`, `profitFactor > 2`, `expectancyPct > 0.02`. Then vet survivors: check `countFills` on their recent trades (dozens or thousands of fills per trade usually means an execution algorithm, not a copyable decision), and confirm recent performance with `interval=30d`, since a strong all-time record can hide a losing month. Rank by per-coin `expectancy` or `netPnl`. Guard the filters for nulls: a specialist with no losing trades has `profitFactor: null` and `expectancy: null`, so `profitFactor > 2` silently drops them in JavaScript and raises `TypeError` in Python. Treat `profitFactor: null` with `losses == 0` as infinite, and rank coins with `expectancy: null` by `netPnl`. Add cohort context from `/wallets?address={address}`.

**"Build a follow watchlist for [COIN] specialists"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=100`, `/closed-trades/summary?address={address}`, `POST /events` (`position_activity` with `filters.coin`)
Use the specialist filter and vetting above to pick 5-10 wallets, then create one `position_activity` rule with those addresses and `"filters": {"coin": ["{COIN}"]}`. Show each delivery with the wallet's per-coin track record.

**"Find high-volume wallets with a losing track record to fade"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=asc&limit=100`, `/closed-trades/summary?address={address}`, `/positions?address={address}&open=true&start=2025-04-04T00:00:00.000Z`
Filter to `totalTrades > 100`, `winRate < 0.4`, `profitFactor < 0.8`, `totalVolumeUsd > 10000000`. Most fall into Exit Liquidity (12), Full Rekt (14) or Giga-Rekt (15). Guard for nulls as in the recipe above (`profitFactor` is `0`, not `null`, when a coin has no wins). Return them as a fade list with their current open positions.

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

**"Which wallets in a cohort are having their best month, and are they still in the market?"**
Endpoints: `/wallets?segmentIds=9&orderBy=address&order=asc&limit=500` (all pages)
Pull every Smart Money (9) wallet, rank client-side by `perpPnlUsd30d` and `perpPnlPercent30d` (percent units), and keep those with `countOpenPerps > 0`. Show `exposureRatio`, `closestLiq` and `combinedPnlUsd30d` next to each so the user sees risk and whole-wallet performance alongside perps.

**"How much heat does this trader take before a winner pays out?"**
Endpoints: `/closed-trades?address={addr}&startTime={28d ago}&endTime={now}` (all pages, earlier windows as needed)
Compare `maePercent` on winning vs losing trades (`realizedPnlUsd` > 0 vs < 0) and `mfePercent` vs the realized move to see how much open profit the trader gives back. Skip trades where the excursion fields are `null`, and check `countFills` to separate algorithmic wallets.

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
Equity, exposure and cohorts from `/wallets`; win rate, profit factor, expectancy and the per-coin breakdown from the summary; per-trade detail and execution quality from `/closed-trades` and its fills; and total funding paid or received per coin from `/fundings` (28-day windows). Show which assets the wallet is actually good at and what funding cost it.

**"Alpha screener: find and vet top traders before following them"**
Endpoints: `/leaderboards/perp-pnl?rankBy=pnlMonth&orderBy=pnlMonth&order=desc&limit=100`, `/wallets?address={address}`, `/positions?address={address}&open=true&start=2025-04-04T00:00:00.000Z`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`
Discover candidates from the monthly leaderboard. For each, pull equity and liquidation proximity from `/wallets`, current exposure and leverage from `/positions`, and the track record from `/closed-trades/summary`. Vet with `countFills` and the `30d` interval before ranking by per-coin `expectancy` or `profitFactor`.

**"Macro sentiment and smart money cohort radar"**
Endpoints: `/segments`, `/positions/heatmap`, `/position-metrics/general?start={ISO}&end={now}`, `/position-metrics/coin/{coin}?start={ISO}&end={now}`, `/position-metrics/coin/{coin}/segment/{segmentId}?start={ISO}&end={now}`, `/{segmentId}/assets/liquidation-risk`, `/state/summary`
Cohort definitions from `/segments`, the global directional grid from the heatmap, market health from `/position-metrics/general`, per-coin concentration from `/position-metrics/coin/{coin}`, and per-cohort trend shifts (one point per state update, about every 30 minutes) from the per-cohort series. Add liquidation exposure and network context. Isolate coins where smart money is fading the retail crowd.

**"Systematic exposure analysis and backtesting pipeline"**
Endpoints: `/hypertracker/state/status`, `/positions?start={ISO}`, `/position-metrics/general?start={ISO}&end={now}`, `/position-metrics/coin/{coin}?start={ISO}&end={now}`, `/closed-trades/summary?address={address}`, `/closed-trades?address={address}`, `/closed-trades/{hash}/fills`, `/exports/coins/{coin}/liquidation-heatmap`
Check freshness with `/hypertracker/state/status`. Pull positioning from `/positions` (paginate with `nextCursor`), macro OI from `/position-metrics/general` and per-coin exposure from `/position-metrics/coin/{coin}`. Build performance baselines from `/closed-trades/summary`, open/close pairs from `/closed-trades` (28-day windows) and slippage from `/closed-trades/{hash}/fills`. Download liquidation price bins from `/exports/coins/{coin}/liquidation-heatmap`.

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
Pull funding in windows of 28 days or less (the limit is one calendar month), total `fundingAmount` per coin, and compare with realized PnL per coin from closed trades. Flag positions where funding paid ate most of the gain.

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
| Closed trades empty or 400 | Use `startTime`/`endTime` (not `start`/`end`), keep each window at 28 days or less (the limit is one calendar month), and remember the default is the last 7 days. |
| Empty order snapshots | Paginated snapshots cover the last 30 days only, on 5-minute boundaries. |
| Snapshot download returns 404 "not available" | Historical files exist only for about January 19 to March 12, 2026; use `/orders/5m-snapshots/{snapshotTime}` (last 30 days) or the per-coin latest download. |
| 0-byte response or broken download | The endpoint redirected to a pre-signed file. Follow redirects (`curl -L`) and fetch `downloadUrl` immediately; links can expire in as little as 30 seconds. |
| `/wallets` returns no items for a real address | Only active wallets are listed (perp volume in the last 30 days or an open position), and the address must be lowercase. Use `/closed-trades/summary` for history. |
| A coin is missing from liquidation risk | Results are sorted by `percentRisk`; page with `offset`. |
| Data looks stale | Most data updates on Hyperliquid state updates (about every 30 minutes). Read `createdAt` and check `/hypertracker/state/status`. |
| Cohort totals look doubled | You summed size and PnL cohorts together. Sum within one axis only. |
| `POST /info` returns 400 "Invalid Hyperliquid wallet address" | Include `user` in the body for every `type`. |
| WebSocket connect returns 403 / `1080`, or `l4book:*` is refused with `1084` | WebSocket access starts on Surge; Free and Pulse cannot connect. `l4book:*` needs Stream, and `allmids:stream` is enabled on request. |
| `orders:feed` subscribe fails with `1084` | Add an `address` filter with `eq` or `in`. |
| Order book subscribe fails with `1083` | Order book stream cap for your plan (5/25/100 per account). Close one; the slot frees about 2.5 minutes later. |
| `1071` on an `l2book` subscribe | Invalid selector. Omit defaults (`nLevels: 20` is rejected), use `mantissa` only with `nSigFigs: 5`. |
| An unsubscribed order book channel comes back | Known `2500` push after unsubscribe on `l2book`, `l2bookdiff`, `l4book`. Call `client.removeSubscription(sub)` after `sub.unsubscribe()`. |
| WebSocket closes with `3008 slow` | The connection's 64 MB outgoing buffer overflowed: your handler is too slow or you subscribed to too much. Move heavy work off the receive loop. |
| WebSocket reconnect lost events (`recovered: false` or `3010`) | Replay covers the last 5,000 messages, up to 10 minutes (seconds for unfiltered fills). Backfill the gap from REST. |
| `POST /info` returns 422 `Failed to deserialize` | The type needs a field the proxy drops (`coin`, `id`) or is unsupported upstream (`liquidatable`). Call Hyperliquid directly. |
| `/candles` returns 400 or 404 | Add a timezone (`Z`) to `start`/`end`, keep the window at 600 seconds or less, and use the exact coin case (`BTC`, `xyz:GOLD`). |
| `/positions/open/coin/xyz:GOLD` returns 404 | That endpoint takes the bare ticker (`GOLD`) and returns it across every dex. |
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
