# Binance Error Codes

_Last updated: 2025-10-28_

Binance error responses contain an integer `code` and a string `msg`. Codes are consistent across responses, but the message can vary slightly by endpoint.

## Example Error Payload

```json
{
  "code": -1121,
  "msg": "Invalid symbol."
}
```

## Error Code Reference

### 10xx – General Server or Network Issues

- **-1000 UNKNOWN**  
  An unknown error occurred while processing the request.
- **-1001 DISCONNECTED**  
  Internal error; unable to process your request. Please try again.
- **-1002 UNAUTHORIZED**  
  You are not authorized to execute this request.
- **-1003 TOO_MANY_REQUESTS**  
  Too many requests queued.  
  Too much request weight used; current limit is `%s` request weight per `%s`. Please use WebSocket Streams for live updates to avoid polling the API.  
  Way too much request weight used; IP banned until `%s`. Please use WebSocket Streams for live updates to avoid bans.
- **-1006 UNEXPECTED_RESP**  
  An unexpected response was received from the message bus. Execution status unknown.
- **-1007 TIMEOUT**  
  Timeout waiting for response from backend server. Send status unknown; execution status unknown.
- **-1008 SERVER_BUSY**  
  Server is currently overloaded with other requests. Please try again in a few minutes.
- **-1010 ERROR_MSG_RECEIVED**  
  This code is sent when an error has been returned by the matching engine. See [Matching Engine Error Messages](#matching-engine-error-messages).
- **-1013 INVALID_MESSAGE**  
  The request is rejected by the API (the request did not reach the Matching Engine). Potential error messages can be found in filter failures or failures during order placement.
- **-1014 UNKNOWN_ORDER_COMPOSITION**  
  Unsupported order combination.
- **-1015 TOO_MANY_ORDERS**  
  Too many new orders.  
  Too many new orders; current limit is `%s` orders per `%s`.
- **-1016 SERVICE_SHUTTING_DOWN**  
  This service is no longer available.
- **-1020 UNSUPPORTED_OPERATION**  
  This operation is not supported.
- **-1021 INVALID_TIMESTAMP**  
  Timestamp for this request is outside of the `recvWindow`.  
  Timestamp for this request was 1000 ms ahead of the server's time.
- **-1022 INVALID_SIGNATURE**  
  Signature for this request is not valid.
- **-1033 COMP_ID_IN_USE**  
  `SenderCompId (49)` is currently in use. Concurrent use of the same `SenderCompId` within one account is not allowed.
- **-1034 TOO_MANY_CONNECTIONS**  
  Too many concurrent connections; current limit is `%s`.  
  Too many connection attempts for account; current limit is `%s` per `%s`.  
  Too many connection attempts from IP; current limit is `%s` per `%s`.
- **-1035 LOGGED_OUT**  
  Please send `Logout<5>` message to close the session.

### 11xx – Request Issues

- **-1100 ILLEGAL_CHARS**  
  Illegal characters found in a parameter.  
  Illegal characters found in parameter `%s`; legal range is `%s`.
- **-1101 TOO_MANY_PARAMETERS**  
  Too many parameters sent for this endpoint.  
  Too many parameters; expected `%s` and received `%s`.  
  Duplicate values for a parameter detected.
- **-1102 MANDATORY_PARAM_EMPTY_OR_MALFORMED**  
  A mandatory parameter was not sent, was empty/null, or malformed.  
  Mandatory parameter `%s` was not sent, was empty/null, or malformed.  
  `Param '%s' or '%s' must be sent, but both were empty/null!`  
  Required tag `%s` missing.  
  Field value was empty or malformed.  
  `'%s' contains unexpected value. Cannot be greater than %s.`
- **-1103 UNKNOWN_PARAM**  
  An unknown parameter was sent.  
  Undefined Tag.
- **-1104 UNREAD_PARAMETERS**  
  Not all sent parameters were read.  
  Not all sent parameters were read; read `%s` parameter(s) but was sent `%s`.
- **-1105 PARAM_EMPTY**  
  A parameter was empty.  
  Parameter `%s` was empty.
- **-1106 PARAM_NOT_REQUIRED**  
  A parameter was sent when not required.  
  Parameter `%s` sent when not required.  
  Tag `%s` was sent when not required.
- **-1108 PARAM_OVERFLOW**  
  Parameter `%s` overflowed.
- **-1111 BAD_PRECISION**  
  Parameter `%s` has too much precision.
- **-1112 NO_DEPTH**  
  No orders on book for symbol.
- **-1114 TIF_NOT_REQUIRED**  
  `timeInForce` parameter sent when not required.
- **-1115 INVALID_TIF**  
  Invalid `timeInForce`.
- **-1116 INVALID_ORDER_TYPE**  
  Invalid `orderType`.
- **-1117 INVALID_SIDE**  
  Invalid `side`.
- **-1118 EMPTY_NEW_CL_ORD_ID**  
  New client order ID was empty.
- **-1119 EMPTY_ORG_CL_ORD_ID**  
  Original client order ID was empty.
- **-1120 BAD_INTERVAL**  
  Invalid interval.
- **-1121 BAD_SYMBOL**  
  Invalid symbol.
- **-1122 INVALID_SYMBOLSTATUS**  
  Invalid `symbolStatus`.
- **-1125 INVALID_LISTEN_KEY**  
  This `listenKey` does not exist.
- **-1127 MORE_THAN_XX_HOURS**  
  Lookup interval is too big.  
  More than `%s` hours between `startTime` and `endTime`.
- **-1128 OPTIONAL_PARAMS_BAD_COMBO**  
  Combination of optional parameters invalid.  
  Combination of optional fields invalid. Recommendation: `%s` and `%s` must both be sent.  
  Fields [`%s`] must be sent together or omitted entirely.  
  Invalid `MDEntryType (269)` combination. BID and OFFER must be requested together.
- **-1130 INVALID_PARAMETER**  
  Invalid data sent for a parameter.  
  Data sent for parameter `%s` is not valid.
- **-1134 BAD_STRATEGY_TYPE**  
  `strategyType` was less than `1000000`.  
  `TargetStrategy (847)` was less than `1000000`.
- **-1135 INVALID_JSON**  
  Invalid JSON request.  
  JSON sent for parameter `%s` is not valid.
- **-1139 INVALID_TICKER_TYPE**  
  Invalid ticker type.
- **-1145 INVALID_CANCEL_RESTRICTIONS**  
  `cancelRestrictions` has to be either `ONLY_NEW` or `ONLY_PARTIALLY_FILLED`.
- **-1151 DUPLICATE_SYMBOLS**  
  Symbol is present multiple times in the list.
- **-1152 INVALID_SBE_HEADER**  
  Invalid `X-MBX-SBE` header; expected `<SCHEMA_ID>:<VERSION>`.
- **-1153 UNSUPPORTED_SCHEMA_ID**  
  Unsupported SBE schema ID or version specified in the `X-MBX-SBE` header.
- **-1155 SBE_DISABLED**  
  SBE is not enabled.
- **-1158 OCO_ORDER_TYPE_REJECTED**  
  Order type not supported in OCO.  
  If the order type provided in the `aboveType` and/or `belowType` is not supported.
- **-1160 OCO_ICEBERGQTY_TIMEINFORCE**  
  Parameter `%s` is not supported if `aboveTimeInForce`/`belowTimeInForce` is not `GTC`.  
  If the order type for the above or below leg is `STOP_LOSS_LIMIT`, and `icebergQty` is provided for that leg, the `timeInForce` has to be `GTC` else it will throw an error.  
  `TimeInForce (59)` must be GTC (1) when `MaxFloor (111)` is used.
- **-1161 DEPRECATED_SCHEMA**  
  Unable to encode the response in SBE schema `x`. Please use schema `y` or higher.
- **-1165 BUY_OCO_LIMIT_MUST_BE_BELOW**  
  A limit order in a buy OCO must be below.
- **-1166 SELL_OCO_LIMIT_MUST_BE_ABOVE**  
  A limit order in a sell OCO must be above.
- **-1168 BOTH_OCO_ORDERS_CANNOT_BE_LIMIT**  
  At least one OCO order must be contingent.
- **-1169 INVALID_TAG_NUMBER**  
  Invalid tag number.
- **-1170 TAG_NOT_DEFINED_IN_MESSAGE**  
  Tag `%s` not defined for this message type.
- **-1171 TAG_APPEARS_MORE_THAN_ONCE**  
  Tag `%s` appears more than once.
- **-1172 TAG_OUT_OF_ORDER**  
  Tag `%s` specified out of required order.
- **-1173 GROUP_FIELDS_OUT_OF_ORDER**  
  Repeating group `%s` fields out of order.
- **-1174 INVALID_COMPONENT**  
  Component `%s` is incorrectly populated on `%s` order. Recommendation: `%s`.
- **-1175 RESET_SEQ_NUM_SUPPORT**  
  Continuation of sequence numbers to new session is currently unsupported. Sequence numbers must be reset for each new session.
- **-1176 ALREADY_LOGGED_IN**  
  `Logon<A>` should only be sent once.
- **-1177 GARBLED_MESSAGE**  
  `CheckSum (10)` contains an incorrect value.  
  `BeginString (8)` is not the first tag in a message.  
  `MsgType (35)` is not the third tag in a message.  
  `BodyLength (9)` does not contain the correct byte count.  
  Only printable ASCII characters and SOH (Start of Header) are allowed.  
  Tag specified without a value.
- **-1178 BAD_SENDER_COMPID**  
  `SenderCompId (49)` contains an incorrect value. The `SenderCompID` value should not change throughout the lifetime of a session.
- **-1179 BAD_SEQ_NUM**  
  `MsgSeqNum (34)` contains an unexpected value. Expected: `%d`.
- **-1180 EXPECTED_LOGON**  
  `Logon<A>` must be the first message in the session.
- **-1181 TOO_MANY_MESSAGES**  
  Too many messages; current limit is `%d` messages per `%s`.
- **-1182 PARAMS_BAD_COMBO**  
  Conflicting fields: [`%s`].
- **-1183 NOT_ALLOWED_IN_DROP_COPY_SESSIONS**  
  Requested operation is not allowed in DropCopy sessions.
- **-1184 DROP_COPY_SESSION_NOT_ALLOWED**  
  DropCopy sessions are not supported on this server. Please reconnect to a drop copy server.
- **-1185 DROP_COPY_SESSION_REQUIRED**  
  Only DropCopy sessions are supported on this server. Either reconnect to order entry server or send `DropCopyFlag (9406)` field.
- **-1186 NOT_ALLOWED_IN_ORDER_ENTRY_SESSIONS**  
  Requested operation is not allowed in order entry sessions.
- **-1187 NOT_ALLOWED_IN_MARKET_DATA_SESSIONS**  
  Requested operation is not allowed in market data sessions.
- **-1188 INCORRECT_NUM_IN_GROUP_COUNT**  
  Incorrect `NumInGroup` count for repeating group `%s`.
- **-1189 DUPLICATE_ENTRIES_IN_A_GROUP**  
  Group `%s` contains duplicate entries.
- **-1190 INVALID_REQUEST_ID**  
  `MDReqID (262)` contains a subscription request id that is already in use on this connection.  
  `MDReqID (262)` contains an unsubscription request id that does not match any active subscription.
- **-1191 TOO_MANY_SUBSCRIPTIONS**  
  Too many subscriptions. Connection may create up to `%s` subscriptions at a time.  
  Similar subscription is already active on this connection. `Symbol='%s'`, active subscription id: `%s`.
- **-1194 INVALID_TIME_UNIT**  
  Invalid value for time unit; expected either `MICROSECOND` or `MILLISECOND`.
- **-1196 BUY_OCO_STOP_LOSS_MUST_BE_ABOVE**  
  A stop loss order in a buy OCO must be above.
- **-1197 SELL_OCO_STOP_LOSS_MUST_BE_BELOW**  
  A stop loss order in a sell OCO must be below.
- **-1198 BUY_OCO_TAKE_PROFIT_MUST_BE_BELOW**  
  A take profit order in a buy OCO must be below.
- **-1199 SELL_OCO_TAKE_PROFIT_MUST_BE_ABOVE**  
  A take profit order in a sell OCO must be above.
- **-1210 INVALID_PEG_PRICE_TYPE**  
  Invalid `pegPriceType`.
- **-1211 INVALID_PEG_OFFSET_TYPE**  
  Invalid `pegOffsetType`.
- **-1220 SYMBOL_DOES_NOT_MATCH_STATUS**  
  The symbol's status does not match the requested `symbolStatus`.

### 20xx – Trading Errors

- **-2010 NEW_ORDER_REJECTED**  
  `NEW_ORDER_REJECTED`
- **-2011 CANCEL_REJECTED**  
  `CANCEL_REJECTED`
- **-2013 NO_SUCH_ORDER**  
  Order does not exist.
- **-2014 BAD_API_KEY_FMT**  
  API-key format invalid.
- **-2015 REJECTED_MBX_KEY**  
  Invalid API-key, IP, or permissions for action.
- **-2016 NO_TRADING_WINDOW**  
  No trading window could be found for the symbol. Try `/ticker/24hrs` instead.
- **-2021 ORDER_CANCEL_REPLACE_PARTIALLY_FAILED**  
  Order cancel-replace partially failed. Either the cancellation failed or the new order placement failed, but not both.
- **-2022 ORDER_CANCEL_REPLACE_FAILED**  
  Both the cancellation and the new order placement failed.
- **-2026 ORDER_ARCHIVED**  
  Order was canceled or expired with no executed quantity over 90 days ago and has been archived.
- **-2035 SUBSCRIPTION_ACTIVE**  
  User Data Stream subscription already active.
- **-2036 SUBSCRIPTION_INACTIVE**  
  User Data Stream subscription not active.
- **-2038 ORDER_AMEND_REJECTED**  
  Matching engine rejected an order amend. See [Matching Engine Error Messages](#matching-engine-error-messages).
- **-2039 CLIENT_ORDER_ID_INVALID**  
  Client order ID is not correct for this order ID.
- **-2042 MAXIMUM_SUBSCRIPTION_IDS**  
  Maximum subscription ID reached for this connection.

### Matching Engine Error Messages

The following messages can accompany error codes `-1010`, `-2010`, `-2011`, and `-2038` and indicate the specific matching engine failure:

- "Unknown order sent." – The order (by either `orderId`, `clOrdId`, `origClOrdId`) could not be found.
- "Duplicate order sent." – The `clOrdId` is already in use.
- "Market is closed." – The symbol is not trading.
- "Account has insufficient balance for requested action." – Not enough funds to complete the action.
- "Market orders are not supported for this symbol." – `MARKET` is not enabled on the symbol.
- "Iceberg orders are not supported for this symbol." – `icebergQty` is not enabled on the symbol.
- "Stop loss orders are not supported for this symbol." – `STOP_LOSS` is not enabled on the symbol.
- "Stop loss limit orders are not supported for this symbol." – `STOP_LOSS_LIMIT` is not enabled on the symbol.
- "Take profit orders are not supported for this symbol." – `TAKE_PROFIT` is not enabled on the symbol.
- "Take profit limit orders are not supported for this symbol." – `TAKE_PROFIT_LIMIT` is not enabled on the symbol.
- "Order amend is not supported for this symbol." – Order amend keep priority is not enabled on the symbol.
- "Price * QTY is zero or less." – `price * quantity` is too low.
- "IcebergQty exceeds QTY." – `icebergQty` must be less than the order quantity.
- "This action is disabled on this account." – Contact customer support; some actions have been disabled on the account.
- "This account may not place or cancel orders." – Contact customer support; the account has trading ability disabled.
- "Unsupported order combination." – The `orderType`, `timeInForce`, `stopPrice`, and/or `icebergQty` combination isn't allowed.
- "Order would trigger immediately." – The order's stop price is not valid when compared to the last traded price.
- "Cancel order is invalid. Check origClOrdId and orderId." – No `origClOrdId` or `orderId` was sent in.
- "Order would immediately match and take." – `LIMIT_MAKER` order type would immediately match and trade, and not be a pure maker order.
- "The relationship of the prices for the orders is not correct." – The prices set in the OCO break the price restrictions.  
  - **BUY:** `LIMIT_MAKER price < Last Traded Price < stopPrice`  
  - **SELL:** `LIMIT_MAKER price > Last Traded Price > stopPrice`
- "OCO orders are not supported for this symbol." – OCO is not enabled on the symbol.
- "Quote order qty market orders are not support for this symbol." – `MARKET` orders using the parameter `quoteOrderQty` are not enabled on the symbol.
- "Trailing stop orders are not supported for this symbol." – Orders using `trailingDelta` are not enabled on the symbol.
- "Order cancel-replace is not supported for this symbol." – `POST /api/v3/order/cancelReplace` (REST API) or `order.cancelReplace` (WebSocket API) is not enabled on the symbol.
- "This symbol is not permitted for this account." – Account and symbol do not have the same permissions (e.g., SPOT, MARGIN, etc.).
- "This symbol is restricted for this account." – Account is unable to trade on that symbol (e.g., an `ISOLATED_MARGIN` account cannot place SPOT orders).
- "Order was not canceled due to cancel restrictions." – Either `cancelRestrictions` was set to `ONLY_NEW` but the order status was not `NEW`, or `cancelRestrictions` was set to `ONLY_PARTIALLY_FILLED` but the order status was not `PARTIALLY_FILLED`.
- "Rest API trading is not enabled." / "WebSocket API trading is not enabled." – Order is being placed on a server that is not configured to allow access to TRADE endpoints.
- "FIX API trading is not enabled." – Order is placed on a FIX server that is not TRADE enabled.
- "Order book liquidity is less than LOT_SIZE filter minimum quantity." – Quote quantity market orders cannot be placed when the order book liquidity is less than minimum quantity configured for the `LOT_SIZE` filter.
- "Order book liquidity is less than MARKET_LOT_SIZE filter minimum quantity." – Quote quantity market orders cannot be placed when the order book liquidity is less than the minimum quantity for `MARKET_LOT_SIZE` filter.
- "Order book liquidity is less than symbol minimum quantity." – Quote quantity market orders cannot be placed when there are no orders on the book.
- "Order amend (quantity increase) is not supported." – `newQty` must be less than the order quantity.
- "The requested action would change no state; rejecting." – The request sent would not have changed the status quo (e.g., `newQty` cannot equal the order quantity).
- "Pegged orders are not supported for this symbol." – `pegInstructionsAllowed` has not been enabled.
- "This order type may not use pegged price." – You are using parameter `pegPriceType` with an unsupported order type (e.g., `MARKET`).
- "This price peg cannot be used with this order type." – You are using `pegPriceType=MARKET_PEG` for a `LIMIT_MAKER` order.
- "Order book liquidity is too low for this pegged order." – The order book doesn’t have the best price level to peg the price to.

### 30xx – Margin & SAPI Issues

- **-3000 INNER_FAILURE** – Internal server error.
- **-3001 NEED_ENABLE_2FA** – Please enable 2FA first.
- **-3002 ASSET_DEFICIENCY** – The requested asset is unavailable.
- **-3003 NO_OPENED_MARGIN_ACCOUNT** – Margin account does not exist.
- **-3004 TRADE_NOT_ALLOWED** – Trading is not allowed.
- **-3005 TRANSFER_OUT_NOT_ALLOWED** – Transferring out is not allowed.
- **-3006 EXCEED_MAX_BORROWABLE** – Borrow amount exceeds the maximum borrowable amount.
- **-3007 HAS_PENDING_TRANSACTION** – Pending transaction detected; try again later.
- **-3008 BORROW_NOT_ALLOWED** – Borrow action is not allowed.
- **-3009 ASSET_NOT_MORTGAGEABLE** – Asset cannot be transferred into margin account currently.
- **-3010 REPAY_NOT_ALLOWED** – Repay is not allowed.
- **-3011 BAD_DATE_RANGE** – Input date is invalid.
- **-3012 ASSET_ADMIN_BAN_BORROW** – Borrowing is banned for this asset.
- **-3013 LT_MIN_BORROWABLE** – Borrow amount is less than the minimum borrowable amount.
- **-3014 ACCOUNT_BAN_BORROW** – Borrowing is banned for this account.
- **-3015 REPAY_EXCEED_LIABILITY** – Repay amount exceeds borrow amount.
- **-3016 LT_MIN_REPAY** – Repay amount is less than the minimum repay amount.
- **-3017 ASSET_ADMIN_BAN_MORTGAGE** – Asset cannot be transferred into margin account currently.
- **-3018 ACCOUNT_BAN_MORTGAGE** – Transferring in has been banned for this account.
- **-3019 ACCOUNT_BAN_ROLLOUT** – Transferring out has been banned for this account.
- **-3020 EXCEED_MAX_ROLLOUT** – Transfer-out amount exceeds the maximum allowed.
- **-3021 PAIR_ADMIN_BAN_TRADE** – Margin account cannot trade this trading pair.
- **-3022 ACCOUNT_BAN_TRADE** – Account trading is banned.
- **-3023 WARNING_MARGIN_LEVEL** – Cannot transfer out/place order under current margin level.
- **-3024 FEW_LIABILITY_LEFT** – Unpaid debt would be too small after this repayment.
- **-3025 INVALID_EFFECTIVE_TIME** – Input date is invalid.
- **-3026 VALIDATION_FAILED** – Parameter validation failed.
- **-3027 NOT_VALID_MARGIN_ASSET** – Not a valid margin asset.
- **-3028 NOT_VALID_MARGIN_PAIR** – Not a valid margin pair.
- **-3029 TRANSFER_FAILED** – Transfer failed.
- **-3036 ACCOUNT_BAN_REPAY** – Account is not allowed to repay.
- **-3037 PNL_CLEARING** – PNL is clearing; wait a moment.
- **-3038 LISTEN_KEY_NOT_FOUND** – Listen key not found.
- **-3041 BALANCE_NOT_CLEARED** – Insufficient balance.
- **-3042 PRICE_INDEX_NOT_FOUND** – Price index not available for this margin pair.
- **-3043 TRANSFER_IN_NOT_ALLOWED** – Transferring in not allowed.
- **-3044 SYSTEM_BUSY** – System busy; retry later.
- **-3045 SYSTEM** – System lacks sufficient asset.
- **-3999 NOT_WHITELIST_USER** – Function is available only for invited users.
- **-4001 CAPITAL_INVALID** – Invalid capital operation.
- **-4002 CAPITAL_IG** – Invalid capital get request.
- **-4003 CAPITAL_IEV** – Input email is invalid.
- **-4004 CAPITAL_UA** – User not logged in or authenticated.
- **-4005 CAPAITAL_TOO_MANY_REQUEST** – Too many new requests.
- **-4006 CAPITAL_ONLY_SUPPORT_PRIMARY_ACCOUNT** – Operation supports main account only.
- **-4007 CAPITAL_ADDRESS_VERIFICATION_NOT_PASS** – Address validation failed.
- **-4008 CAPITAL_ADDRESS_TAG_VERIFICATION_NOT_PASS** – Address tag validation failed.
- **-4010 CAPITAL_WHITELIST_EMAIL_CONFIRM** – Whitelist email already confirmed.
- **-4011 CAPITAL_WHITELIST_EMAIL_EXPIRED** – Whitelist email is invalid or expired.
- **-4012 CAPITAL_WHITELIST_CLOSE** – Whitelist is not open.
- **-4013 CAPITAL_WITHDRAW_2FA_VERIFY** – 2FA not enabled for withdrawal.
- **-4014 CAPITAL_WITHDRAW_LOGIN_DELAY** – Withdrawals blocked within two minutes of login.
- **-4015 CAPITAL_WITHDRAW_RESTRICTED_MINUTE** – Withdrawal temporarily limited.
- **-4016 CAPITAL_WITHDRAW_RESTRICTED_PASSWORD** – Withdrawal prohibited within 24 hours of password change.
- **-4017 CAPITAL_WITHDRAW_RESTRICTED_UNBIND_2FA** – Withdrawal prohibited within 24 hours of removing 2FA.
- **-4018 CAPITAL_WITHDRAW_ASSET_NOT_EXIST** – Asset does not exist.
- **-4019 CAPITAL_WITHDRAW_ASSET_PROHIBIT** – Asset withdrawal not open.
- **-4021 CAPITAL_WITHDRAW_AMOUNT_MULTIPLE** – Withdrawal must be an `%s` multiple of `%s`.
- **-4022 CAPITAL_WITHDRAW_MIN_AMOUNT** – Withdrawal less than minimum amount `%s`.
- **-4023 CAPITAL_WITHDRAW_MAX_AMOUNT** – Withdrawal exceeds 24-hour maximum.
- **-4024 CAPITAL_WITHDRAW_USER_NO_ASSET** – User does not hold this asset.
- **-4025 CAPITAL_WITHDRAW_USER_ASSET_LESS_THAN_ZERO** – Held asset quantity is less than zero.
- **-4026 CAPITAL_WITHDRAW_USER_ASSET_NOT_ENOUGH** – Insufficient balance for withdrawal.
- **-4027 CAPITAL_WITHDRAW_GET_TRAN_ID_FAILURE** – Failed to obtain `tranId`.
- **-4028 CAPITAL_WITHDRAW_MORE_THAN_FEE** – Withdrawal amount must exceed the fee.
- **-4029 CAPITAL_WITHDRAW_NOT_EXIST** – Withdrawal record does not exist.
- **-4030 CAPITAL_WITHDRAW_CONFIRM_SUCCESS** – Withdrawal confirmation succeeded.
- **-4031 CAPITAL_WITHDRAW_CANCEL_FAILURE** – Withdrawal cancellation failed.
- **-4032 CAPITAL_WITHDRAW_CHECKSUM_VERIFY_FAILURE** – Withdrawal verification exception.
- **-4033 CAPITAL_WITHDRAW_ILLEGAL_ADDRESS** – Illegal address detected.
- **-4034 CAPITAL_WITHDRAW_ADDRESS_CHEAT** – Address suspected of being fake.
- **-4035 CAPITAL_WITHDRAW_NOT_WHITE_ADDRESS** – Address not on whitelist.
- **-4036 CAPITAL_WITHDRAW_NEW_ADDRESS** – New address requires waiting `{0}` hours before withdrawal.
- **-4037 CAPITAL_WITHDRAW_RESEND_EMAIL_FAIL** – Failed to resend confirmation email.
- **-4038 CAPITAL_WITHDRAW_RESEND_EMAIL_TIME_OUT** – Please retry in five minutes.
- **-4039 CAPITAL_USER_EMPTY** – User does not exist.
- **-4040 CAPITAL_NO_CHARGE** – Address has no deposit history.
- **-4041 CAPITAL_MINUTE_TOO_SMALL** – Please retry in one minute.
- **-4042 CAPITAL_CHARGE_NOT_RESET** – Cannot reissue deposit address for this asset.
- **-4043 CAPITAL_ADDRESS_TOO_MUCH** – More than 100 recharge addresses used in 24 hours.
- **-4044 CAPITAL_BLACKLIST_COUNTRY_GET_ADDRESS** – Address request denied for blacklist country.
- **-4045 CAPITAL_GET_ASSET_ERROR** – Failed to acquire asset data.
- **-4046 CAPITAL_AGREEMENT_NOT_CONFIRMED** – Agreement not confirmed.
- **-4047 CAPITAL_DATE_INTERVAL_LIMIT** – Time interval must be within 0–90 days.
- **-4060 CAPITAL_WITHDRAW_USER_ASSET_LOCK_DEPOSIT** – Deposit awaiting confirmations; `{0}` asset temporarily locked.

### 50xx – Asset Conversion & Transfers

- **-5001 ASSET_DRIBBLET_CONVERT_SWITCH_OFF** – Transfer to micro assets disabled.
- **-5002 ASSET_ASSET_NOT_ENOUGH** – Insufficient balance.
- **-5003 ASSET_USER_HAVE_NO_ASSET** – User does not hold this asset.
- **-5004 USER_OUT_OF_TRANSFER_FLOAT** – Residual balances exceed `0.001 BTC`; reselect assets.
- **-5005 USER_ASSET_AMOUNT_IS_TOO_LOW** – Residual balance is too low.
- **-5006 USER_CAN_NOT_REQUEST_IN_24_HOURS** – Only one transfer allowed per 24 hours.
- **-5007 AMOUNT_OVER_ZERO** – Quantity must be greater than zero.
- **-5008 ASSET_WITHDRAW_WITHDRAWING_NOT_ENOUGH** – Insufficient amount of returnable assets.
- **-5009 PRODUCT_NOT_EXIST** – Product does not exist.
- **-5010 TRANSFER_FAIL** – Asset transfer failed.
- **-5011 FUTURE_ACCT_NOT_EXIST** – Futures account does not exist.
- **-5012 TRANSFER_PENDING** – Asset transfer pending.
- **-5021 PARENT_SUB_HAVE_NO_RELATION** – Parent and sub-account have no relationship.
- **-5012 FUTURE_ACCT_OR_SUBRELATION_NOT_EXIST** – Futures account or sub-account relationship does not exist.

### 60xx – Savings Issues

- **-6001 DAILY_PRODUCT_NOT_EXIST** – Daily product does not exist.
- **-6003 DAILY_PRODUCT_NOT_ACCESSIBLE** – Product unavailable or permission denied.
- **-6004 DAILY_PRODUCT_NOT_PURCHASABLE** – Product not purchasable.
- **-6005 DAILY_LOWER_THAN_MIN_PURCHASE_LIMIT** – Purchase amount below minimum limit.
- **-6006 DAILY_REDEEM_AMOUNT_ERROR** – Redeem amount error.
- **-6007 DAILY_REDEEM_TIME_ERROR** – Not within redeem time.
- **-6008 DAILY_PRODUCT_NOT_REDEEMABLE** – Product not in redeem status.
- **-6009 REQUEST_FREQUENCY_TOO_HIGH** – Request frequency too high.
- **-6011 EXCEEDED_USER_PURCHASE_LIMIT** – Exceeded user purchase limit.
- **-6012 BALANCE_NOT_ENOUGH** – Balance insufficient.
- **-6013 PURCHASING_FAILED** – Purchase failed.
- **-6014 UPDATE_FAILED** – Exceeded maximum allowed purchase quantity.
- **-6015 EMPTY_REQUEST_BODY** – Request body is empty.
- **-6016 PARAMS_ERR** – Parameter error.
- **-6017 NOT_IN_WHITELIST** – User not in whitelist.
- **-6018 ASSET_NOT_ENOUGH** – Asset amount insufficient.
- **-6019 PENDING** – Request pending confirmation.
- **-6020 PROJECT_NOT_EXISTS** – Project does not exist.

### 70xx – Futures Issues

- **-7001 FUTURES_BAD_DATE_RANGE** – Unsupported date range.
- **-7002 FUTURES_BAD_TYPE** – Unsupported data request type.

### 20xxx – Futures & Spot Algo

- **-20121** – Invalid symbol.
- **-20124** – Invalid algo ID or already completed.
- **-20130** – Invalid data sent for a parameter.
- **-20132** – Client algo ID is duplicated.
- **-20194** – Duration too short to execute required quantity.
- **-20195** – Total size too small.
- **-20196** – Total size too large.
- **-20198** – Maximum open orders reached.
- **-20204** – USD notional outside permitted limit.

### 10xxx – Crypto Loans

- **-10001 SYSTEM_MAINTENANCE** – System under maintenance.
- **-10002 INVALID_INPUT** – Invalid input parameters.
- **-10005 NO_RECORDS** – No records found.
- **-10007 COIN_NOT_LOANABLE** – Coin is not loanable.
- **-10008 COIN_NOT_LOANABLE** – Coin is not loanable.
- **-10009 COIN_NOT_COLLATERAL** – Coin cannot be used as collateral.
- **-10010 COIN_NOT_COLLATERAL** – Coin cannot be used as collateral.
- **-10011 INSUFFICIENT_ASSET** – Insufficient spot assets.
- **-10012 INVALID_AMOUNT** – Invalid repayment amount.
- **-10013 INSUFFICIENT_AMOUNT** – Insufficient collateral amount.
- **-10015 DEDUCTION_FAILED** – Collateral deduction failed.
- **-10016 LOAN_FAILED** – Failed to provide loan.
- **-10017 REPAY_EXCEED_DEBT** – Repayment exceeds debt.
- **-10018 INVALID_AMOUNT** – Invalid repayment amount.
- **-10019 CONFIG_NOT_EXIST** – Configuration does not exist.
- **-10020 UID_NOT_EXIST** – User ID does not exist.
- **-10021 ORDER_NOT_EXIST** – Order does not exist.
- **-10022 INVALID_AMOUNT** – Invalid adjustment amount.
- **-10023 ADJUST_LTV_FAILED** – Failed to adjust LTV.
- **-10024 ADJUST_LTV_NOT_SUPPORTED** – LTV adjustment not supported.
- **-10025 REPAY_FAILED** – Repayment failed.
- **-10026 INVALID_PARAMETER** – Invalid parameter.
- **-10028 INVALID_PARAMETER** – Invalid parameter.
- **-10029 AMOUNT_TOO_SMALL** – Loan amount too small.
- **-10030 AMOUNT_TOO_LARGE** – Loan amount too large.
- **-10031 QUOTA_REACHED** – Individual loan quota reached.
- **-10032 REPAY_NOT_AVAILABLE** – Repayment temporarily unavailable.
- **-10034 REPAY_NOT_AVAILABLE** – Collateral repayment unavailable; try using borrowed coin.
- **-10039 AMOUNT_TOO_SMALL** – Repayment amount too small.
- **-10040 AMOUNT_TOO_LARGE** – Repayment amount too large.
- **-10041 INSUFFICIENT_AMOUNT** – Insufficient loanable assets for `{0}`; adjust amount or retry later.
- **-10042 ASSET_NOT_SUPPORTED** – Asset `%s` not supported.
- **-10043 ASSET_NOT_SUPPORTED** – Borrowing not supported for `{0}`.
- **-10044 QUOTA_REACHED** – Collateral amount reached limit.
- **-10045 COLLTERAL_REPAY_NOT_SUPPORTED** – Collateral repayment not supported for the loan coin.
- **-10046 EXCEED_MAX_ADJUSTMENT** – Collateral adjustment exceeds maximum.
- **-10047 REGION_NOT_SUPPORTED** – Coin not supported in user region due to regulations.

### 12xxx – Liquid Swap

- **-12014 TOO_MANY_REQUESTS** – More than one request in two seconds.

### 13xxx – BLVT (Leveraged Tokens)

- **-13000 BLVT_FORBID_REDEEM** – Redemption of the token is forbidden.
- **-13001 BLVT_EXCEED_DAILY_LIMIT** – Exceeds individual 24-hour redemption limit.
- **-13002 BLVT_EXCEED_TOKEN_DAILY_LIMIT** – Exceeds total 24-hour redemption limit for the token.
- **-13003 BLVT_FORBID_PURCHASE** – Subscription of the token is forbidden.
- **-13004 BLVT_EXCEED_DAILY_PURCHASE_LIMIT** – Exceeds individual 24-hour subscription limit.
- **-13005 BLVT_EXCEED_TOKEN_DAILY_PURCHASE_LIMIT** – Exceeds total 24-hour subscription limit.
- **-13006 BLVT_PURCHASE_LESS_MIN_AMOUNT** – Subscription amount too small.
- **-13007 BLVT_PURCHASE_AGREEMENT_NOT_SIGN** – Agreement not signed.

### 18xxx – Binance Code

- **-18002** – Total amount of codes created exceeds 24-hour limit; try again after UTC 0.
- **-18003** – Too many codes created in 24 hours; retry after UTC 0.
- **-18004** – Too many invalid redeem attempts in 24 hours; retry after UTC 0.
- **-18005** – Too many invalid verify attempts; try again later.
- **-18006** – Amount too small; re-enter value.
- **-18007** – Token not supported; re-enter value.

### 21xxx – Portfolio Margin Account

- **-21001 USER_IS_NOT_UNIACCOUNT** – Request ID is not a Portfolio Margin Account.
- **-21002 UNI_ACCOUNT_CANT_TRANSFER_FUTURE** – Portfolio Margin Account cannot transfer from margin to futures.
- **-21003 NET_ASSET_MUST_LTE_RATIO** – Failed to retrieve margin assets.
- **-21004 USER_NO_LIABILITY** – User has no portfolio margin bankruptcy loan.
- **-21005 NO_ENOUGH_ASSET** – Spot wallet lacks sufficient BUSD to repay bankruptcy loan.
- **-21006 HAD_IN_PROCESS_REPAY** – Repayment already in process.
- **-21007 IN_FORCE_LIQUIDATION** – Repayment failed because liquidation is in process.

### Filter Failures

- "Filter failure: PRICE_FILTER" – Price is too high, too low, and/or not following the tick size rule for the symbol.
- "Filter failure: PERCENT_PRICE" – Price is X% too high or X% too low from the average weighted price over the last Y minutes.
- "Filter failure: LOT_SIZE" – Quantity is too high, too low, and/or not following the step size rule for the symbol.
- "Filter failure: MIN_NOTIONAL" – `price * quantity` is too low to be a valid order for the symbol.
- "Filter failure: NOTIONAL" – `price * quantity` is not within range of the `minNotional` and `maxNotional`.
- "Filter failure: ICEBERG_PARTS" – ICEBERG order would break into too many parts; `icebergQty` is too small.
- "Filter failure: MARKET_LOT_SIZE" – `MARKET` order's quantity is too high, too low, and/or not following the step size rule for the symbol.
- "Filter failure: MAX_POSITION" – The account's position has reached the maximum defined limit (sum of the balance of the base asset and the quantity of all open BUY orders).
- "Filter failure: MAX_NUM_ORDERS" – Account has too many open orders on the symbol.
- "Filter failure: MAX_NUM_ALGO_ORDERS" – Account has too many open stop loss and/or take profit orders on the symbol.
- "Filter failure: MAX_NUM_ICEBERG_ORDERS" – Account has too many open iceberg orders on the symbol.
- "Filter failure: MAX_NUM_ORDER_AMENDS" – Account has made too many amendments to a single order on the symbol.
- "Filter failure: MAX_NUM_ORDER_LISTS" – Account has too many open order lists on the symbol.
- "Filter failure: TRAILING_DELTA" – `trailingDelta` is not within the defined range of the filter for that order type.
- "Filter failure: EXCHANGE_MAX_NUM_ORDERS" – Account has too many open orders on the exchange.
- "Filter failure: EXCHANGE_MAX_NUM_ALGO_ORDERS" – Account has too many open stop loss and/or take profit orders on the exchange.
- "Filter failure: EXCHANGE_MAX_NUM_ICEBERG_ORDERS" – Account has too many open iceberg orders on the exchange.
- "Filter failure: EXCHANGE_MAX_NUM_ORDER_LISTS" – Account has too many open order lists on the exchange.


