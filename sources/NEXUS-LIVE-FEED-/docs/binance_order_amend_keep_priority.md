# Order Amend Keep Priority

## Overview
Order Amend Keep Priority requests allow traders to reduce the quantity of an existing order without sacrificing its position in the order book. The amendment is applied in-place, so the order keeps its original identifier and time priority.

## Supported Actions
- Reduce the quantity of an existing order while retaining order book priority.

## API Endpoints
| Interface | Request |
|-----------|---------|
| REST API  | `PUT /api/v3/order/amend/keepPriority` |
| WebSocket | `order.amend.keepPriority` |
| FIX       | `OrderAmendKeepPriorityRequest <XAK>` |

## Cancel-Replace vs. Order Amend Keep Priority
- **Cancel-Replace**: Cancels the original order and submits a new order. The new order receives a new order ID and loses time priority.
- **Order Amend Keep Priority**: Modifies the existing order in-place, keeps the order ID, and preserves time priority.

### Example
Initial order book:

| User | Order ID | Side | Price | Quantity |
|------|----------|------|-------|----------|
| User A | 10 | BUY | 87,000 | 1.00 |
| You | 15 | BUY | 87,000 | 5.50 |
| User B | 20 | BUY | 87,000 | 4.00 |
| User C | 21 | BUY | 86,999 | 2.00 |

If order 15 is canceled and re-submitted (cancel-replace) with quantity 5.00, the book becomes:

| User | Order ID | Side | Price | Quantity |
|------|----------|------|-------|----------|
| User A | 10 | BUY | 87,000 | 1.00 |
| You | 11 | BUY | 87,000 | 5.50 |
| User B | 20 | BUY | 87,000 | 4.00 |
| You (new) | 22 | BUY | 87,000 | 5.00 |
| User C | 21 | BUY | 86,999 | 2.00 |

If order 15 is amended with Order Amend Keep Priority to quantity 5.00, the book becomes:

| User | Order ID | Side | Price | Quantity |
|------|----------|------|-------|----------|
| User A | 10 | BUY | 87,000 | 1.00 |
| You | 15 | BUY | 87,000 | 5.00 |
| User B | 20 | BUY | 87,000 | 4.00 |
| User C | 21 | BUY | 86,999 | 2.00 |

## Rate Limits and Notifications
- Order Amend Keep Priority requests currently count as zero toward the unfilled order rate limit.
- Successful amendments include the updated order information in the API response.
- On the User Data Stream, successful amendments emit an `executionReport` event with execution type `x` (`REPLACED`).
- If the order belongs to an order list and the client order ID changes, a `listStatus` event with status type `l` (`UPDATED`) is also emitted.

## Error Handling
If an amendment fails due to filters, permissions, or other restrictions, the request is rejected and the original order remains unchanged.

## Client Order IDs
Amended orders receive a new random client order ID by default. To keep the existing client order ID, pass it explicitly in the `newClientOrderId` parameter.

## Special Cases
- **Iceberg Orders**: Iceberg orders can be amended. The visible portion only changes when `newQty` is below the previous visible quantity.
- **Order Lists**: Orders within an order list can be amended. For OCO pairs, both orders must maintain the same quantity. For OTO orders, the working and pending orders can be amended independently.

## Symbol Support
Check Exchange Information: symbols that allow Order Amend Keep Priority have `amendAllowed` set to `true`.
