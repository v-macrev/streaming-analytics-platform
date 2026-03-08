from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


EventType = Literal[
    "page_view",
    "add_to_cart",
    "order_created",
    "payment_processed",
    "inventory_updated",
]


class PageViewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: str = Field(min_length=1, max_length=128)
    product_id: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=64)
    referrer: str = Field(default="direct", min_length=1, max_length=128)


class AddToCartPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=100)
    unit_price: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(default="BRL", min_length=3, max_length=3)

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> float:
        return float(value)


class OrderCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1, max_length=64)
    items_count: int = Field(ge=1, le=1000)
    total_amount: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(min_length=3, max_length=3)
    channel: str = Field(default="web", min_length=1, max_length=32)

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> float:
        return float(value)


class PaymentProcessedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str = Field(min_length=1, max_length=64)
    order_id: str = Field(min_length=1, max_length=64)
    payment_method: Literal[
        "credit_card",
        "pix",
        "debit_card",
        "wallet",
        "boleto",
    ]
    payment_status: Literal["approved", "declined", "pending"]
    amount: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(default="BRL", min_length=3, max_length=3)

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> float:
        return float(value)


class InventoryUpdatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(min_length=1, max_length=64)
    warehouse_id: str = Field(min_length=1, max_length=64)
    delta_qty: int = Field(ge=-100000, le=100000)
    stock_after: int = Field(ge=0, le=1000000)
    reason: Literal["sale", "restock", "adjustment", "return"] = "adjustment"


PayloadModel = Union[
    PageViewPayload,
    AddToCartPayload,
    OrderCreatedPayload,
    PaymentProcessedPayload,
    InventoryUpdatedPayload,
]


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    event_type: EventType
    event_time: datetime
    producer_time: datetime
    user_id: str = Field(min_length=1, max_length=64)
    session_id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=64)
    payload: PayloadModel

    @model_validator(mode="after")
    def validate_payload_matches_event_type(self) -> "EventEnvelope":
        expected_payload_map: dict[EventType, type[BaseModel]] = {
            "page_view": PageViewPayload,
            "add_to_cart": AddToCartPayload,
            "order_created": OrderCreatedPayload,
            "payment_processed": PaymentProcessedPayload,
            "inventory_updated": InventoryUpdatedPayload,
        }

        expected_type = expected_payload_map[self.event_type]
        if not isinstance(self.payload, expected_type):
            raise ValueError(
                f"Payload type {type(self.payload).__name__} does not match "
                f"event_type '{self.event_type}'. Expected {expected_type.__name__}."
            )

        return self

    @field_serializer("event_time", "producer_time")
    def serialize_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()

    @classmethod
    def build(
        cls,
        *,
        event_type: EventType,
        user_id: str,
        session_id: str,
        source: str,
        payload: PayloadModel,
        event_time: datetime | None = None,
        producer_time: datetime | None = None,
        event_id: str | None = None,
    ) -> "EventEnvelope":
        now = datetime.now(timezone.utc)

        return cls(
            event_id=event_id or str(uuid4()),
            event_type=event_type,
            event_time=event_time or now,
            producer_time=producer_time or now,
            user_id=user_id,
            session_id=session_id,
            source=source,
            payload=payload,
        )


class ProducerRecord(BaseModel):

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=256)
    value: EventEnvelope

    @classmethod
    def from_event(cls, event: EventEnvelope) -> "ProducerRecord":
        return cls(
            key=event.user_id,
            value=event,
        )