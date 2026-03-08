from __future__ import annotations

from collections import Counter

from config import ProducerSettings
from generator import EventGenerator
from models import (
    AddToCartPayload,
    InventoryUpdatedPayload,
    OrderCreatedPayload,
    PageViewPayload,
    PaymentProcessedPayload,
)


def test_generator_produces_valid_events_with_supported_types() -> None:
    settings = ProducerSettings()
    generator = EventGenerator(settings)

    events = [generator.next_event() for _ in range(100)]

    assert len(events) == 100

    for event in events:
        assert event.event_type in {
            "page_view",
            "add_to_cart",
            "order_created",
            "payment_processed",
            "inventory_updated",
        }
        assert event.event_id
        assert event.user_id
        assert event.session_id
        assert event.source == settings.producer_source_name
        assert event.event_time.tzinfo is not None
        assert event.producer_time.tzinfo is not None


def test_generator_respects_single_enabled_event_type() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=0,
        PRODUCER_WEIGHT_ADD_TO_CART=0,
        PRODUCER_WEIGHT_ORDER_CREATED=0,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=0,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=1,
    )
    generator = EventGenerator(settings)

    events = [generator.next_event() for _ in range(25)]

    assert all(event.event_type == "inventory_updated" for event in events)


def test_page_view_events_have_expected_payload_shape() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=1,
        PRODUCER_WEIGHT_ADD_TO_CART=0,
        PRODUCER_WEIGHT_ORDER_CREATED=0,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=0,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=0,
    )
    generator = EventGenerator(settings)

    event = generator.next_event()

    assert event.event_type == "page_view"
    assert isinstance(event.payload, PageViewPayload)
    assert event.payload.page.startswith("/")
    assert event.payload.product_id.startswith("prd_")
    assert event.payload.category
    assert event.payload.referrer


def test_add_to_cart_events_have_expected_payload_shape() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=0,
        PRODUCER_WEIGHT_ADD_TO_CART=1,
        PRODUCER_WEIGHT_ORDER_CREATED=0,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=0,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=0,
    )
    generator = EventGenerator(settings)

    event = generator.next_event()

    assert event.event_type == "add_to_cart"
    assert isinstance(event.payload, AddToCartPayload)
    assert event.payload.product_id.startswith("prd_")
    assert 1 <= event.payload.quantity <= 4
    assert event.payload.unit_price > 0
    assert event.payload.currency == settings.producer_currency


def test_order_created_events_are_added_to_recent_order_state() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=0,
        PRODUCER_WEIGHT_ADD_TO_CART=0,
        PRODUCER_WEIGHT_ORDER_CREATED=1,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=0,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=0,
    )
    generator = EventGenerator(settings)

    initial_recent_orders = len(generator._recent_orders)
    event = generator.next_event()

    assert event.event_type == "order_created"
    assert isinstance(event.payload, OrderCreatedPayload)
    assert len(generator._recent_orders) == initial_recent_orders + 1

    recent_order = generator._recent_orders[-1]
    assert recent_order.order_id == event.payload.order_id
    assert recent_order.user_id == event.user_id
    assert recent_order.amount == event.payload.total_amount
    assert recent_order.currency == event.payload.currency


def test_payment_processed_events_reference_recent_orders_when_available() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=0,
        PRODUCER_WEIGHT_ADD_TO_CART=0,
        PRODUCER_WEIGHT_ORDER_CREATED=0,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=1,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=0,
    )
    generator = EventGenerator(settings)

    generator._recent_orders = [
        generator._pick_or_create_order_for_payment(),
        generator._pick_or_create_order_for_payment(),
    ]

    known_order_ids = {order.order_id for order in generator._recent_orders}

    matched_recent_order = False
    for _ in range(50):
        event = generator.next_event()
        assert event.event_type == "payment_processed"
        assert isinstance(event.payload, PaymentProcessedPayload)

        if event.payload.order_id in known_order_ids:
            matched_recent_order = True
            break

    assert matched_recent_order is True


def test_inventory_updates_keep_stock_non_negative() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=0,
        PRODUCER_WEIGHT_ADD_TO_CART=0,
        PRODUCER_WEIGHT_ORDER_CREATED=0,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=0,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=1,
    )
    generator = EventGenerator(settings)

    for _ in range(100):
        event = generator.next_event()

        assert event.event_type == "inventory_updated"
        assert isinstance(event.payload, InventoryUpdatedPayload)
        assert event.payload.stock_after >= 0
        assert event.payload.warehouse_id.startswith("wh_")


def test_inventory_updates_mutate_internal_stock_state() -> None:
    settings = ProducerSettings(
        PRODUCER_WEIGHT_PAGE_VIEW=0,
        PRODUCER_WEIGHT_ADD_TO_CART=0,
        PRODUCER_WEIGHT_ORDER_CREATED=0,
        PRODUCER_WEIGHT_PAYMENT_PROCESSED=0,
        PRODUCER_WEIGHT_INVENTORY_UPDATED=1,
    )
    generator = EventGenerator(settings)

    event = generator.next_event()

    assert event.event_type == "inventory_updated"
    assert isinstance(event.payload, InventoryUpdatedPayload)
    assert (
        generator._stock_by_product[event.payload.product_id]
        == event.payload.stock_after
    )


def test_generated_events_use_configured_source_name_and_currency() -> None:
    settings = ProducerSettings(
        PRODUCER_SOURCE_NAME="synthetic-lab",
        PRODUCER_CURRENCY="USD",
    )
    generator = EventGenerator(settings)

    events = [generator.next_event() for _ in range(200)]

    assert all(event.source == "synthetic-lab" for event in events)

    monetary_payloads = [
        event.payload
        for event in events
        if isinstance(
            event.payload,
            (AddToCartPayload, OrderCreatedPayload, PaymentProcessedPayload),
        )
    ]

    assert monetary_payloads
    assert all(payload.currency == "USD" for payload in monetary_payloads)


def test_generated_event_mix_includes_multiple_types_under_default_weights() -> None:
    settings = ProducerSettings()
    generator = EventGenerator(settings)

    events = [generator.next_event().event_type for _ in range(200)]
    counts = Counter(events)

    assert len(counts) >= 3
    assert counts["page_view"] > 0
    assert sum(counts.values()) == 200