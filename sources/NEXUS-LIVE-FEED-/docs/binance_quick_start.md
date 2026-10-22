# Binance API Quick Start

## API Key Setup
Some endpoints require an API key. Please review the [API key creation guide](https://www.binance.com/en/support/faq/360002502072) before enabling programmatic access. Once the key is created, configure IP restrictions to limit where the key can be used for improved security.

> **Important:** Never share your API key or secret key with anyone. If the key is ever exposed, delete it immediately and generate a new one.

### API Key Restrictions
- Newly created keys have **Enable Reading** permissions by default.
- To allow withdrawals via the API, adjust the key restrictions through the Binance user interface.

## Enabling Accounts
- **Spot Account** – A Spot account is provisioned automatically when a Binance account is created.
- **Margin Account** – Enable a Margin account for Margin Trading by following the [Margin Trading Guide](https://www.binance.com/en/support/faq/360000671322).

## API Libraries
Lightweight client libraries are available for multiple languages to help you connect to the Binance public API:

- [Python connector](https://github.com/binance/binance-connector-python)
- [JavaScript connector](https://github.com/binance/binance-connector-js)
- [Ruby connector](https://github.com/binance/binance-connector-ruby)
- [.NET connector](https://github.com/binance/binance-connector-dotnet)
- [Java connector](https://github.com/binance/binance-connector-java)

## Postman Collections
A Postman collection with pre-built endpoints is available for rapid testing, making it ideal for new users. Learn more here: [Binance API Postman](https://github.com/binance/binance-api-postman).

## Swagger
A YAML file with OpenAPI specifications for the REST API, along with a Swagger UI, can be accessed from the official repository: [binance-api-swagger](https://github.com/binance/binance-api-swagger).
