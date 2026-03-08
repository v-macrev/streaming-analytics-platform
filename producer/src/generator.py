from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable
from uuid import uuid4

from config import EventType, ProducerSettings
from models import (
    AddToCartPayload,
    EventEnvelope,
    InventoryUpdatedPayload,
    OrderCreatedPayload,
    PageViewPayload,
    PaymentProcessedPayload,
)

TWOPLACES = Decimal("0.01")


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Product:
    product_id: str
    category: str
    unit_price: Decimal


@dataclass(frozen=True)
class OrderContext:
    order_id: str
    user_id: str
    amount: Decimal
    currency: str


class EventGenerator:
    def __init__(self, settings: ProducerSettings) -> None:
        self.settings = settings
        self._rng = random.Random()

        self._products: tuple[Product, ...] = (
            Product("prd_1001", "electronics", Decimal("199.90")),
            Product("prd_1002", "electronics", Decimal("79.90")),
            Product("prd_1003", "books", Decimal("39.90")),
            Product("prd_1004", "books", Decimal("59.90")),
            Product("prd_1005", "fashion", Decimal("129.90")),
            Product("prd_1006", "fashion", Decimal("89.90")),
            Product("prd_1007", "home", Decimal("249.90")),
            Product("prd_1008", "home", Decimal("149.90")),
            Product("prd_1009", "health", Decimal("29.90")),
            Product("prd_1010", "health", Decimal("49.90")),
        )

        self._pages_by_category: dict[str, tuple[str, ...]] = {
            "electronics": ("/home", "/search", "/product", "/deals"),
            "books": ("/home", "/search", "/product", "/recommendations"),
            "fashion": ("/home", "/search", "/product", "/new-arrivals"),
            "home": ("/home", "/search", "/product", "/collections"),
            "health": ("/home", "/search", "/product", "/pharmacy"),
        }

        self._referrers: tuple[str, ...] = (
            "direct",
            "google",
            "instagram",
            "email",
            "push_notification",
            "affiliate",
        )

        self._payment_methods: tuple[str, ...] = (
            "credit_card",
            "pix",
            "debit_card",
            "wallet",
            "boleto",
        )

        self._stock_by_product: dict[str, int] = {
            product.product_id: self._rng.randint(20, 250)
            for product in self._products
        }

        self._recent_orders: list[OrderContext] = []

        self._builders: dict[EventType, Callable[[], EventEnvelope]] = {
            "page_view": self._build_page_view_event,
            "add_to_cart": self._build_add_to_cart_event,
            "order_created": self._build_order_created_event,
            "payment_processed": self._build_payment_processed_event,
            "inventory_updated": self._build_inventory_updated_event,
        }

    def next_event(self) -> EventEnvelope:
        event_type = self._choose_event_type()
        return self._builders[event_type]()

    def _choose_event_type(self) -> EventType:
        event_types = list(self.settings.event_weights.keys())
        weights = list(self.settings.event_weights.values())
        return self._rng.choices(event_types, weights=weights, k=1)[0]

    def _random_user_id(self) -> str:
        value = self._rng.randint(
            self.settings.producer_user_id_min,
            self.settings.producer_user_id_max,
        )
        return str(value)

    def _random_session_id(self) -> str:
        return f"{self.settings.producer_session_id_prefix}_{uuid4().hex[:12]}"

    def _random_order_id(self) -> str:
        return f"{self.settings.producer_order_id_prefix}_{uuid4().hex[:12]}"

    def _random_payment_id(self) -> str:
        return f"{self.settings.producer_payment_id_prefix}_{uuid4().hex[:12]}"

    def _random_product(self) -> Product:
        return self._rng.choice(self._products)

    def _random_warehouse_id(self) -> str:
        warehouse_number = self._rng.randint(
            1,
            self.settings.producer_inventory_warehouse_count,
        )
        return f"wh_{warehouse_number:02d}"

    def _random_event_time(self) -> datetime:
        now = datetime.now(timezone.utc)
        lag_seconds = self._rng.randint(0, 20)
        return now - timedelta(seconds=lag_seconds)

    def _append_recent_order(self, order: OrderContext) -> None:
        self._recent_orders.append(order)
        max_size = 500
        if len(self._recent_orders) > max_size:
            self._recent_orders = self._recent_orders[-max_size:]

    def _build_page_view_event(self) -> EventEnvelope:
        product = self._random_product()
        page = self._rng.choice(self._pages_by_category[product.category])

        payload = PageViewPayload(
            page=page,
            product_id=product.product_id,
            category=product.category,
            referrer=self._rng.choice(self._referrers),
        )

        return EventEnvelope.build(
            event_type="page_view",
            user_id=self._random_user_id(),
            session_id=self._random_session_id(),
            source=self.settings.producer_source_name,
            payload=payload,
            event_time=self._random_event_time(),
        )

    def _build_add_to_cart_event(self) -> EventEnvelope:
        product = self._random_product()

        payload = AddToCartPayload(
            product_id=product.product_id,
            quantity=self._rng.randint(1, 4),
            unit_price=_quantize_money(product.unit_price),
            currency=self.settings.producer_currency,
        )

        return EventEnvelope.build(
            event_type="add_to_cart",
            user_id=self._random_user_id(),
            session_id=self._random_session_id(),
            source=self.settings.producer_source_name,
            payload=payload,
            event_time=self._random_event_time(),
        )

    def _build_order_created_event(self) -> EventEnvelope:
        product = self._random_product()
        items_count = self._rng.randint(1, 5)

        base_amount = product.unit_price * Decimal(items_count)
        amount_multiplier = Decimal(str(self._rng.uniform(0.95, 1.25)))
        total_amount = _quantize_money(base_amount * amount_multiplier)

        user_id = self._random_user_id()
        order_id = self._random_order_id()

        payload = OrderCreatedPayload(
            order_id=order_id,
            items_count=items_count,
            total_amount=total_amount,
            currency=self.settings.producer_currency,
            channel="web",
        )

        self._append_recent_order(
            OrderContext(
                order_id=order_id,
                user_id=user_id,
                amount=total_amount,
                currency=self.settings.producer_currency,
            )
        )

        return EventEnvelope.build(
            event_type="order_created",
            user_id=user_id,
            session_id=self._random_session_id(),
            source=self.settings.producer_source_name,
            payload=payload,
            event_time=self._random_event_time(),
        )

    def _build_payment_processed_event(self) -> EventEnvelope:
        order_context = self._pick_or_create_order_for_payment()

        status = self._rng.choices(
            population=["approved", "declined", "pending"],
            weights=[82, 12, 6],
            k=1,
        )[0]

        payload = PaymentProcessedPayload(
            payment_id=self._random_payment_id(),
            order_id=order_context.order_id,
            payment_method=self._rng.choice(self._payment_methods),
            payment_status=status,
            amount=_quantize_money(order_context.amount),
            currency=order_context.currency,
        )

        return EventEnvelope.build(
            event_type="payment_processed",
            user_id=order_context.user_id,
            session_id=self._random_session_id(),
            source=self.settings.producer_source_name,
            payload=payload,
            event_time=self._random_event_time(),
        )

    def _pick_or_create_order_for_payment(self) -> OrderContext:
        if self._recent_orders and self._rng.random() < 0.85:
            return self._rng.choice(self._recent_orders)

        product = self._random_product()
        items_count = self._rng.randint(1, 4)
        total_amount = _quantize_money(product.unit_price * Decimal(items_count))

        return OrderContext(
            order_id=self._random_order_id(),
            user_id=self._random_user_id(),
            amount=total_amount,
            currency=self.settings.producer_currency,
        )

    def _build_inventory_updated_event(self) -> EventEnvelope:
        product = self._random_product()
        current_stock = self._stock_by_product[product.product_id]

        action = self._rng.choices(
            population=["sale", "restock", "adjustment", "return"],
            weights=[45, 25, 20, 10],
            k=1,
        )[0]

        if action == "sale":
            delta_qty = -self._rng.randint(1, 5)
        elif action == "restock":
            delta_qty = self._rng.randint(5, 40)
        elif action == "return":
            delta_qty = self._rng.randint(1, 3)
        else:
            delta_qty = self._rng.randint(-3, 3)

        stock_after = max(0, current_stock + delta_qty)
        applied_delta = stock_after - current_stock
        self._stock_by_product[product.product_id] = stock_after

        payload = InventoryUpdatedPayload(
            product_id=product.product_id,
            warehouse_id=self._random_warehouse_id(),
            delta_qty=applied_delta,
            stock_after=stock_after,
            reason=action,
        )

        return EventEnvelope.build(
            event_type="inventory_updated",
            user_id=self._random_user_id(),
            session_id=self._random_session_id(),
            source=self.settings.producer_source_name,
            payload=payload,
            event_time=self._random_event_time(),
        )