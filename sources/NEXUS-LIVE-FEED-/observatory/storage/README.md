# Lake layout & governance

```
/lake
  /raw/{dataset}/{yyyy}/{mm}/{dd}/file.parquet
  /clean/{dataset}/{yyyy}/{mm}/{dd}/file.parquet
  /validated/{dataset}/{yyyy}/{mm}/{dd}/file.parquet
```

- Raw zone is append-only. Files are immutable and tracked with object versioning.
- Clean zone applies deduplication, time zone normalization (UTC), and corporate action adjustments.
- Validated marts assemble aligned feature frames ready for metric computation.

Lineage is captured through OpenMetadata/DataHub and backed by the schema registry for Kafka topics. Access is granted via least-privilege IAM roles; public downloads are generated from validated data only.
