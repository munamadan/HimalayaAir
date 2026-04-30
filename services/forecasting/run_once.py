from __future__ import annotations

import argparse
from datetime import datetime
from time import monotonic

from services.common.aqi_calculator import normalize_pollutant
from services.forecasting.config import ForecastSettings
from services.forecasting.modeled_bias import build_modeled_bias_forecast
from services.forecasting.model_selection import choose_forecast_model
from services.forecasting.models import ForecastModel, ForecastResult, ForecastRunResult, ModelSelection
from services.forecasting.persistence import build_persistence_forecast
from services.forecasting.repository import ForecastRepository, ForecastRepositoryError
from services.forecasting.sarimax import SarimaxForecastError, build_sarimax_forecast
from shared.logging_config import configure_logging, get_logger
from shared.time_utils import ensure_utc, parse_utc, utc_now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one HimalayaAir forecast recomputation.")
    parser.add_argument("--dry-run", action="store_true", help="Build forecasts without writing forecast tables.")
    parser.add_argument("--station-id", type=int, help="Limit the run to one station id.")
    parser.add_argument("--pollutant", action="append", help="Limit to one pollutant. Can be supplied more than once.")
    parser.add_argument("--generated-at", help="Override generation timestamp as ISO-8601 UTC.")
    return parser.parse_args()


def run_forecast_once(
    *,
    settings: ForecastSettings | None = None,
    dry_run: bool = False,
    station_id: int | None = None,
    pollutants: tuple[str, ...] | None = None,
    generated_at: datetime | None = None,
) -> ForecastRunResult:
    resolved_settings = settings or ForecastSettings.from_env()
    configure_logging(service_name=resolved_settings.service_name, log_format=resolved_settings.log_format)
    logger = get_logger(__name__)
    repository = ForecastRepository(resolved_settings)
    started = monotonic()
    run_at = _floor_hour(generated_at or utc_now())
    selected_pollutants = tuple(normalize_pollutant(pollutant) for pollutant in (pollutants or resolved_settings.pollutants))
    station_ids = [station_id] if station_id is not None else repository.fetch_active_station_ids()
    results: list[ForecastResult] = []
    errors: list[str] = []

    if not station_ids:
        result = ForecastRunResult(
            status="failed",
            forecast_run_id=None,
            stations_attempted=0,
            stations_succeeded=0,
            forecasts_written=0,
            accuracy_records_written=0,
            fallback_reason=None,
            error_message="no active stations are available for forecasting",
        )
        _record_pipeline(repository, resolved_settings, result, run_at, monotonic() - started, dry_run=dry_run)
        return result

    for current_station_id in station_ids:
        station_success = False
        for pollutant in selected_pollutants:
            try:
                context = repository.build_context(station_id=current_station_id, pollutant=pollutant, generated_at=run_at)
                selection = choose_forecast_model(context, resolved_settings)
                forecast = _build_forecast(context, resolved_settings, selection)
                results.append(forecast)
                station_success = True
                logger.info(
                    "forecast_model_selected",
                    station_id=current_station_id,
                    pollutant=pollutant,
                    model=forecast.model_name,
                    model_source=forecast.model_source,
                    fallback_reason=forecast.fallback_reason,
                )
            except Exception as exc:
                message = f"station={current_station_id} pollutant={pollutant}: {exc}"
                errors.append(message)
                logger.warning("forecast_station_failed", station_id=current_station_id, pollutant=pollutant, error=str(exc))
        if not station_success:
            logger.warning("forecast_station_all_pollutants_failed", station_id=current_station_id)

    succeeded_station_ids = {result.station_id for result in results}
    status = "success" if len(succeeded_station_ids) == len(station_ids) and not errors else "partial" if results else "failed"
    duration_seconds = monotonic() - started
    fallback_reason = _run_fallback_reason(results)
    forecast_run_id: int | None = None
    forecasts_written = 0
    accuracy_written = 0

    if not dry_run and results:
        forecast_run_id, forecasts_written = repository.write_forecast_run(
            generated_at=run_at,
            model_name=_run_model_name(results),
            status=status,
            stations_attempted=len(station_ids),
            stations_succeeded=len(succeeded_station_ids),
            fallback_reason=fallback_reason,
            duration_seconds=duration_seconds,
            results=results,
        )
        accuracy_written = repository.compute_elapsed_accuracy(now=run_at)

    result = ForecastRunResult(
        status=status,
        forecast_run_id=forecast_run_id,
        stations_attempted=len(station_ids),
        stations_succeeded=len(succeeded_station_ids),
        forecasts_written=forecasts_written,
        accuracy_records_written=accuracy_written,
        fallback_reason=fallback_reason,
        error_message="; ".join(errors) if errors else None,
    )
    _record_pipeline(repository, resolved_settings, result, run_at, duration_seconds, dry_run=dry_run)
    logger.info(
        "forecast_run_complete",
        status=result.status,
        dry_run=dry_run,
        forecast_run_id=result.forecast_run_id,
        stations_attempted=result.stations_attempted,
        stations_succeeded=result.stations_succeeded,
        forecasts_written=result.forecasts_written,
        accuracy_records_written=result.accuracy_records_written,
    )
    return result


