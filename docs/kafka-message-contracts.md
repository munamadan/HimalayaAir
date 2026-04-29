# Kafka Message Contracts

Phase 04 defines the shared Kafka topic names, keys, and message schemas used by later services.

## Topics

| Topic | Key format | Producer | Consumer |
|---|---|---|---|
| `raw-aq-readings` | `station_id:sensor_id:pollutant:timestamp` | OpenAQ poller or replay publisher | Spark stream processor |
| `weather-data` | `location_id:timestamp` | weather poller | Spark stream processor and forecast jobs |
| `modeled-aq-data` | `model_location_id:pollutant:timestamp:model_run_at` | Open-Meteo AQ poller | Spark stream processor and fallback consumers |
| `processed-aq-readings` | `batch_id` | Spark stream processor | API/WebSocket layer |
| `raw-aq-readings-dlq` | `original_topic:original_key:failed_at` | producers or processors after visible failure handling | operators and later quality checks |
| `pipeline-events` | `component:event_type:created_at` | services reporting pipeline status | operations consumers |

## Required Provenance

Every Kafka message schema includes:

- `schema_version`
- `source`
- `observation_type`

Air-quality messages also carry `coverage_mode` and `confidence` where the downstream user experience needs provenance. Open-Meteo AQ must use `source=openmeteo_cams`, `observation_type=modeled`, and `coverage_mode=MODELED_BASELINE`. Replay fixture messages must use `source=demo_replay`, `observation_type=replay`, and `coverage_mode=REPLAY_DEMO`.

`processed-aq-readings` carries a batch summary for WebSocket notifications. The summary is not the source of truth; it contains per-station `source` and `observation_type` fields, while TimescaleDB remains authoritative for full AQ records.

## Shared Models

The Python contracts live in `shared.kafka.messages`:

- `RawAQReadingMessage`
- `WeatherDataMessage`
- `ModeledAQDataMessage`
- `ProcessedAQReadingMessage`
- `ProcessedAQBatchSummaryMessage`
- `DLQMessage`

Use `message_key()` on each model to build the Kafka key, and use `message_to_json()` or `to_json_bytes()` for serialization.
