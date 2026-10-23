# Binance User Data Streams

_Last updated: 2025-10-24_

This reference summarizes the realtime account-level events that Binance pushes over a User Data Stream subscription. The stream is accessed via the WebSocket API using an API key. Both SBE and JSON payloads are supported and all JSON timestamps are expressed in milliseconds.

Each event is wrapped in an envelope that includes the `subscriptionId` returned when the subscription was created. This allows multiple simultaneous subscriptions to be multiplexed over the same WebSocket connection.

```json
{
  "subscriptionId": 0,
  "event": {
    "e": "balanceUpdate",
    "E": 1573200697110,
    "a": "BTC",
    "d": "100.00000000",
    "T": 1573200697068
  }
}
```

| Field             | Description |
|-------------------|-------------|
| `subscriptionId`  | Identifier returned when the stream subscription was created. |
| `event`           | Stream payload containing the event-specific fields. |

## Subscription management

User Data Stream subscriptions can be created on any authenticated WebSocket connection and, with a valid signature, on unauthenticated connections. Key properties of the subscription lifecycle are:

* Only one active subscription per account is permitted on a single connection.
* A session supports up to 1,000 concurrently active subscriptions and 65,535 total subscriptions over its lifetime.
* Check the `userDataStream` flag inside `session.status` to confirm whether any subscriptions are active (`true`), inactive (`false`), or unavailable (`null`).

### Subscribe using the authenticated session

```json
{
  "id": "d3df8a21-98ea-4fe0-8f4e-0fcea5d418b7",
  "method": "userDataStream.subscribe"
}
```

| Response field  | Description |
|-----------------|-------------|
| `subscriptionId` | Identifier assigned to the subscription. Use this value to match incoming events to the originating account. |

This call requires an authenticated WebSocket connection established with Ed25519 credentials (`session.logon`).

### Subscribe using an API key signature

```json
{
  "id": "d3df8a22-98ea-4fe0-9f4e-0fcea5d418b7",
  "method": "userDataStream.subscribe.signature",
  "params": {
    "apiKey": "<key>",
    "timestamp": 1747385641636,
    "signature": "<signature>"
  }
}
```

| Parameter   | Type    | Description |
|-------------|---------|-------------|
| `apiKey`    | String  | API key identifying the account whose data stream will be subscribed. |
| `timestamp` | Long    | Current timestamp in milliseconds used for request validation. |
| `signature` | String  | HMAC signature generated with the API secret. |

The response mirrors the authenticated subscription response and returns a `subscriptionId`.

### Unsubscribe from the User Data Stream

```json
{
  "id": "d3df8a21-98ea-4fe0-8f4e-0fcea5d418b7",
  "method": "userDataStream.unsubscribe"
}
```

Provide the optional `subscriptionId` parameter to terminate a specific subscription; omit it to cancel all active subscriptions on the connection.

### List active subscriptions

```json
{
  "id": "d3df5a22-88ea-4fe0-9f4e-0fcea5d418b7",
  "method": "session.subscriptions",
  "params": {}
}
```

The response enumerates every active subscription in the session. Track subscription-to-account mappings on the client side.


## Account Update (`outboundAccountPosition`)

`outboundAccountPosition` is emitted whenever a balance changes. Only the assets affected by the triggering event are included in the payload.

```json
{
  "subscriptionId": 0,
  "event": {
    "e": "outboundAccountPosition",
    "E": 1564034571105,
    "u": 1564034571073,
    "B": [
      {
        "a": "ETH",
        "f": "10000.000000",
        "l": "0.000000"
      }
    ]
  }
}
```

| Field | Description |
|-------|-------------|
| `e` | Event type (`outboundAccountPosition`). |
| `E` | Event time. |
| `u` | Time of the last account update. |
| `B` | Array of balances that changed. Each entry contains the asset code (`a`), free balance (`f`), and locked balance (`l`). |

## Balance Update (`balanceUpdate`)

`balanceUpdate` covers deposits, withdrawals, and transfers between internal Binance accounts.

```json
{
  "subscriptionId": 0,
  "event": {
    "e": "balanceUpdate",
    "E": 1573200697110,
    "a": "BTC",
    "d": "100.00000000",
    "T": 1573200697068
  }
}
```

| Field | Description |
|-------|-------------|
| `e` | Event type (`balanceUpdate`). |
| `E` | Event time. |
| `a` | Asset. |
| `d` | Balance delta. |
| `T` | Clear time. |

## Order Update (`executionReport`)

Order lifecycle changes are delivered through the `executionReport` event.

```json
{
  "subscriptionId": 0,
  "event": {
    "e": "executionReport",
    "E": 1499405658658,
    "s": "ETHBTC",
    "c": "mUvoqJxFIILMdfAW5iGSOW",
    "S": "BUY",
    "o": "LIMIT",
    "f": "GTC",
    "q": "1.00000000",
    "p": "0.10264410",
    "P": "0.00000000",
    "F": "0.00000000",
    "g": -1,
    "C": "",
    "x": "NEW",
    "X": "NEW",
    "r": "NONE",
    "i": 4293153,
    "l": "0.00000000",
    "z": "0.00000000",
    "L": "0.00000000",
    "n": "0",
    "N": null,
    "T": 1499405658657,
    "t": -1,
    "v": 3,
    "I": 8641984,
    "w": true,
    "m": false,
    "M": false,
    "O": 1499405658657,
    "Z": "0.00000000",
    "Y": "0.00000000",
    "Q": "0.00000000",
    "W": 1499405658657,
    "V": "NONE"
  }
}
```

