# Binance Spot FIX API Reference

This document captures the Binance Spot FIX API contract for order entry, drop copy, and market data connectivity. It highlights the current Spot Testnet endpoints, authentication requirements, operational safeguards, and the message catalogue developers rely on when integrating FIX alongside REST or WebSocket tooling.

## 1. General Requirements

- **Exchange scope:** The FIX interfaces are available for the Spot exchange only.
- **Transport:** All sessions must negotiate TLS. Use a TCP+TLS client directly or terminate TLS through a local proxy such as `stunnel`.
- **Timeouts:** Requests wait up to 10 seconds for the matching engine. After that the API responds with `-1007 TIMEOUT` and the final order state must be confirmed via User Data Stream or follow-up queries.
- **Keys:** Only Ed25519 API keys are supported. Generate dedicated FIX keys and protect the private component.
- **Encoding:** Messages are ASCII with SOH (`0x01`) delimiters; only printable ASCII characters are accepted.

## 2. Session Types and Endpoints

| Session | Endpoint | Capabilities | Eligible Permissions |
|---------|----------|--------------|----------------------|
| Order Entry | `tcp+tls://fix-oe.testnet.binance.vision:9000` | Submit, cancel, amend, and query usage limits. Receives all `ExecutionReport <8>` and `List Status <N>` messages. | `FIX_API` |
| Drop Copy | `tcp+tls://fix-dc.testnet.binance.vision:9000` | Receive all `ExecutionReport <8>` and `List Status <N>` events for the account. | `FIX_API`, `FIX_API_READ_ONLY` |
| Market Data | `tcp+tls://fix-md.testnet.binance.vision:9000` | Subscribe to market data streams and query active instruments (no order placement). | `FIX_API`, `FIX_API_READ_ONLY` |

QuickFIX schemas are provided for each session type. Review them before generating message classes or validation rules.

## 3. API Key Permissions

- **Order Entry:** Requires the `FIX_API` permission.
- **Drop Copy:** Accepts `FIX_API` or `FIX_API_READ_ONLY` permissions.
- **Market Data:** Accepts `FIX_API` or `FIX_API_READ_ONLY` permissions.

All FIX sessions require Ed25519 keys.

## 4. Connection Lifecycle

1. Open the TLS socket and send `Logon <A>` immediately. The server confirms with its own logon. Resend requests (`MsgType 2`) are not supported.
2. Negotiate a heartbeat interval (`HeartBtInt (108)`) between 5 and 60 seconds. Both sides monitor the cadence:
   - If the **server** receives no traffic for one interval it issues `TestRequest <1>`. Failure to respond with `Heartbeat <0>` echoing the `TestReqID (112)` within one more interval leads to `Logout <5>` and disconnection.
   - If the **client** detects silence for one interval it should send `TestRequest <1>` and expect a `Heartbeat <0>` with the same `TestReqID (112)`. Missing the response indicates the session should be re-established.
   - If neither side sends any traffic within one interval the server proactively sends `Heartbeat <0>`.
3. Maintenance windows are announced with repeating `News <B>` messages (every 10 seconds for 10 minutes). Upon receipt, establish a new session and gracefully close the current one. If the client does not logout within 10 seconds of the final notice the server will close the connection.
4. Always send `Logout <5>` before disconnecting. Omitting the logout leaves the `SenderCompID (49)` unusable for twice the heartbeat interval.

## 5. Message Ordering and Response Mode

| Field | Options | Notes |
|-------|---------|-------|
| `MessageHandling (25035)` | `UNORDERED (1)` • `SEQUENTIAL (2)` | Declared in the initial logon. `UNORDERED` allows in-flight reordering for higher throughput; `SEQUENTIAL` enforces strict `MsgSeqNum (34)` delivery. Regardless of mode the client must increment `MsgSeqNum` by exactly one per message. |
| `ResponseMode (25036)` | `EVERYTHING (1)` • `ONLY_ACKS (2)` | Controls which `ExecutionReport <8>` and `ListStatus <N>` messages each session receives. The default is `EVERYTHING`, broadcasting all order flow for the account. |

