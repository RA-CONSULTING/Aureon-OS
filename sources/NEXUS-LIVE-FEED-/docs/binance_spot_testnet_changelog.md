# Binance Spot Testnet Changelog

_Last updated: 2025-10-24_

> **Note:** All features listed here apply only to the Binance Spot Testnet. The testnet does not always match production behavior.

## 2025-10-24

### Schema-Based Encoding (SBE)
- **Schema 3:1** (`spot_3_1.xml`) updated to support `listenToken` subscription methods for margin trading.

### REST and WebSocket API
- Documentation for `listenKey` usage on `wss://stream.binance.com` removed following the 2025-04-01 announcement.
- Legacy `listenKey` flows remain available until a future retirement notice.

#### REST API
- `POST /api/v3/userDataStream`
- `PUT /api/v3/userDataStream`
- `DELETE /api/v3/userDataStream`

#### WebSocket API
- `userDataStream.start`
- `userDataStream.ping`
- `userDataStream.stop`

## 2025-10-17 *(effective 07:00 UTC)*

An optional `symbolStatus` parameter has been added to the following endpoints. When supplied, only symbols whose trading status matches the specified value are returned.

### REST API
- `GET /api/v3/depth`
- `GET /api/v3/ticker/price`
- `GET /api/v3/ticker/bookTicker`
- `GET /api/v3/ticker/24hr`
- `GET /api/v3/ticker/tradingDay`
- `GET /api/v3/ticker`

### WebSocket API
- `depth`
- `ticker.price`
- `ticker.book`
- `ticker.24hr`
- `ticker.tradingDay`
- `ticker`

#### Behavior
- If `symbol=<SYMBOL>` is provided and the symbol is not in the requested status, the request fails with **-1220 SYMBOL_DOES_NOT_MATCH_STATUS**.
- If `symbols=[...]` is provided, any symbols that do not match the requested status are excluded. If none match, the response is an empty array.
- Endpoints where `symbol` and `symbols` are optional treat their omission as `symbols=[...]`.

## 2025-10-08 *(effective 07:00 UTC)*

### FIX API
- Updated QuickFIX Market Data schema reflecting microsecond `RecvWindow` support (announced 2025-08-05).
- `InstrumentList <y>` changes:
  - Added fields `StartPriceRange`, `EndPriceRange`.
  - `MinTradeVol`, `MaxTradeVol`, `MinQtyIncrement`, `MarketMinTradeVol`, `MarketMaxTradeVol`, `MarketMinQtyIncrement`, and `MinPriceIncrement` are now optional.
  - Changes are breaking—update to the new schema.

## 2025-10-01

- Periodic **data reset** performed on the Spot Testnet.
- Reminder: **SBE 2:1** schema retired on 2025-10-02 (six months after deprecation). Lifecycle documentation updated.

## 2025-09-24 *(deployment from 07:00 UTC)*

- New filter discovery endpoint:
  - REST: `GET /api/v3/myFilters`
  - WebSocket: `myFilters`
  - Only endpoint exposing whether an account has `MAX_ASSET` filters.
- SBE schema 3:1 (`spot_3_1.xml`) comments updated (non-breaking but recommended).
- Documentation added for `MAX_ASSET` filter.
- All Testnet accounts now have a `MAX_ASSET` filter for asset `JPY` (value `1000000`).

## 2025-09-18

- Updated documentation for `recvWindow` microsecond support:
  - REST: **Timing Security**
  - WebSocket: **Timing Security**

## 2025-09-12

- QuickFIX Order Entry schema updated to support **pegged orders**.
- FIX API documentation refreshed for microsecond `recvWindow` support in:
  - **Message Components**
  - **Timing Security**

## 2025-09-05

- Periodic **data reset** performed.

## 2025-08-28

- Expanded SBE FAQ: more detail on schema compatibility plus clarification of `NonRepresentable` and `NonRepresentableMessage` semantics.

## 2025-08-26

- “Request Security” documentation refreshed for REST and WebSocket APIs (no functional change).

## 2025-08-25 *(schema update at 05:00 UTC)*

### SBE
- Schema 3:1 (`spot_3_1.xml`) field renames in `MaxAssetFilter` message due to SbeTool Java generator issues:
  - `limitExponent` → `qtyExponent`
  - `limit` → `maxQty`
- Update recommended for consistency, though only impacted users must adopt.

## 2025-08-19

- `userDataStream.subscribe` responses now return `subscriptionId` (previously undocumented).

## 2025-08-07

### FIX API Documentation
- Documented FIX Market Data subscription limit.
- Clarified message processing order text.
- **2025-08-08 07:00 UTC** enablement:
  - `MAX_NUM_ORDER_LISTS` filter limit set to 20 per symbol.

