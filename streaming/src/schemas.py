from __future__ import annotations

from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)


def get_event_payload_schema() -> StructType:
    return StructType(
        [
            StructField("page", StringType(), nullable=True),
            StructField("product_id", StringType(), nullable=True),
            StructField("category", StringType(), nullable=True),
            StructField("referrer", StringType(), nullable=True),
            StructField("quantity", IntegerType(), nullable=True),
            StructField("unit_price", DoubleType(), nullable=True),
            StructField("currency", StringType(), nullable=True),
            StructField("order_id", StringType(), nullable=True),
            StructField("items_count", IntegerType(), nullable=True),
            StructField("total_amount", DoubleType(), nullable=True),
            StructField("channel", StringType(), nullable=True),
            StructField("payment_id", StringType(), nullable=True),
            StructField("payment_method", StringType(), nullable=True),
            StructField("payment_status", StringType(), nullable=True),
            StructField("amount", DoubleType(), nullable=True),
            StructField("warehouse_id", StringType(), nullable=True),
            StructField("delta_qty", IntegerType(), nullable=True),
            StructField("stock_after", IntegerType(), nullable=True),
            StructField("reason", StringType(), nullable=True),
        ]
    )


def get_event_envelope_schema() -> StructType:
    return StructType(
        [
            StructField("event_id", StringType(), nullable=False),
            StructField("event_type", StringType(), nullable=False),
            StructField("event_time", StringType(), nullable=False),
            StructField("producer_time", StringType(), nullable=False),
            StructField("user_id", StringType(), nullable=False),
            StructField("session_id", StringType(), nullable=False),
            StructField("source", StringType(), nullable=False),
            StructField("payload", get_event_payload_schema(), nullable=False),
        ]
    )


def get_flattened_event_columns() -> list[str]:
    return [
        "event_id",
        "event_type",
        "event_time",
        "producer_time",
        "user_id",
        "session_id",
        "source",
        "payload.page",
        "payload.product_id",
        "payload.category",
        "payload.referrer",
        "payload.quantity",
        "payload.unit_price",
        "payload.currency",
        "payload.order_id",
        "payload.items_count",
        "payload.total_amount",
        "payload.channel",
        "payload.payment_id",
        "payload.payment_method",
        "payload.payment_status",
        "payload.amount",
        "payload.warehouse_id",
        "payload.delta_qty",
        "payload.stock_after",
        "payload.reason",
    ]


def get_metric_output_columns() -> list[str]:
    return [
        "window_start",
        "window_end",
        "metric_name",
        "metric_value",
        "dimension_key",
        "dimension_value",
        "processed_at",
    ]