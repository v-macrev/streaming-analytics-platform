from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from models import (
    AddToCartPayload,
    EventEnvelope,
    InventoryUpdatedPayload,
    OrderCreatedPayload,
    PageViewPayload,
    PaymentProcessedPayload,
    ProducerRecord,
)


def test_page_view_event_envelope_builds_successfully() -> None:
    payload = PageViewPayload(
        page="/product",
        product_id="prd_1001",
        category="electronics",
        referrer="google",
    )

    event = EventEnvelope.build(
        event_type="page_view",
        user_id="1234",
        session_id="sess_abc123",
        source="web-simulator",
        payload=payload,
    )

    assert event.event_type == "page_view"
    assert event.user_id == "1234"
    assert event.session_id == "sess_abc123"
    assert event.source == "web-simulator"
    assert event.payload == payload
    assert event.event_id
    assert event.event_time.tzinfo is not None
    assert event.producer_time.tzinfo is not None


def test_add_to_cart_payload_serializes_decimal_as_json_number() -> None:
    payload = AddToCartPayload(
        product_id="prd_1002",
        quantity=2,
        unit_price=Decimal("79.90"),
        currency="BRL",
    )

    dumped = payload.model_dump(mode="json")

    assert dumped["product_id"] == "prd_1002"
    assert dumped["quantity"] == 2
    assert dumped["unit_price"] == 79.90
    assert dumped["currency"] == "BRL"


def test_order_created_payload_serializes_total_amount_as_json_number() -> None:
    payload = OrderCreatedPayload(
        order_id="ord_abc123",
        items_count=3,
        total_amount=Decimal("249.90"),
        currency="BRL",
        channel="web",
    )

    dumped = payload.model_dump(mode="json")

    assert dumped["order_id"] == "ord_abc123"
    assert dumped["items_count"] == 3
    assert dumped["total_amount"] == 249.90
    assert dumped["currency"] == "BRL"
    assert dumped["channel"] == "web"


def test_payment_processed_payload_serializes_amount_as_json_number() -> None:
    payload = PaymentProcessedPayload(
        payment_id="pay_abc123",
        order_id="ord_abc123",
        payment_method="pix",
        payment_status="approved",
        amount=Decimal("249.90"),
        currency="BRL",
    )

    dumped = payload.model_dump(mode="json")

    assert dumped["payment_id"] == "pay_abc123"
    assert dumped["order_id"] == "ord_abc123"
    assert dumped["payment_method"] == "pix"
    assert dumped["payment_status"] == "approved"
    assert dumped["amount"] == 249.90
    assert dumped["currency"] == "BRL"


def test_inventory_updated_payload_accepts_negative_delta_qty() -> None:
    payload = InventoryUpdatedPayload(
        product_id="prd_1003",
        warehouse_id="wh_01",
        delta_qty=-4,
        stock_after=16,
        reason="sale",
    )

    assert payload.product_id == "prd_1003"
    assert payload.warehouse_id == "wh_01"
    assert payload.delta_qty == -4
    assert payload.stock_after == 16
    assert payload.reason == "sale"


def test_event_envelope_serializes_datetimes_as_utc_iso_strings() -> None:
    event_time = datetime(2026, 3, 7, 15, 30, 0, tzinfo=timezone.utc)
    producer_time = datetime(2026, 3, 7, 15, 30, 5, tzinfo=timezone.utc)

    payload = PageViewPayload(
        page="/product",
        product_id="prd_1004",
        category="books",
        referrer="email",
    )

    event = EventEnvelope(
        event_id="evt_001",
        event_type="page_view",
        event_time=event_time,
        producer_time=producer_time,
        user_id="5678",
        session_id="sess_xyz987",
        source="web-simulator",
        payload=payload,
    )

    dumped = event.model_dump(mode="json")

    assert dumped["event_time"] == "2026-03-07T15:30:00+00:00"
    assert dumped["producer_time"] == "2026-03-07T15:30:05+00:00"


def test_event_envelope_rejects_payload_mismatch_for_event_type() -> None:
    wrong_payload = PageViewPayload(
        page="/product",
        product_id="prd_1005",
        category="fashion",
        referrer="direct",
    )

    with pytest.raises(ValidationError) as exc_info:
        EventEnvelope(
            event_id="evt_bad_001",
            event_type="payment_processed",
            event_time=datetime.now(timezone.utc),
            producer_time=datetime.now(timezone.utc),
            user_id="7777",
            session_id="sess_bad001",
            source="web-simulator",
            payload=wrong_payload,
        )

    assert "does not match event_type" in str(exc_info.value)


def test_producer_record_uses_user_id_as_kafka_key() -> None:
    payload = PageViewPayload(
        page="/search",
        product_id="prd_1006",
        category="fashion",
        referrer="instagram",
    )

    event = EventEnvelope.build(
        event_type="page_view",
        user_id="9999",
        session_id="sess_keytest",
        source="web-simulator",
        payload=payload,
    )

    record = ProducerRecord.from_event(event)

    assert record.key == "9999"
    assert record.value == event


@pytest.mark.parametrize(
    ("payload", "expected_event_type"),
    [
        (
            PageViewPayload(
                page="/home",
                product_id="prd_1001",
                category="electronics",
                referrer="direct",
            ),
            "page_view",
        ),
        (
            AddToCartPayload(
                product_id="prd_1002",
                quantity=1,
                unit_price=Decimal("79.90"),
                currency="BRL",
            ),
            "add_to_cart",
        ),
        (
            OrderCreatedPayload(
                order_id="ord_param_001",
                items_count=2,
                total_amount=Decimal("159.80"),
                currency="BRL",
                channel="web",
            ),
            "order_created",
        ),
        (
            PaymentProcessedPayload(
                payment_id="pay_param_001",
                order_id="ord_param_001",
                payment_method="credit_card",
                payment_status="approved",
                amount=Decimal("159.80"),
                currency="BRL",
            ),
            "payment_processed",
        ),
        (
            InventoryUpdatedPayload(
                product_id="prd_1007",
                warehouse_id="wh_02",
                delta_qty=10,
                stock_after=50,
                reason="restock",
            ),
            "inventory_updated",
        ),
    ],
)
def test_event_envelope_build_accepts_all_supported_payload_types(
    payload: object,
    expected_event_type: str,
) -> None:
    event = EventEnvelope.build(
        event_type=expected_event_type,
        user_id="2001",
        session_id="sess_supported",
        source="web-simulator",
        payload=payload,
    )

    assert event.event_type == expected_event_type
    assert event.payload == payload