By default all concurrent order entry sessions receive successful execution and list status events, including those originating outside FIX.

## 6. Timing Security

Every request requires `SendingTime (52)` in UTC. `RecvWindow (25000)` is optional (defaults to 5,000 ms for logon only) and caps the acceptable latency in milliseconds (maximum 60,000 ms, supports millisecond fractions). Requests are processed when the following logic passes:

```text
serverTime = getCurrentTime()
if (SendingTime < serverTime + 1 second) and (serverTime - SendingTime) <= RecvWindow:
    serverTime = getCurrentTime()
    if (serverTime - SendingTime) <= RecvWindow:
        forward request to Matching Engine
    else:
        reject request
else:
    reject request
```

## 7. Logon Authentication

`Logon <A>` messages authenticate the session and must be the first payload the client sends.

- `Username (553)`: the API key.
- `RawData (96)`: Ed25519 signature over the concatenation of `MsgType`, `SenderCompID`, `TargetCompID`, `MsgSeqNum`, and `SendingTime`, separated by SOH. `RawDataLength (95)` must match the encoded signature length.
- `EncryptMethod (98)`: must be `0`.
- `HeartBtInt (108)`: heartbeat interval in seconds (5–60).
- `ResetSeqNumFlag (141)`: must be `Y`.
- `MessageHandling (25035)` and optional `ResponseMode (25036)` configure sequencing and downstream behaviour.
- `DropCopyFlag (9406)`: set to `Y` only when logging into Drop Copy sessions.

### Sample Python Helper

```python
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

def logon_raw_data(private_key: Ed25519PrivateKey,
                   sender_comp_id: str,
                   target_comp_id: str,
                   msg_seq_num: str,
                   sending_time: str) -> str:
    payload = chr(1).join([
        "A",  # MsgType for Logon
        sender_comp_id,
        target_comp_id,
        msg_seq_num,
        sending_time,
    ])
    signature = private_key.sign(payload.encode("ASCII"))
    return base64.b64encode(signature).decode("ASCII")

with open("private_key.pem", "rb") as fp:
    private_key = load_pem_private_key(fp.read(), password=None)

raw_data = logon_raw_data(
    private_key,
    sender_comp_id="5JQmUOsm",
    target_comp_id="SPOT",
    msg_seq_num="1",
    sending_time="20240612-08:52:21.613",
)
```

To verify an implementation, the canonical values below produce the signature `4MHXelVVcpkdwuLbl6n73HQUXUf1dse2PCgT1DYqW9w8AVZ1RACFGM+5UdlGPrQHrgtS3CvsRURC1oj73j8gCA==`:

| Field | Value |
|-------|-------|
| `MsgType (35)` | `A` |
| `SenderCompID (49)` | `EXAMPLE` |
| `TargetCompID (56)` | `SPOT` |
| `MsgSeqNum (34)` | `1` |
| `SendingTime (52)` | `20240627-11:17:25.223` |

### Sample Logon Exchange

```
8=FIX.4.4|9=248|35=A|34=1|49=5JQmUOsm|52=20240612-08:52:21.613|56=SPOT|95=88|96=KhJLbZqADWknfTAcp0ZjyNz36Kxa4ffvpNf9nTIc+K5l35h+vA1vzDRvLAEQckyl6VDOwJ53NOBnmmRYxQvQBQ==|98=0|108=30|141=Y|553=W5rcOD30c0gT4jHK8oX5d5NbzWoa0k4SFVoTHIFNJVZ3NuRpYb6ZyJznj8THyx5d|25035=1|10=000|
8=FIX.4.4|9=113|35=A|34=1|49=SPOT|52=20240612-08:52:21.636837|56=5JQmUOsm|98=0|108=30|25037=4392a152-3481-4499-921a-6d42c50702e2|10=051|
```

