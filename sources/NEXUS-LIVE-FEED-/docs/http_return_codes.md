# HTTP Return Codes

- **HTTP 4XX** return codes are used for malformed requests; the issue is on the sender's side.
- **HTTP 403** return code is used when the Web Application Firewall (WAF) limit has been violated.
- **HTTP 409** return code is used when a cancel/replace order partially succeeds (e.g., the cancellation fails but the new order placement succeeds).
- **HTTP 429** return code is used when breaking a request rate limit.
- **HTTP 418** return code is used when an IP has been auto-banned for continuing to send requests after receiving 429 codes.
- **HTTP 5XX** return codes are used for internal errors; the issue is on Binance's side. It is important to **not** treat this as a failure operation; the execution status is **unknown** and could have been a success.