def _build_forecast(context, settings: ForecastSettings, selection: ModelSelection) -> ForecastResult:
    if selection.model == ForecastModel.SARIMAX:
        try:
            return build_sarimax_forecast(context, settings, selection)
        except SarimaxForecastError as exc:
            selection = _selection_after_sarimax_failure(context, settings, str(exc))
    if selection.model == ForecastModel.MODELED_BIAS:
        return build_modeled_bias_forecast(context, settings, selection)
    return build_persistence_forecast(context, settings, selection)


def _selection_after_sarimax_failure(context, settings: ForecastSettings, error_message: str) -> ModelSelection:
    reason = f"SARIMAX was selected but failed visibly: {error_message}"
    if len(context.modeled_future) >= settings.horizon_hours:
        return ModelSelection(
            model=ForecastModel.MODELED_BIAS,
            model_source="modeled_aq_with_observed_bias" if context.modeled_history and context.observed_history else "modeled_aq_unadjusted",
            fallback_reason=reason,
            sarimax_rejection_reasons=(reason,),
        )
    return ModelSelection(
        model=ForecastModel.PERSISTENCE,
        model_source=f"persistence_{context.persistence_baseline.source}",
        fallback_reason=f"{reason}; Modeled AQ forecast has {len(context.modeled_future)} of {settings.horizon_hours} required future hour(s).",
        sarimax_rejection_reasons=(reason,),
    )


def _record_pipeline(
    repository: ForecastRepository,
    settings: ForecastSettings,
    result: ForecastRunResult,
    run_at: datetime,
    duration_seconds: float,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        return
    try:
        repository.record_pipeline_run(
            component=settings.pipeline_component,
            run_at=run_at,
            status=result.status,
            records_processed=result.forecasts_written,
            duration_seconds=duration_seconds,
            error_message=result.error_message,
            metadata={
                "forecast_run_id": result.forecast_run_id,
                "stations_attempted": result.stations_attempted,
                "stations_succeeded": result.stations_succeeded,
                "accuracy_records_written": result.accuracy_records_written,
                "fallback_reason": result.fallback_reason,
            },
        )
    except ForecastRepositoryError as exc:
        logger = get_logger(__name__)
        logger.warning("forecast_pipeline_run_record_failed", error=str(exc))


def _run_model_name(results: list[ForecastResult]) -> str:
    names = {result.model_name for result in results}
    return next(iter(names)) if len(names) == 1 else "mixed"


def _run_fallback_reason(results: list[ForecastResult]) -> str | None:
    reasons = sorted({result.fallback_reason for result in results if result.fallback_reason})
    return "; ".join(reasons) if reasons else None


def _floor_hour(value: datetime) -> datetime:
    return ensure_utc(value).replace(minute=0, second=0, microsecond=0)


def main() -> int:
    args = parse_args()
    generated_at = parse_utc(args.generated_at) if args.generated_at else None
    result = run_forecast_once(
        dry_run=bool(args.dry_run),
        station_id=args.station_id,
        pollutants=tuple(args.pollutant) if args.pollutant else None,
        generated_at=generated_at,
    )
    return 0 if result.status in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