## 8. Message Envelope and Data Types

- **Header:** `BeginString (8)` → `BodyLength (9)` → `MsgType (35)` → `SenderCompID (49)` → `TargetCompID (56)` → `MsgSeqNum (34)` → `SendingTime (52)` → optional `RecvWindow (25000)`.
- **Trailer:** `CheckSum (10)` is a three-digit, zero-padded modulo-256 checksum over the entire message (including SOH characters).
- **Client Identifiers:** `ClOrdID`, `OrigClOrdID`, `MDReqID`, `ClListID`, `OrigClListID`, and `CancelClOrdID` must satisfy `^[a-zA-Z0-9-_]{1,36}$`. `SenderCompID` and `TargetCompID` must match `^[a-zA-Z0-9-_]{1,8}$`.
- **Timestamps:** UTC strings support seconds, milliseconds, or microseconds precision (e.g., `20240612-08:52:21.636837`).

Common data types:

| Type | Description |
|------|-------------|
| `BOOLEAN` | Enum `Y` or `N`. |
| `CHAR` | Single character. |
| `INT` | Signed 64-bit integer. |
| `LENGTH`, `NUMINGROUP` | Unsigned 64-bit integer. |
| `PRICE`, `QTY` | Fixed-point numbers (precision defined per symbol). |
| `SEQNUM` | Unsigned 32-bit integer (wraps after `4,294,967,295`). |
| `STRING` | Printable ASCII sequence. |
| `UTCTIMESTAMP` | `YYYYMMDD-hh:mm:ss[.SSS][SSS]` formats. |

## 9. Administrative Messages

- **Heartbeat `<0>`:** Sent by either party when the link is otherwise idle or responding to `TestRequest <1>`. Echo `TestReqID (112)` when responding.
- **TestRequest `<1>`:** Confirms liveness when no messages arrive within one heartbeat interval. The receiver must reply with `Heartbeat <0>` containing the provided `TestReqID`.
- **Reject `<3>`:** Returned for malformed messages, unknown symbols, unsupported tags, or when connection limits are exceeded. Diagnostic data appears in `Text (58)` and `ErrorCode (25016)`. `SessionRejectReason (373)` further qualifies the issue.
- **Logout `<5>`:** Initiates or acknowledges orderly shutdowns. Include optional human-readable `Text (58)`.
- **News `<B>`:** Broadcasts maintenance countdowns ("You'll be disconnected in %d seconds" / "Your connection is about to be closed. Please reconnect.").

## 10. Limits and Usage Monitoring

### 10.1 Message Limits

| Session | Limit |
|---------|-------|
| Order Entry | 10,000 messages per 10 seconds |
| Drop Copy | 60 messages per 60 seconds |
| Market Data | 2,000 messages per 60 seconds |

Exceeding a limit triggers `Logout <5>` and disconnection.

### 10.2 Connection Limits

| Session | Concurrent TCP Connections | Connection Attempts |
|---------|---------------------------|---------------------|
| Order Entry | 10 | 15 attempts / 30 seconds |
| Drop Copy | 10 | 15 attempts / 30 seconds |
| Market Data | 100 | 300 attempts / 300 seconds |

Wait up to twice the heartbeat interval after closing a socket for the limit counters to decrease.

### 10.3 Unfilled Order Count

Binance enforces unfilled order limits per account. Query `LimitQuery <XLQ>` to inspect both message usage and unfilled order counts. Orders consistently filled by trades can continue to recycle capacity; rejected requests include the relevant error messaging.

## 11. Order Entry Workflow

### 11.1 `NewOrderSingle <D>`

Supported Binance order semantics and required FIX fields:

