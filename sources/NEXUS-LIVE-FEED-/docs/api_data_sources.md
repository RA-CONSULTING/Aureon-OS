# API Data Sources and Latency

The Nexus API system responds asynchronously. A short delay between a request and its response is normal because the platform aggregates information from several storage layers.

| Data Source       | Latency  | Description                                       |
|-------------------|----------|---------------------------------------------------|
| Matching Engine   | lowest   | The Matching Engine produces the response directly. |
| Memory            | low      | Data is fetched from the API server's local or external memory cache. |
| Database          | moderate | Data is retrieved from the database.              |

Some API methods query multiple data sources sequentially—such as `Memory => Database`. In those cases the service first checks the cache for the freshest values before falling back to the database if necessary. This cascading lookup pattern maximizes performance while ensuring the most up-to-date data is returned.