## 2025-08-05 *(deployment from 07:00 UTC)*

### General
- **Pegged orders** enabled across APIs; `pegInstructionsAllowed` introduced in exchange info.
- Conditional fields (`pegPriceType`, `pegOffSetType`, `pegOffsetValues`, `peggedPrice`) now emitted when relevant across REST/WebSocket/FIX order lookups and cancel flows.
- `recvWindow` now supports microseconds (with millisecond default). Precision up to three decimal places.
- `specialCommission` structure introduced for commission requests (`computeCommissionRates=true`).
- New filter `MAX_NUM_ORDER_AMENDS` (limit 10 amendments per order).
- New error codes **-1120**, **1211**.
- Query order lists first consult cache before DB.
- Orders with cumulative quantity 0 in state `EXPIRED_IN_MATCH` archived after 90 days.
- Matching Engine bug fixed for order list filters.

### REST API
- Affected endpoints include:
  - `GET /api/v3/order`
  - `GET /api/v3/orderList`
  - `GET /api/v3/openOrderList`
  - `GET /api/v3/allOrders`
  - `DELETE /api/v3/order`
  - `DELETE /api/v3/orderList`
  - `DELETE /api/v3/openOrders`
  - `PUT /api/v3/order/amend/keepPriority`
  - `GET /api/v3/account/commission`
  - `POST /api/v3/order/test` (with `computeCommissionRates=true`)
  - `POST /api/v3/sor/order/test` (with `computeCommissionRates=true`)

### WebSocket API
- Impacted topics include:
  - `order.status`, `orderList.status`, `allOrders`
  - `order.cancel`, `orderList.cancel`, `openOrders.cancelAll`
  - `order.amend.keepPriority`
  - `account.commission`
  - `order.test` / `sor.order.test` with `computeCommissionRates=true`
  - `userDataStream.subscribe` now returns `subscriptionId`
  - Multiple User Data Stream subscriptions per connection (one per account). New methods:
    - `userDataStream.subscribe.signature`
    - `session.subscriptions`
    - `userDataStream.unsubscribe`
- `userDataStream` flag semantics adjusted (`true` if any subscription active).
- `userDataStream.unsubscribe` authorization changed to **NONE** and supports bulk closure.
- User Data Stream payloads include `subscriptionId`.

### FIX API
- `OrdType(4)` adds value `P (PEGGED)`.
- Added tags `PegOffsetValue(211)`, `PegPriceType(1094)`, `PegMoveType(835)`, `PegOffsetType(836)` to order entry/cancel-amend messages.
- `ExecutionReport <8>` echoes peg instructions including optional `PeggedPrice (839)`.
- New error messaging for pegged orders.
- `recvWindow` microsecond support plus third timing check near matching engine.
- New filters supported: `EXCHANGE_MAX_NUM_ORDER_LISTS`, `MAX_NUM_ORDER_LISTS`, `MAX_NUM_ORDER_AMENDS`.
- `ExecutionReportEvent` renders default values for `rejectReason` and `origClientOrderId` to align with JSON.
- `NonRepresentableMessage` introduced for schema gaps.
- When schema cannot represent a response, errors are returned.
- When clients send reject messages, FIX API no longer echoes `Reject <3>`—clearer errors returned instead.

### SBE Schema 3:1 Highlights
- New fields across responses: `pegInstructionsAllowed`, `pricePeg`, `pricePegOffsetLevel`, `peggedPrice`, `subscriptionId`, special commission fields, etc.
- Support for new filters and default-value handling.

### User Data Stream
- `subscriptionId` included in events.

## 2025-07-02

- Periodic **data reset** performed.

## 2025-06-04

- Periodic **data reset** performed.

## 2025-05-28

- Documented API timeout values and related errors across FIX, REST, WebSocket.

## 2025-05-22

- Reminder: **SBE 2:0** schema retired on 2025-05-28 (six-month window).

## 2025-05-21 *(effective 07:00 UTC)*

### Timing Security Updates
- Additional `recvWindow` check performed just before forwarding to the matching engine.
- Rejections from the new check count towards message/IP limits and unfilled order counts.
- Documentation updated (REST/WebSocket/FIX Timing Security).

### FIX Market Data
- Bug fix: `InstrumentList <y>` now reports accurate `NoRelatedSym(146)` values.

## 2025-04-29

- Upcoming support announcement: Ed25519-only features expanding to HMAC/RSA (e.g., WebSocket User Data Stream subscriptions without listenKeys).