| Order name | Binance Type | Side(s) | Required FIX tags |
|------------|--------------|---------|-------------------|
| Market | `MARKET` | Buy/Sell | `40=1`, `38` **or** `152` |
| Limit | `LIMIT` | Buy/Sell | `40=2`, `38`, `44`, `59` |
| Limit maker | `LIMIT_MAKER` | Buy/Sell | `40=2`, `18=6`, `38`, `44` |
| Stop-loss / Take-profit | `STOP_LOSS` / `TAKE_PROFIT` | Buy/Sell | `40=3`, `38`, trigger configuration (`1100=4`, `1101=1`, `1107=2`, `1109` depending on side, plus `1102` and/or `25009`) |
| Stop-loss-limit / Take-profit-limit | `STOP_LOSS_LIMIT` / `TAKE_PROFIT_LIMIT` | Buy/Sell | `40=4`, `38`, `44`, `59`, trigger configuration (`1100=4`, `1101=1`, `1107=2`, `1109`, plus `1102` and/or `25009`) |
| Trailing stop / take-profit | Variants above | Buy/Sell | Include `25009` (trailing delta bips) along with the applicable trigger tags |
| Pegged | `PEGGED` | Buy/Sell | `40=P`, `835=1`, `836=3`, `1094` (`4` or `5`), and optional `211` |

`CashOrderQty (152)` expresses quote-quantity market orders. Iceberg orders require `MaxFloor (111)`.

Responses:

- `ExecutionReport <8>` with `ExecType=0 (NEW)` for acceptance.
- `ExecutionReport <8>` with `ExecType=8 (REJECTED)` when the request fails.
- `Reject <3>` if the message itself is invalid.

### 11.2 `OrderCancelRequest <F>`

Provide a fresh `ClOrdID (11)` plus one of `OrderID (37)` or `OrigClOrdID (41)` (both allowed; `OrderID` is checked first). Cancelling any leg of a list cancels the entire list. Successful cancellations emit `ExecutionReport <8>` with `ExecType=4`. Failures return `OrderCancelReject <9>` with `ErrorCode (25016)` and descriptive `Text (58)`.

### 11.3 `OrderCancelRequestAndNewOrderSingle <XCN>`

Combines cancel and re-entry. Always processes the cancel first, then submits the new order. Configure behaviour with:

- `OrderCancelRequestAndNewOrderSingleMode (25033)`: `STOP_ON_FAILURE (1)` or `ALLOW_FAILURE (2)`.
- `OrderRateLimitExceededMode (25038)`: optional, instructs whether to cancel only when unfilled order limits are exceeded.

Results include cancellation and new-order `ExecutionReport <8>` messages. If the cancel fails you may also receive `OrderCancelReject <9>`.

### 11.4 `OrderMassCancelRequest <q>` / `OrderMassCancelReport <r>`

Send `ClOrdID (11)`, `Symbol (55)`, and `MassCancelRequestType=1` to cancel all open orders on a symbol. Every order generates an `ExecutionReport <8>` (`ExecType=4`); the aggregate summary arrives in `OrderMassCancelReport <r>` with `MassCancelResponse (531)` and optional `TotalAffectedOrders (533)`.

### 11.5 `NewOrderList <E>` / `ListStatus <N>`

Define contingent structures (`OCO`, `OTO`, `OTOCO`) with `ClListID (25014)` and `NoOrders (73)` (only 2 or 3 orders). Configure relationships using the `ListTrigger` repeating group:

- `ListTriggerType (25011)` ∈ {`1` activated, `2` partially filled, `3` filled}
- `ListTriggerTriggerIndex (25012)`: zero-based order index the condition references
- `ListTriggerAction (25013)` ∈ {`1` release, `2` cancel}

`ListStatus <N>` reports progression, rejections, and completion for each leg along with trigger definitions.

### 11.6 `OrderAmendKeepPriorityRequest <XAK>` / `OrderAmendReject <XAR>`

Reduces the working quantity of an existing order without losing queue priority. Reference the order via `OrderID (37)` or `OrigClOrdID (41)` (both allowed). Supply the new `OrderQty (38)`—it must be lower than the original. Successful amendments emit `ExecutionReport <8>` (and `ListStatus <N>` if part of a list). Failures trigger `OrderAmendReject <XAR>`.

