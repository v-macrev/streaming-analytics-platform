from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


EventType = Literal[
    "page_view",
    "add_to_cart",
    "order_created",
    "payment_processed",
    "inventory_updated",
]


class ProducerSettings(BaseSettings):
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
    )
    kafka_topic_events: str = Field(
        default="events.raw",
        alias="KAFKA_TOPIC_EVENTS",
    )

    # ------------------------------------------------------------------
    # Producer Runtime
    # ------------------------------------------------------------------
    producer_source_name: str = Field(
        default="web-simulator",
        alias="PRODUCER_SOURCE_NAME",
    )
    producer_event_interval_ms: int = Field(
        default=500,
        alias="PRODUCER_EVENT_INTERVAL_MS",
        ge=1,
    )
    producer_batch_size: int = Field(
        default=1,
        alias="PRODUCER_BATCH_SIZE",
        ge=1,
        le=1000,
    )

    # ------------------------------------------------------------------
    # Identity / ID Generation
    # ------------------------------------------------------------------
    producer_user_id_min: int = Field(
        default=1000,
        alias="PRODUCER_USER_ID_MIN",
        ge=1,
    )
    producer_user_id_max: int = Field(
        default=9999,
        alias="PRODUCER_USER_ID_MAX",
        ge=1,
    )
    producer_session_id_prefix: str = Field(
        default="sess",
        alias="PRODUCER_SESSION_ID_PREFIX",
        min_length=1,
        max_length=32,
    )
    producer_order_id_prefix: str = Field(
        default="ord",
        alias="PRODUCER_ORDER_ID_PREFIX",
        min_length=1,
        max_length=32,
    )
    producer_payment_id_prefix: str = Field(
        default="pay",
        alias="PRODUCER_PAYMENT_ID_PREFIX",
        min_length=1,
        max_length=32,
    )

    # ------------------------------------------------------------------
    # Domain Generation
    # ------------------------------------------------------------------
    producer_inventory_warehouse_count: int = Field(
        default=3,
        alias="PRODUCER_INVENTORY_WAREHOUSE_COUNT",
        ge=1,
        le=1000,
    )
    producer_currency: str = Field(
        default="BRL",
        alias="PRODUCER_CURRENCY",
        min_length=3,
        max_length=3,
    )

    # ------------------------------------------------------------------
    # Event Weights
    # ------------------------------------------------------------------
    producer_weight_page_view: int = Field(
        default=45,
        alias="PRODUCER_WEIGHT_PAGE_VIEW",
        ge=0,
    )
    producer_weight_add_to_cart: int = Field(
        default=20,
        alias="PRODUCER_WEIGHT_ADD_TO_CART",
        ge=0,
    )
    producer_weight_order_created: int = Field(
        default=12,
        alias="PRODUCER_WEIGHT_ORDER_CREATED",
        ge=0,
    )
    producer_weight_payment_processed: int = Field(
        default=13,
        alias="PRODUCER_WEIGHT_PAYMENT_PROCESSED",
        ge=0,
    )
    producer_weight_inventory_updated: int = Field(
        default=10,
        alias="PRODUCER_WEIGHT_INVENTORY_UPDATED",
        ge=0,
    )

    @model_validator(mode="after")
    def validate_ranges(self) -> "ProducerSettings":
        if self.producer_user_id_min > self.producer_user_id_max:
            raise ValueError(
                "PRODUCER_USER_ID_MIN cannot be greater than PRODUCER_USER_ID_MAX."
            )

        if self.event_weight_total <= 0:
            raise ValueError(
                "At least one producer event weight must be greater than zero."
            )

        return self

    @property
    def event_interval_seconds(self) -> float:
        return self.producer_event_interval_ms / 1000.0

    @property
    def event_weights(self) -> dict[EventType, int]:
        return {
            "page_view": self.producer_weight_page_view,
            "add_to_cart": self.producer_weight_add_to_cart,
            "order_created": self.producer_weight_order_created,
            "payment_processed": self.producer_weight_payment_processed,
            "inventory_updated": self.producer_weight_inventory_updated,
        }

    @property
    def enabled_event_types(self) -> tuple[EventType, ...]:
        return tuple(
            event_type
            for event_type, weight in self.event_weights.items()
            if weight > 0
        )

    @property
    def event_weight_total(self) -> int:
        return sum(self.event_weights.values())


@lru_cache(maxsize=1)
def get_settings() -> ProducerSettings:
    return ProducerSettings()