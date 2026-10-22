# SPOT API Glossary

> **Disclaimer:** This glossary refers only to the SPOT API implementation. Definitions may differ for Futures, Options, or other Binance APIs.

## A
- **ACK**: `newOrderRespType` enum. Order response containing only `symbol`, `orderId`, `orderListId`, `clientOrderId`, and `transactTime`.
- **aggTrade / Aggregate trade**: Aggregation of one or more individual trades from the same taker order filled at the same time and price.
- **allocation**: Transfer of an asset from the exchange to your account (e.g., when an order is filled by SOR instead of trading directly).
- **allocationId**: Unique identifier of an allocation on a symbol.
- **allocationType**: See `AllocationType`.
- **askPrice**: In ticker responses, the lowest price on the SELL side.
- **askQty**: In ticker responses, total quantity offered at the lowest price on the SELL side.
- **asks**: Orders on the SELL side.
- **avgPrice**: Volume-weighted average price for a set interval of minutes.

## B
- **baseAsset**: The first asset in the symbol (e.g., BTC is the base asset of BTCUSDT), representing the asset being bought and sold (the quantity).
- **baseAssetPrecision**: Number of decimals allowed on the `baseAsset` (Exchange Information).
- **baseCommissionPrecision**: Number of decimals the base asset commission is calculated to (Exchange Information).
- **bidPrice**: In ticker responses, the highest price on the BUY side.
- **bidQty**: In ticker responses, total quantity offered at the highest price on the BUY side.
- **bids**: Orders on the BUY side.
- **BREAK**: Trading status indicating the symbol is not available for trading during expected downtime. Market data is not generated during BREAK.
- **BUY**: Enum value in the `side` parameter to purchase an asset (e.g., BTC).

## C
- **CANCELED**: Order status indicating the order has been canceled by the user.
- **cancelReplaceMode**: Parameter in cancel/replace orders defining whether the new order placement should proceed if the cancel request fails.
- **clientOrderId**: User-defined field in order placement responses identifying the newly placed order.
- **commission**: Fee paid on a trade.
- **commissionAsset**: Asset the commission fees were deducted from.
- **Counter Order Id**: Field in User Data Stream execution reports indicating the counterparty order in a prevented match.
- **Counter Symbol**: Field in User Data Stream execution reports indicating the counterparty symbol in a prevented match.
- **cummulativeQuoteQty**: Accumulation of `price * qty` for each fill of an order.

## D
- **Data Source**: Specifies where an endpoint or request retrieves its data.

## E
- **executedQty**: Quantity filled in an order.
- **EXPIRED**: Order status indicating the order was canceled according to order type rules or by the exchange.
- **EXPIRED_IN_MATCH**: Order status indicating the order was canceled by the exchange due to STP (e.g., `EXPIRE_TAKER` matching with orders on the book from the same account or `tradeGroupId`).

## F
- **filters**: Define trading rules on the exchange.
- **FOK / Fill or Kill**: `timeInForce` enum where the order expires if it cannot be fully filled immediately.
- **free**: Amount of an asset in a user's balance that can be traded or withdrawn.
- **FULL**: `newOrderRespType` enum providing a response with all order information, including the `fills` field.

## G
- **GTC / Good Til Canceled**: `timeInForce` enum where the order remains active until canceled or fully filled.

## H
- **HALT**: Trading status indicating the symbol is unavailable for trading during emergency downtime. Market data is still generated during HALT.

## I
- **intervalNum**: Amount of time in an interval (e.g., `interval = SECOND`, `intervalNum = 5` means every 5 seconds).
- **IOC / Immediate or Canceled**: `timeInForce` enum where the order fills as much as possible immediately and expires the remainder.
- **isBestMatch**: Response field indicating if the trade price was the best available on the exchange.
- **isBuyerMaker**: Response field indicating if the buyer was also the market maker.
- **isWorking**: Field showing if the order has started working on the order book.

## K
- **kline**: Candlestick data showing open, close, high, low, volume, and other market data for a symbol over a duration.

## L
- **Last Prevented Quantity**: Order quantity that expired due to STP.
- **lastPrice**: Price of the latest trade.
- **lastQty**: Total quantity traded at the `lastPrice`.
- **LIMIT**: Order type where the execution price will be no worse than the set price (price or better).
- **LIMIT_MAKER**: Order type restricted to maker orders (cannot immediately match and take).
- **limitClientOrderId**: Parameter identifying the LIMIT_MAKER order in an OCO pair.
- **listClientOrderId**: Parameter identifying the pair of orders in an OCO placement.
- **locked**: Amount of an asset locked in open orders and other platform services.

## M
- **MARKET**: Order type that buys or sells at the best available prices until filled or liquidity is exhausted.
- **Matching Engine**: Data source indicating the response originates from the engine; also refers to the system that processes requests and matches orders.
- **Match Type**: Field in order response/execution report indicating if the order was filled by the SOR.
- **Memory**: Data source where the response comes from internal API memory or cache.

## N
- **NEW**: Order status indicating the order has been accepted by the Matching Engine.
- **newClientOrderId**: Parameter assigning the `clientOrderId` for a placed order or cancel message.
- **Notional value**: Product of `price * qty`.

