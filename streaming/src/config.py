from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StreamingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="streaming-analytics-platform", alias="APP_NAME")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    app_timezone: str = Field(default="UTC", alias="APP_TIMEZONE")

    # ------------------------------------------------------------------
    # Kafka
    # ------------------------------------------------------------------
    kafka_bootstrap_servers: str = Field(
        default="localhost:9094",
        alias="KAFKA_BOOTSTRAP_SERVERS",
        min_length=1,
    )
    kafka_topic_events: str = Field(
        default="events.raw",
        alias="KAFKA_TOPIC_EVENTS",
        min_length=1,
    )
    kafka_consumer_group: str = Field(
        default="streaming-analytics-consumer",
        alias="KAFKA_CONSUMER_GROUP",
        min_length=1,
    )
    kafka_auto_offset_reset: str = Field(
        default="latest",
        alias="KAFKA_AUTO_OFFSET_RESET",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Spark
    # ------------------------------------------------------------------
    spark_app_name: str = Field(
        default="streaming-analytics-job",
        alias="SPARK_APP_NAME",
        min_length=1,
    )
    spark_master_url: str = Field(
        default="spark://spark-master:7077",
        alias="SPARK_MASTER_URL",
        min_length=1,
    )
    spark_checkpoint_dir: str = Field(
        default="/tmp/spark-checkpoints",
        alias="SPARK_CHECKPOINT_DIR",
        min_length=1,
    )
    spark_trigger_interval: str = Field(
        default="10 seconds",
        alias="SPARK_TRIGGER_INTERVAL",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # Stream semantics
    # ------------------------------------------------------------------
    stream_watermark_delay: str = Field(
        default="2 minutes",
        alias="STREAM_WATERMARK_DELAY",
        min_length=1,
    )
    stream_window_duration: str = Field(
        default="1 minute",
        alias="STREAM_WINDOW_DURATION",
        min_length=1,
    )
    stream_slide_duration: str = Field(
        default="1 minute",
        alias="STREAM_SLIDE_DURATION",
        min_length=1,
    )

    # ------------------------------------------------------------------
    # ClickHouse
    # ------------------------------------------------------------------
    clickhouse_host: str = Field(
        default="localhost",
        alias="CLICKHOUSE_HOST",
        min_length=1,
    )
    clickhouse_port: int = Field(
        default=8123,
        alias="CLICKHOUSE_PORT",
        ge=1,
        le=65535,
    )
    clickhouse_database: str = Field(
        default="analytics",
        alias="CLICKHOUSE_DATABASE",
        min_length=1,
    )
    clickhouse_user: str = Field(
        default="analytics_user",
        alias="CLICKHOUSE_USER",
        min_length=1,
    )
    clickhouse_password: str = Field(
        default="analytics_pass",
        alias="CLICKHOUSE_PASSWORD",
        min_length=1,
    )
    clickhouse_metrics_table: str = Field(
        default="metrics_realtime_1m",
        alias="CLICKHOUSE_METRICS_TABLE",
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "StreamingSettings":
        allowed_offset_values = {"earliest", "latest"}
        if self.kafka_auto_offset_reset not in allowed_offset_values:
            raise ValueError(
                "KAFKA_AUTO_OFFSET_RESET must be either 'earliest' or 'latest'."
            )

        return self

    @property
    def clickhouse_http_url(self) -> str:
        return (
            f"http://{self.clickhouse_host}:{self.clickhouse_port}"
        )

    @property
    def spark_kafka_starting_offsets(self) -> str:
        return self.kafka_auto_offset_reset

    @property
    def spark_query_name(self) -> str:
        return f"{self.spark_app_name}-query"

    @property
    def spark_checkpoint_metrics_dir(self) -> str:
        base = self.spark_checkpoint_dir.rstrip("/")
        return f"{base}/metrics_realtime_1m"


@lru_cache(maxsize=1)
def get_settings() -> StreamingSettings:
    return StreamingSettings()