from __future__ import annotations

import pytest
from pydantic import ValidationError

from config import ProducerSettings


def test_settings_load_with_defaults() -> None:
    settings = ProducerSettings()

    assert settings.app_env == "local"
    assert settings.app_name == "streaming-analytics-platform"
    assert settings.app_log_level == "INFO"
    assert settings.kafka_bootstrap_servers == "localhost:9094"
    assert settings.kafka_topic_events == "events.raw"
    assert settings.producer_source_name == "web-simulator"
    assert settings.producer_event_interval_ms == 500
    assert settings.producer_batch_size == 1
    assert settings.producer_currency == "BRL"


def test_event_interval_seconds_is_derived_correctly() -> None:
    settings = ProducerSettings(PRODUCER_EVENT_INTERVAL_MS=250)

    assert settings.producer_event_interval_ms == 250
    assert settings.event_interval_seconds == 0.25


def test_event_weights_are_exposed_correctly() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=50,
        PRODUCER_WEIGHT_ADD_TO_CART=20,
        PRODUCER_WEIGHT_ORDER_CREATED=10,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=15,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=5,
    )

    assert settings.event_weights == {
        "page_view": 50,
        "add_to_cart": 20,
        "order_created": 10,
        "payment_processed": 15,
        "inventory_updated": 5,
    }
    assert settings.event_weight_total == 100


def test_enabled_event_types_only_include_positive_weights() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=10,
        PRODUCER_WEIGHT_ADD_TO_CART=0,
        PRODUCER_WEIGHT_ORDER_CREATED=0,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=5,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=0,
    )

    assert settings.enabled_event_types == (
        "page_view",
        "payment_processed",
    )


def test_user_id_range_validation_rejects_inverted_bounds() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProducerSettings(
            PRODUCER_USER_ID_MIN=9999,
            PRODUCER_USER_ID_MAX=1000,
        )

    assert "PRODUCER_USER_ID_MIN cannot be greater than PRODUCER_USER_ID_MAX" in str(
        exc_info.value
    )


def test_settings_reject_when_all_event_weights_are_zero() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProducerSettings(
            PRODUCER_WEIGHT_PAGE_VIEW=0,
            PRODUCER_WEIGHT_ADD_TO_CART=0,
            PRODUCER_WEIGHT_ORDER_CREATED=0,
            PRODUCER_WEIGHT_PAYMENT_PROCESSED=0,
            PRODUCER_WEIGHT_INVENTORY_UPDATED=0,
        )

    assert "At least one producer event weight must be greater than zero" in str(
        exc_info.value
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("PRODUCER_EVENT_INTERVAL_MS", 0),
        ("PRODUCER_BATCH_SIZE", 0),
        ("PRODUCER_USER_ID_MIN", 0),
        ("PRODUCER_INVENTORY_WAREHOUSE_COUNT", 0),
    ],
)
def test_numeric_constraints_reject_invalid_values(
    field_name: str,
    value: int,
) -> None:
    kwargs = {field_name: value}

    with pytest.raises(ValidationError):
        ProducerSettings(**kwargs)


def test_custom_runtime_values_are_applied() -> None:
    settings = ProducerSettings(
        APP_ENV="docker",
        APP_NAME="sap-producer",
        APP_LOG_LEVEL="DEBUG",
        KAFKA_BOOTSTRAP_SERVERS="kafka:9092",
        KAFKA_TOPIC_EVENTS="events.raw",
        PRODUCER_SOURCE_NAME="test-simulator",
        PRODUCER_BATCH_SIZE=10,
        PRODUCER_CURRENCY="USD",
        PRODUCER_SESSION_ID_PREFIX="session",
        PRODUCER_ORDER_ID_PREFIX="order",
        PRODUCER_PAYMENT_ID_PREFIX="payment",
    )

    assert settings.app_env == "docker"
    assert settings.app_name == "sap-producer"
    assert settings.app_log_level == "DEBUG"
    assert settings.kafka_bootstrap_servers == "kafka:9092"
    assert settings.kafka_topic_events == "events.raw"
    assert settings.producer_source_name == "test-simulator"
    assert settings.producer_batch_size == 10
    assert settings.producer_currency == "USD"
    assert settings.producer_session_id_prefix == "session"
    assert settings.producer_order_id_prefix == "order"
    assert settings.producer_payment_id_prefix == "payment"