## O
- **OCO**: One-Cancels-the-Other order composed of paired orders (e.g., `STOP_LOSS`/`STOP_LOSS_LIMIT` with a `LIMIT_MAKER`). Executing one expires the other.
- **Order Amend Keep Priority**: See entry of the same name.
- **Order Book**: List of open bids and asks for a symbol.
- **Order List**: Multiple orders grouped as a unit. See OCO and OTO.
- **orderId**: Field uniquely identifying an order on a symbol.
- **origQty**: Original quantity submitted during order placement.
- **origClientOrderId**: Field used to cancel or query an order via `clientOrderId`.
- **OTO**: One-Triggers-the-Other order with a working order and a pending order; the pending order is placed when the working order fully fills.
- **OTOCO**: One-Triggers-a-One-Cancels-the-Other order combining a working order and an OCO pair triggered upon full fill of the working order.

## P
- **PARTIALLY_FILLED**: Order status indicating partial fills.
- **Pending order**: Order in an order list placed only when the corresponding working order fully fills. A single order list can include a single pending order or two forming an OCO.
- **PENDING_NEW**: Order status indicating pending orders have been accepted but not yet placed on the book.
- **Prevented execution price**: Price of a prevented self-trade (User Data Stream execution reports). See STP.
- **Prevented execution quantity**: Quantity of a prevented self-trade. See STP.
- **Prevented execution quote quantity**: Quote quantity of a prevented self-trade. See STP.
- **preventedQuantity**: Order quantity expired due to STP events.
- **Prevented Match**: Record of orders expiring due to STP.
- **preventedMatchId**: Identifier (with `symbol`) to query a prevented match of an expired order.

## Q
- **quantity**: Parameter specifying amount of the base asset to buy or sell.
- **quoteAsset**: Second asset in the symbol (e.g., USDT in BTCUSDT) representing the asset used to quote prices.
- **quoteAssetPrecision**: Number of decimals allowed on the `quoteAsset` (Exchange Information).
- **quoteCommissionPrecision**: Number of decimals quote asset commission is calculated to (Exchange Information).
- **quoteOrderQty**: MARKET order parameter specifying the amount of the quote asset to spend/receive in a reverse MARKET order.
- **quoteQty**: `price * qty`; the notional value.

## R
- **recvWindow**: API parameter specifying how many milliseconds after the timestamp the request remains valid.
- **RESULT**: `newOrderRespType` enum returning all order information except the `fills` field.
- **Reverse MARKET order**: MARKET order specified using `quoteOrderQty` instead of `quantity`.

## S
- **Self Trade Prevention (STP)**: Feature preventing orders from matching against the user's own account or `tradeGroupId`. See STP FAQ.
- **selfTradePreventionMode**: Parameter specifying behavior when an order could cause a self-trade.
- **SELL**: Enum value in `side` used when selling an asset (e.g., BTC).
- **Smart Order Routing (SOR)**: Uses interchangeable quote assets to improve liquidity. See SOR FAQ.
- **specialCommissionForOrder / specialCommission**: See Commission FAQ.
- **SPOT**: Trading type involving immediate purchase and delivery of an asset.
- **standardCommissionForOrder / standardCommission**: See Commission FAQ.
- **stopClientOrderId**: Parameter identifying the STOP order in an OCO pair.
- **stopPrice**: Price used in algorithmic orders to trigger placement on the order book; also determines when trailing price tracking begins.
- **STOP_LOSS**: Algorithmic order placing a MARKET order once the market price hits the `stopPrice`.
- **STOP_LOSS_LIMIT**: Algorithmic order placing a LIMIT order once the market price hits the `stopPrice`.
- **strategyId**: Numeric value identifying the order within an order strategy.
- **strategyType**: Numeric value identifying the order strategy.
- **symbol**: Trading pair composed of a base and quote asset (e.g., BTCUSDT, BNBBTC).

## T
- **TAKE_PROFIT**: Algorithmic order placing a MARKET order once the market price hits the `stopPrice`.
- **TAKE_PROFIT_LIMIT**: Algorithmic order placing a LIMIT order once the market price hits the `stopPrice`.
- **taxCommissionForOrder / taxCommission**: See Commission FAQ.
- **ticker**: Reports price change and other market data for a symbol within a rolling interval.
- **time**: For trades/allocations, the execution time; for order queries, the creation time.
- **timeInForce**: Determines taker behavior, maker eligibility, and order duration before expiry. Supported enums: `GTC`, `IOC`, `FOK`.
- **tradeGroupId**: Group of accounts belonging to the same trade group.
- **TRADING**: Trading status where orders can be placed.
- **trailingDelta**: Trailing stop parameter specifying required delta price change before order activation.
- **trailingTime**: Time when the trailing order becomes active and tracks price changes.
- **transactTime**: Timestamp of order updates (placed, filled, canceled). Millisecond precision by default.

## U
- **uiKlines**: Modified candlestick data optimized for chart presentation.
- **updateTime**: Last update timestamp for an order (milliseconds by default).
- **User Data Stream**: WebSocket stream delivering real-time account information (balances, order updates, etc.).
- **usedSor**: Indicates if the order was placed through SOR.

## W
- **weightedAveragePrice**: Volume-weighted average price over the last *x* minutes.
- **workingFloor**: Field indicating whether the order is filled by SOR or by the order book it was submitted to.
- **Working order**: Order immediately placed on the book that triggers pending order(s) when fully filled; always a single LIMIT or LIMIT_MAKER order.
- **workingTime**: Time when the order started working on the order book.

## X
- **X-MBX-ORDER-COUNT-XX**: Response header emitted when placing an order, indicating current order count for interval `XX` for the account.
- **X-MBX-USED-WEIGHT-XX**: Response header emitted when sending any API request, indicating current used request weight for interval `XX` by the IP.