## 2025-04-25 *(effective 09:00 UTC)*

- Request weight increased from **1 → 4** for:
  - REST: `PUT /api/v3/order/amend/keepPriority`
  - WebSocket: `order.amend.keepPriority`
- Documentation updated.
- Clarified FIX `SEQNUM` is a 32-bit unsigned integer with rollover.

## 2025-04-21

- **Order Amend Keep Priority** enabled on all symbols.
- Self-trade prevention mode **DECREMENT** enabled on all symbols.

## 2025-04-01 *(deployment from 07:00 UTC)*

### New Features
- **Order Amend Keep Priority** (REST `PUT /api/v3/order/amend/keepPriority`, WebSocket `order.amend.keepPriority`, FIX messages `OrderAmendKeepPriorityRequest`, `OrderAmendReject`).
- Exchange info adds `allowAmend` flag.
- Self-trade prevention mode **DECREMENT** available; `allowedSelfTradePreventionModes` updated accordingly.

### URL Migrations
- Legacy WebSocket URLs to be removed in May 2025. Move to:
  - `wss://ws-api.testnet.binance.vision/ws-api/v3`
  - `wss://stream.testnet.binance.vision/ws`

### Order Identifier Behavior
- When both `orderId` and `origClientOrderId`/`cancelOrigClientOrderId` supplied, matching requires both to refer to the same order. Applies to REST/WebSocket/FIX cancel and status requests.
- Similar logic for `listOrderId` + `listClientOrderId` on order list cancellations.
- `GET /api/v3/myTrades` (and WebSocket `myTrades`) weight now **5** when `orderId` supplied, otherwise **20**.
- Requests missing both `orderId` and `origClientOrderId` now fail with **-1102** (previously -1128).
- New error code **-2038** for failed amend-keep-priority requests.
- New error messages for **-1034**.

### FIX API
- Schema updated for new features including STP mode `DECREMENT`.
- Connection limits enforced (10 concurrent per account) with rate limits per service.
- Maintenance notifications via `News <B>` (headline includes disconnect countdown).
- `OrderCancelRequest <F>` / `OrderCancelRequestAndNewOrderSingle <XCN>` accept both `orderId` and `clientOrderId`.
- `EncryptMethod(98)` validated as `0` at logon.

### User Data Streams
- Using `listenKey` on `stream.testnet.binance.vision` deprecated; migrate to WebSocket API subscriptions with Ed25519 keys.
- Future documentation clean-up announced.

### SBE
- Schema **3:0** released (deprecates 2:1). Highlights:
  - `amendAllowed` in `ExchangeInfoResponse`.
  - New messages `OrderAmendmentsResponse`, `OrderAmendKeepPriorityResponse`.
  - All enums gain `NON_REPRESENTABLE` variant.
  - New STP mode `DECREMENT`.
  - `symbolStatus` enum values `AUCTION_MATCH`, `PRE_TRADING`, `POST_TRADING` removed.
  - Fields `usedSor`, `orderCapacity`, `workingFloor`, `preventedQuantity`, `matchType` now mandatory.
  - `orderCreationTime` optional in `ExecutionReportEvent`.
  - Deprecated schema 2:1 unable to represent new responses (errors returned instead).

### Schema 2:1 Deprecation Impact
- Known mismatches when using schema 2:1 for user data streams (e.g., `listStatusType`, `selfTradePreventionMode`, `orderCreationTime`).

## 2025-03-31

- Added clarification on **cancel order** performance expectations.

## 2025-03-13 *(effective 05:00 UTC)*

- FIX Drop Copy sessions limited to **60 messages per minute**.
- FIX Market Data sessions limited to **2000 messages per minute**.
- Documentation updated accordingly.

## 2025-03-05

- Request weights increased **2 → 4** for:
  - REST: `GET /api/v3/aggTrade`
  - WebSocket: `trades.aggregate`
- Documentation updated.

## 2025-02-28

- **SBE Market Data Streams** available (trade, best bid/ask, diff depth, partial book depth). Improved latency vs JSON.

## 2025-02-05

- WebSocket services now send ping every **20 seconds** (was 3 minutes); allowed pong delay reduced to **1 minute** (was 10).
- Documentation updated for WebSocket Market Data, User Data Streams, WebSocket API.
- FIX Market Data `Trade` stream now renders `AggressorSide (2446)`; QuickFIX schema updated.

## 2024-12-17

- FIX Market Data available on Spot Testnet; documentation includes schema link.

## 2024-11-27