Average fill price can be derived by dividing `Z` (quote asset transacted quantity) by `z` (filled quantity).

### Execution Types

| Code | Meaning |
|------|---------|
| `NEW` | Order accepted. |
| `CANCELED` | Order canceled by the user. |
| `REPLACED` | Order amended. |
| `REJECTED` | Order rejected without execution. |
| `TRADE` | Order filled partially or fully. |
| `EXPIRED` | Order canceled by matching rules or exchange action. |
| `TRADE_PREVENTION` | Order expired because of self-trade prevention (STP). |

### Conditional Fields

Certain fields appear only when the related feature is present in the order. The following table lists the conditional keys:

| Field | Name | Description |
|-------|------|-------------|
| `d` | Trailing Delta | Present for trailing stop orders. |
| `D` | Trailing Time | Present for trailing stop orders. |
| `j` | Strategy ID | Returned when `strategyId` was supplied. |
| `J` | Strategy Type | Returned when `strategyType` was supplied. |
| `v` | Prevented Match ID | Present for orders that expired due to STP. |
| `A` | Prevented Quantity | Quantity blocked by STP. |
| `B` | Last Prevented Quantity | Most recent prevented quantity. |
| `u` | Trade Group ID | Identifier for the trade group. |
| `U` | Counter Order ID | Opposing order identifier. |
| `Cs` | Counter Symbol | Symbol for the counter order. |
| `pl` | Prevented Execution Quantity | Execution quantity blocked by STP. |
| `pL` | Prevented Execution Price | Price associated with `pl`. |
| `pY` | Prevented Execution Quote Qty | Quote quantity blocked by STP. |
| `W` | Working Time | When the order was resting on the book. |
| `b` | Match Type | Present for orders with allocations. |
| `a` | Allocation ID | Identifier for the allocation. |
| `k` | Working Floor | Present for orders that may allocate. |
| `uS` | Used SOR | Indicates Smart Order Routing usage. |
| `gP` | Pegged Price Type | Present for pegged orders. |
| `gOT` | Pegged Offset Type | Present for pegged orders. |
| `gOV` | Pegged Offset Value | Offset applied to the peg. |
| `gp` | Pegged Price | Resulting peg price. |

### Reject Reasons

The `r` field communicates why an order was rejected. Refer to the Errors documentation for detailed descriptions.

| Code | Message |
|------|---------|
| `NONE` | N/A — order was not rejected. |
| `INSUFFICIENT_BALANCES` | "Account has insufficient balance for requested action." |
| `STOP_PRICE_WOULD_TRIGGER_IMMEDIATELY` | "Order would trigger immediately." |
| `WOULD_MATCH_IMMEDIATELY` | "Order would immediately match and take." |
| `OCO_BAD_PRICES` | "The relationship of the prices for the orders is not correct." |

## OCO List Status (`listStatus`)

An additional `listStatus` event accompanies `executionReport` events for order lists such as OCOs.

```json
{
  "subscriptionId": 0,
  "event": {
    "e": "listStatus",
    "E": 1564035303637,
    "s": "ETHBTC",
    "g": 2,
    "c": "OCO",
    "l": "EXEC_STARTED",
    "L": "EXECUTING",
    "r": "NONE",
    "C": "F4QN4G8DlFATFlIUQ0cjdD",
    "T": 1564035303625,
    "O": [
      {
        "s": "ETHBTC",
        "i": 17,
        "c": "AJYsMjErWJesZvqlJCTUgL"
      },
      {
        "s": "ETHBTC",
        "i": 18,
        "c": "bfYPSQdLoqAJeNrOr9adzq"
      }
    ]
  }
}
```

| Field | Description |
|-------|-------------|
| `e` | Event type (`listStatus`). |
| `E` | Event time. |
| `g` | Order list ID. |
| `c` | Contingency type (for example, `OCO`). |
| `l` | List status type. |
| `L` | List order status. |
| `r` | List reject reason. |
| `C` | List client order ID. |
| `T` | Transaction time. |
| `O` | Orders in the list, each with symbol (`s`), order ID (`i`), and client order ID (`c`). |

## Session Lifecycle Events

### Stream Terminated (`eventStreamTerminated`)

Sent when the user data stream stops, such as after an unsubscribe request.

```json
{
  "subscriptionId": 0,
  "event": {
    "e": "eventStreamTerminated",
    "E": 1728973001334
  }
}
```

### External Lock Update (`externalLockUpdate`)

Emitted when an external system locks or unlocks a portion of the spot wallet balance (for example, when used as margin collateral).

```json
{
  "subscriptionId": 0,
  "event": {
    "e": "externalLockUpdate",
    "E": 1581557507324,
    "a": "NEO",
    "d": "10.00000000",
    "T": 1581557507268
  }
}
```

| Field | Description |
|-------|-------------|
| `e` | Event type (`externalLockUpdate`). |
| `E` | Event time. |
| `a` | Asset affected by the external lock. |
| `d` | Delta applied to the lock. |
| `T` | Transaction time. |

## Notes

- Subscribe to the user data stream via the WebSocket API after creating a listen key with a signed REST request.
- Keep the listen key alive by calling the keep-alive endpoint every 30 minutes.
- Close the stream explicitly when logging out or switching sessions to receive the `eventStreamTerminated` confirmation.
