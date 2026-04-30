# Airflow Manual Triggers

These examples assume the batch profile is running and the core TimescaleDB schema has already been migrated.

```bash
docker compose --profile batch up -d airflow-postgres airflow-webserver airflow-scheduler
```

OpenAQ historical backfill, archive first with API fallback:

```bash
docker compose --profile batch exec airflow-scheduler airflow dags trigger openaq_historical_backfill \
  --conf '{"start_date":"2026-04-01","end_date":"2026-04-02","max_sensors":5}'
```

Weather historical backfill from Open-Meteo archive:

```bash
docker compose --profile batch exec airflow-scheduler airflow dags trigger weather_historical_backfill \
  --conf '{"start_date":"2026-03-01","end_date":"2026-03-31","max_locations":5}'
```

Data quality check:

```bash
docker compose --profile batch exec airflow-scheduler airflow dags trigger air_quality_data_quality_check \
  --conf '{"fresh_hours":2,"recent_hours":24,"dead_sensor_days":14}'
```

FIRMS daily load:

```bash
docker compose --profile batch exec airflow-scheduler airflow dags trigger firms_daily_load \
  --conf '{"date":"2026-04-29","source":"VIIRS_SNPP_NRT","bbox":"80.0,26.0,89.0,31.0","day_range":1}'
```

Forecast recompute scheduling hook:

```bash
docker compose --profile batch exec airflow-scheduler airflow dags trigger forecast_recompute_hook
```

`OPENAQ_API_KEY` and `FIRMS_MAP_KEY` must stay server-side in the Airflow environment. Missing keys are recorded visibly in `pipeline_runs` instead of falling back silently.