### Microsecond Support (opt-in)
- **WebSocket Streams**: optional `timeUnit` URL parameter (`millisecond`/`microsecond`).
- **REST API**: optional `X-MBX-TIME-UNIT` header with same values. Affects request parameters and response timestamps.
- **WebSocket API & User Data Streams**: optional `timeUnit` URL parameter.

### General Changes
- Bug fix: OCO buy orders missing `stopPrice` now accepted.
- OCO combinations expanded to include `TAKE_PROFIT` and `TAKE_PROFIT_LIMIT` pairs.
- `origQuoteOrderQty` now appears in responses where applicable (result/full resp types).

### Impacted Requests
- REST: `POST /api/v3/order`, `/api/v3/sor/order`, `/api/v3/order/oco`, `/api/v3/orderList/oco`, `/api/v3/orderList/oto`, `/api/v3/orderList/otoco`, `DELETE /api/v3/order`, `DELETE /api/v3/orderList`, `POST /api/v3/order/cancelReplace`.
- WebSocket: `order.place`, `sor.order.place`, `orderList.place`, `.oco`, `.oto`, `.otoco`, `order.cancel`, `orderList.cancel`, `order.cancelReplace`.

### SBE Schema 2:1
- Released with support for `origQuoteOrderQty`, WebSocket session `userDataStream` flag, and new user data stream messages/responses.
- Schema 1:0 deprecated (six-month retirement window).

### WebSocket API
- User Data Stream subscriptions via WebSocket API introduced (Ed25519 only).
- New requests: `userDataStream.subscribe`, `.unsubscribe`.
- `session.logon`, `.status`, `.logout` include `userDataStream` field.
- Bug fix: `userDataStream.start` now returns new listenKey post-logon.

### User Data Stream
- New events: `eventStreamTerminated`, `externalLockUpdate`.

### FIX API
- Added administrative `News <B>` message for disconnect countdown notifications.

## 2024-11-05

- Exchange info endpoints now accept optional `showPermissionSets` (hide permissions) and `symbolStatus` filters.

## 2024-10-02

- Reminder: **SBE 1:0** schema disabled on 2024-10-04 per policy.

## 2024-09-04

- Spot Testnet now enforces **Unfilled Order Count**; documentation updated.

## 2024-08-16

- New error messaging for low-liquidity quote quantity market orders.

## 2024-08-07

- QuickFIX schema adjustments (details not specified).

## 2024-07-23 *(deployment from ~07:00 UTC)*

- FIX Drop Copy sessions now supported.
- New API key permission: `FIX_API_READ_ONLY`.

## 2024-07-17

- Kline timestamp bug fixed across REST/WebSocket/UI endpoints using `timeZone` parameter.

## 2024-06-21

- FIX API available on Spot Testnet (Ed25519 key with `FIX_API` permission required). Production release TBD.

## 2024-06-05

- Trade WebSocket streams no longer expose buyer (`b`) and seller (`a`) order IDs; rely on User Data Streams to track fills.

## 2024-05-30

### WebSocket API
- `wss://ws-api.testnet.binance.vision/ws-api/v3` designated primary URL (others deprecated).

### WebSocket Streams
- `wss://stream.testnet.binance.vision/ws` and `/stream` now primary endpoints (others deprecated).

## 2024-05-23

### REST API
- `orderRateLimitExceededMode` added to `POST /api/v3/order/cancelReplace`.

### WebSocket API
- `orderRateLimitExceededMode` added to `order.cancelReplace`.

### WebSocket Streams
- Kline/Candlestick streams support `@+08:00` (UTC+8) offset.

## 2024-05-02

- OTO (`POST /api/v3/orderList/oto`) and OTOCO (`POST /api/v3/orderList/otoco`) orders enabled (and WebSocket equivalents `orderList.place.oto`, `.otoco`).

## 2024-04-04

### General
- Exchange info `permissions` moved into `permissionSets` (legacy field now empty, will be removed).
- Request weights increased **10 → 25** for `GET /api/v3/trades`, `GET /api/v3/historicalTrades`, `trades.recent`, `trades.historical`.

### REST API
- `POST /api/v3/order/oco` deprecated (use `/api/v3/orderList/oco`).
- `otoAllowed` flag added to exchange info response.

### WebSocket API
- `orderList.place` deprecated (use `.oco`).
- `otoAllowed` added to exchange info response.

### SBE
- Schema **2:0** released (deprecates 1:0). Highlights include permission set handling and support for deprecated OCO responses.
- When using schema 1:0, `permissions` group remains empty.

## 2024-03-13

### General
- `GET /api/v3/account` and `account.status` accept `omitZeroBalances` to hide empty balances.

### User Data Stream
- New event `listenKeyExpired` emitted when a listenKey expires.

