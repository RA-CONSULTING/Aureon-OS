# Simple Binary Encoding (SBE) FAQ

This FAQ explains how to request SBE responses from the Binance SPOT REST and WebSocket APIs, how to decode those responses, and how schema versioning works for SBE payloads. The implementation is based on the FIX SBE specification.

## Getting SBE Responses

### REST API

To receive SBE payloads from the REST API:

1. Set the `Accept` header to include `application/sbe`.
2. Provide the schema identifier and version in the `X-MBX-SBE` header as `<ID>:<VERSION>`.

```bash
curl -sX GET \
  -H "Accept: application/sbe" \
  -H "X-MBX-SBE: 1:0" \
  'https://api.binance.com/api/v3/exchangeInfo?symbol=BTCUSDT'
```

#### REST Notes

- If the `Accept` header only includes `application/sbe`:
  - If SBE is not enabled, the server returns **HTTP 406 Not Acceptable**.
  - If `X-MBX-SBE` is malformed, invalid, or missing, the response is an SBE-encoded error.
- If the `Accept` header includes both `application/sbe` and `application/json`:
  - If SBE is not enabled, the response falls back to JSON.
  - If `X-MBX-SBE` is malformed, invalid, or missing, the response falls back to JSON.

### WebSocket API

To enable SBE payloads on the WebSocket API:

1. Add `responseFormat=sbe` to the connection URL.
2. Include `sbeSchemaId=<SCHEMA_ID>` and `sbeSchemaVersion=<SCHEMA_VERSION>` query parameters.

Sample WebSocket request:

```bash
id=$(date +%s%3N)
method="exchangeInfo"
params='{"symbol":"BTCUSDT"}'

request=$( jq -n \
        --arg id "$id" \
        --arg method "$method" \
        --argjson params "$params" \
        '{id: $id, method: $method, params: $params}' )

response=$(echo $request | websocat -n1 'wss://ws-api.binance.com:443/ws-api/v3?responseFormat=sbe&sbeSchemaId=1&sbeSchemaVersion=0')
```

#### WebSocket Notes

- Specifying only `responseFormat=sbe`:
  - If SBE is not enabled, the handshake returns **HTTP 400**.
  - If `sbeSchemaId` or `sbeSchemaVersion` are malformed or invalid, the handshake returns **HTTP 400**.
- Specifying both `responseFormat=sbe` and `responseFormat=json` results in **HTTP 400**.
- Handshake errors are returned as JSON with `Content-Type: application/json;charset=UTF-8`.
- After an SBE-enabled session is established, all subsequent responses remain SBE-encoded even if SBE is later disabled. In that case, requests receive an SBE-encoded “SBE is not enabled” error.
- `websocat` is not recommended due to issues decoding binary frames; the example above is illustrative only.

## Supported APIs

- SPOT REST API
- SPOT WebSocket API

## SBE Schemas

- Production schema: `spot_prod_latest.xml`
- Testnet schema: `spot_testnet_latest.xml`
- Schema files, changelog updates, and lifecycle JSON records are maintained in this repository.

### Schema Lifecycle

SBE schemas use two XML attributes:

- `id`: Incremented for breaking changes (resets `version` to 0).
- `version`: Incremented for non-breaking changes (does not change `id`).

Lifecycle rules:

- When a new schema (even non-breaking) is released, previous schemas become **deprecated**.
- Deprecated schemas are supported for **at least 6 months**.
- Requests using deprecated schemas:
  - REST: responses include `X-MBX-SBE-DEPRECATED` header and are encoded in the highest compatible schema.
  - WebSocket: responses set `sbeSchemaIdVersionDeprecated=true` and encode data in the highest compatible schema.
- Requests using **retired** schemas result in **HTTP 400**.

#### Example Timeline

| Date           | Event                                                                 |
|----------------|-----------------------------------------------------------------------|
| Jan 3024       | Schema `1:0` released (initial version).                              |
| Mar 3024       | Schema `1:1` released (non-breaking). Schema `1:0` deprecated.         |
| Aug 3024       | Schema `2:0` released (breaking). Schema `1:0` deprecated for 1 month; Schema `1:1` deprecated for 6 months. |
| Sep 3024       | Schema `1:0` retired (after 6 months from release).                   |
| Feb 3025       | Schema `2:1` released (non-breaking). Schema `1:1` retired; Schema `2:0` deprecated. |

#### NonRepresentable Values

- Schema `3:0`: Each enum includes a `NonRepresentable` valid value to signal additional data in newer schemas.
- Schema `3:1`: Adds `NonRepresentableMessage` to indicate additional data is available when using the latest schema. This message can appear as a top-level message or within fields of type `messageData`, `messageData8`, `messageData16`, `optionalMessageData`, or `optionalMessageData16`.

### Schema Lifecycle JSON Example

```json
{
  "environment": "PROD",
  "latestSchema": {
      "id": 2,
      "version": 1,
      "releaseDate": "3025-02-01"
  },
  "deprecatedSchemas": [
      {
          "id": 2,
          "version": 0,
          "releaseDate": "3024-08-01",
          "deprecatedDate": "3025-02-01"
      }
  ],
  "retiredSchemas": [
      {
          "id": 1,
          "version": 1,
          "releaseDate": "3024-03-01",
          "deprecatedDate": "3024-08-01",
          "retiredDate": "3025-02-01"
      },
      {
          "id": 1,
          "version": 0,
          "releaseDate": "3024-01-01",
          "deprecatedDate": "3024-03-01",
          "retiredDate": "3024-09-01"
      }
  ]
}
```

## Generating SBE Decoders

1. Download the appropriate schema file (`spot_prod_latest.xml` or `spot_testnet_latest.xml`).
2. Clone and build the [Simple Binary Encoding](https://github.com/real-logic/simple-binary-encoding) project:

   ```bash
   git clone https://github.com/real-logic/simple-binary-encoding.git
   cd simple-binary-encoding
   ./gradlew
   ```

3. Run the `SbeTool` code generator. Samples for Java, C++, and Rust decoding `exchangeInfo` payloads are available in the repository.

### Field Encodings

- **Decimal fields:** Mantissa and exponent are encoded separately as primitive fields to minimize payload size.
- **Timestamp fields:** Encoded in **microseconds**, unlike JSON responses which default to milliseconds.

### Custom Schema Attributes

The schema includes Binance-specific attributes prefixed with `mbx:` for documentation:

- `mbx:exponent`: references the exponent field corresponding to a mantissa field.
- `mbx:jsonPath`: names the equivalent field in the JSON response.
- `mbx:jsonValue`: names the equivalent ENUM value in the JSON response.

## Additional Resources

- [Simple Binary Encoding GitHub Repository](https://github.com/real-logic/simple-binary-encoding)
- HTML documentation and schema files are provided in this repository under `docs/`.