## 12. Execution Reports (`ExecutionReport <8>`)

`ExecutionReport` messages track every order state change:

- `ExecType (150)` / `OrdStatus (39)`: state transition and cumulative status (`NEW`, `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `REJECTED`, `EXPIRED`, `TRADE`, etc.).
- `OrderID (37)`, `ClOrdID (11)`, `OrigClOrdID (41)`: identifiers for cross-referencing.
- Fill metrics: `CumQty (14)`, `LeavesQty (151)`, `LastQty (32)`, `LastPx (31)`, `CumQuoteQty (25017)`.
- Trade detail: `TradeID (1003)`, `AggressorIndicator (1057)`, `MatchType (574)`.
- Trigger and peg metadata: `TriggerPrice (1102)`, `TriggerPriceDirection (1109)`, `TriggerTrailingDeltaBips (25009)`, `PeggedPrice (839)`, etc.
- STP expirations: `PreventedMatchID (25024)` and related fields.
- SOR indicator: `SOR (25032)`.

## 13. Limit Monitoring Messages

- **`LimitQuery <XLQ>`:** Supply `ReqID (6136)` to query current usage. Use this to poll message limits, order limits, and unfilled order counts.
- **`LimitResponse <XLR>`:** Returns one or more `LimitIndicators` with `LimitType (25004)`, `LimitCount (25005)`, `LimitMax (25006)`, and optional reset cadence (`LimitResetInterval (25007)` plus unit `LimitResetIntervalResolution (25008)`).

## 14. Market Data Interfaces

### 14.1 Instrument Directory (`InstrumentListRequest <x>` / `InstrumentList <y>`)

- `InstrumentListRequestType (559)`: `0` for a single symbol (requires `Symbol (55)`), `4` for all active instruments.
- Responses detail quote assets, lot sizes, price filters, and market lot size boundaries.

### 14.2 Market Data Subscriptions (`MarketDataRequest <V>`)

Use `MDReqID (262)` as a unique subscription handle and set `SubscriptionRequestType (263)` to `1` (subscribe) or `2` (unsubscribe). Supported combinations:

- **Trade Stream:** `MDEntryType=TRADE (2)`, `MarketDepth` optional (typically `1`). Updates are real-time.
- **Individual Symbol Book Ticker:** `MDEntryType=BID (0)` and `OFFER (1)`, `MarketDepth=1`, optional `AggregatedBook=Y`.
- **Diff. Depth Stream:** `MDEntryType=BID/OFFER`, `MarketDepth` between 2 and 5000 (sets initial snapshot depth). Incrementals arrive every 100 ms.

Initial snapshots use `MarketDataSnapshot <W>` and include `LastBookUpdateID (25044)` for depth tracking. Incremental updates arrive via `MarketDataIncrementalRefresh <X>` with `MDUpdateAction (279)` (`NEW`, `CHANGE`, `DELETE`). Diff depth streams include `FirstBookUpdateID (25043)` / `LastBookUpdateID (25044)`. When a message would exceed 10,000 entries it is fragmented; fragments are sequential and flagged with `LastFragment (893)`.

### 14.3 Market Data Rejects (`MarketDataRequestReject <Y>`)

Invalid or duplicate subscriptions return `MarketDataRequestReject <Y>` detailing the issue through `MDReqRejReason (281)`, optional `ErrorCode (25016)`, and descriptive `Text (58)`.

## 15. Error Handling

The exchange rejects malformed messages via `Reject <3>` or the corresponding application-level reject (`OrderCancelReject <9>`, `OrderAmendReject <XAR>`, etc.). Inspect `Text (58)` and `ErrorCode (25016)` for actionable diagnostics and consult the published error code list for enumerations.

---

**Reminder:** Monitor User Data Streams or REST fallbacks to reconcile order status after timeouts or disconnects, and poll `LimitQuery <XLQ>` to track remaining capacity.
