from __future__ import annotations

from confluent_kafka import Producer

from shared.enums import ObservationType, SourceName
from shared.kafka.client import create_producer, produce_message
from shared.kafka.messages import ModeledAQDataMessage, WeatherDataMessage
from shared.settings import KafkaSettings

from services.weather_poller.models import ModeledAQReading, WeatherReading


class WeatherReadingPublisher:
    def __init__(self, settings: KafkaSettings, *, logger: object | None = None) -> None:
        self.settings = settings
        self.logger = logger
        self.producer: Producer = create_producer(settings)

    def publish_weather(self, readings: list[WeatherReading]) -> int:
        for reading in readings:
            message = build_weather_message(reading)
            produce_message(
                self.producer,
                topic=self.settings.topics.weather_data,
                key=message.message_key(),
                message=message,
                logger=self.logger,
            )
        return len(readings)

    def publish_modeled_aq(self, readings: list[ModeledAQReading]) -> int:
        for reading in readings:
            message = build_modeled_aq_message(reading)
            produce_message(
                self.producer,
                topic=self.settings.topics.modeled_aq_data,
                key=message.message_key(),
                message=message,
                logger=self.logger,
            )
        return len(readings)


def build_weather_message(reading: WeatherReading) -> WeatherDataMessage:
    return WeatherDataMessage(
        source=SourceName.OPENMETEO_WEATHER,
        observation_type=ObservationType.MODELED,
        location_id=reading.location_id,
        location_name=reading.location_name,
        latitude=reading.latitude,
        longitude=reading.longitude,
        temp=reading.temp,
        humidity=reading.humidity,
        wind_speed=reading.wind_speed,
        wind_dir=reading.wind_dir,
        precipitation=reading.precipitation,
        timestamp=reading.timestamp,
        quality_flag=reading.quality_flag,
    )


def build_modeled_aq_message(reading: ModeledAQReading) -> ModeledAQDataMessage:
    return ModeledAQDataMessage(
        source=SourceName.OPENMETEO_CAMS,
        observation_type=ObservationType.MODELED,
        coverage_mode=reading.coverage_mode,
        model_location_id=reading.model_location_id,
        location_name=reading.location_name,
        latitude=reading.latitude,
        longitude=reading.longitude,
        pollutant=reading.pollutant,
        value=reading.value,
        unit=reading.unit,
        us_aqi=reading.us_aqi,
        timestamp=reading.timestamp,
        model_run_at=reading.model_run_at,
        quality_flag=reading.quality_flag,
    )
