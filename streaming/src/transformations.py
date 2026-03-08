from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from config import StreamingSettings
from schemas import get_event_envelope_schema


def parse_kafka_events(raw_df: DataFrame) -> DataFrame:
    envelope_schema = get_event_envelope_schema()

    parsed_df = (
        raw_df.select(
            F.col("key").cast("string").alias("kafka_key"),
            F.col("value").cast("string").alias("raw_json"),
            F.col("topic").alias("kafka_topic"),
            F.col("partition").alias("kafka_partition"),
            F.col("offset").alias("kafka_offset"),
            F.col("timestamp").alias("kafka_timestamp"),
        )
        .withColumn("event", F.from_json(F.col("raw_json"), envelope_schema))
        .filter(F.col("event").isNotNull())
    )

    return parsed_df.select(
        "kafka_key",
        "kafka_topic",
        "kafka_partition",
        "kafka_offset",
        "kafka_timestamp",
        F.col("event.event_id").alias("event_id"),
        F.col("event.event_type").alias("event_type"),
        F.col("event.event_time").alias("event_time"),
        F.col("event.producer_time").alias("producer_time"),
        F.col("event.user_id").alias("user_id"),
        F.col("event.session_id").alias("session_id"),
        F.col("event.source").alias("source"),
        F.col("event.payload.page").alias("page"),
        F.col("event.payload.product_id").alias("product_id"),
        F.col("event.payload.category").alias("category"),
        F.col("event.payload.referrer").alias("referrer"),
        F.col("event.payload.quantity").alias("quantity"),
        F.col("event.payload.unit_price").alias("unit_price"),
        F.col("event.payload.currency").alias("currency"),
        F.col("event.payload.order_id").alias("order_id"),
        F.col("event.payload.items_count").alias("items_count"),
        F.col("event.payload.total_amount").alias("total_amount"),
        F.col("event.payload.channel").alias("channel"),
        F.col("event.payload.payment_id").alias("payment_id"),
        F.col("event.payload.payment_method").alias("payment_method"),
        F.col("event.payload.payment_status").alias("payment_status"),
        F.col("event.payload.amount").alias("amount"),
        F.col("event.payload.warehouse_id").alias("warehouse_id"),
        F.col("event.payload.delta_qty").alias("delta_qty"),
        F.col("event.payload.stock_after").alias("stock_after"),
        F.col("event.payload.reason").alias("reason"),
    )


def normalize_events(events_df: DataFrame, settings: StreamingSettings) -> DataFrame:
    normalized_df = (
        events_df.withColumn("event_ts", F.to_timestamp("event_time"))
        .withColumn("producer_ts", F.to_timestamp("producer_time"))
        .withColumn("quantity", F.coalesce(F.col("quantity"), F.lit(0)))
        .withColumn("unit_price", F.coalesce(F.col("unit_price"), F.lit(0.0)))
        .withColumn("items_count", F.coalesce(F.col("items_count"), F.lit(0)))
        .withColumn("total_amount", F.coalesce(F.col("total_amount"), F.lit(0.0)))
        .withColumn("amount", F.coalesce(F.col("amount"), F.lit(0.0)))
        .withColumn("delta_qty", F.coalesce(F.col("delta_qty"), F.lit(0)))
        .withColumn("stock_after", F.coalesce(F.col("stock_after"), F.lit(0)))
        .withColumn(
            "payment_approved_flag",
            F.when(
                (F.col("event_type") == "payment_processed")
                & (F.col("payment_status") == "approved"),
                F.lit(1.0),
            ).otherwise(F.lit(0.0)),
        )
        .withColumn(
            "payment_attempt_flag",
            F.when(F.col("event_type") == "payment_processed", F.lit(1.0)).otherwise(
                F.lit(0.0)
            ),
        )
        .withColumn(
            "low_stock_flag",
            F.when(
                (F.col("event_type") == "inventory_updated")
                & (F.col("stock_after") > 0)
                & (F.col("stock_after") <= 10),
                F.lit(1.0),
            ).otherwise(F.lit(0.0)),
        )
        .withColumn(
            "order_event_flag",
            F.when(F.col("event_type") == "order_created", F.lit(1.0)).otherwise(
                F.lit(0.0)
            ),
        )
        .withColumn(
            "page_view_flag",
            F.when(F.col("event_type") == "page_view", F.lit(1.0)).otherwise(
                F.lit(0.0)
            ),
        )
        .withColumn(
            "active_user_flag",
            F.when(F.col("user_id").isNotNull(), F.col("user_id")).otherwise(F.lit(None)),
        )
        .filter(F.col("event_ts").isNotNull())
        .withWatermark("event_ts", settings.stream_watermark_delay)
    )

    return normalized_df


def build_metrics(events_df: DataFrame, settings: StreamingSettings) -> DataFrame:
    window_expr = F.window(
        F.col("event_ts"),
        settings.stream_window_duration,
        settings.stream_slide_duration,
    )

    processed_at = F.current_timestamp()

    metrics_event_throughput = (
        events_df.groupBy(window_expr.alias("window"), F.col("event_type"))
        .agg(F.count(F.lit(1)).cast("double").alias("metric_value"))
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.lit("events_per_minute").alias("metric_name"),
            F.col("metric_value"),
            F.lit("event_type").alias("dimension_key"),
            F.col("event_type").alias("dimension_value"),
            processed_at.alias("processed_at"),
        )
    )

    metrics_revenue = (
        events_df.filter(F.col("event_type") == "order_created")
        .groupBy(window_expr.alias("window"))
        .agg(F.sum("total_amount").cast("double").alias("metric_value"))
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.lit("revenue_per_minute").alias("metric_name"),
            F.coalesce(F.col("metric_value"), F.lit(0.0)).alias("metric_value"),
            F.lit("scope").alias("dimension_key"),
            F.lit("all").alias("dimension_value"),
            processed_at.alias("processed_at"),
        )
    )

    metrics_orders = (
        events_df.filter(F.col("event_type") == "order_created")
        .groupBy(window_expr.alias("window"))
        .agg(F.count(F.lit(1)).cast("double").alias("metric_value"))
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.lit("orders_per_minute").alias("metric_name"),
            F.col("metric_value"),
            F.lit("scope").alias("dimension_key"),
            F.lit("all").alias("dimension_value"),
            processed_at.alias("processed_at"),
        )
    )

    metrics_payment_success = (
        events_df.filter(F.col("event_type") == "payment_processed")
        .groupBy(window_expr.alias("window"))
        .agg(
            F.sum("payment_approved_flag").alias("approved_count"),
            F.sum("payment_attempt_flag").alias("attempt_count"),
        )
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.lit("payment_success_rate").alias("metric_name"),
            F.when(F.col("attempt_count") > 0, F.col("approved_count") / F.col("attempt_count"))
            .otherwise(F.lit(0.0))
            .cast("double")
            .alias("metric_value"),
            F.lit("scope").alias("dimension_key"),
            F.lit("all").alias("dimension_value"),
            processed_at.alias("processed_at"),
        )
    )

    metrics_active_users = (
        events_df.groupBy(window_expr.alias("window"))
        .agg(F.countDistinct("user_id").cast("double").alias("metric_value"))
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.lit("active_users_per_minute").alias("metric_name"),
            F.col("metric_value"),
            F.lit("scope").alias("dimension_key"),
            F.lit("all").alias("dimension_value"),
            processed_at.alias("processed_at"),
        )
    )

    metrics_low_stock = (
        events_df.filter(F.col("event_type") == "inventory_updated")
        .groupBy(window_expr.alias("window"))
        .agg(F.sum("low_stock_flag").cast("double").alias("metric_value"))
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.lit("low_stock_signals_per_minute").alias("metric_name"),
            F.coalesce(F.col("metric_value"), F.lit(0.0)).alias("metric_value"),
            F.lit("scope").alias("dimension_key"),
            F.lit("all").alias("dimension_value"),
            processed_at.alias("processed_at"),
        )
    )

    return (
        metrics_event_throughput.unionByName(metrics_revenue)
        .unionByName(metrics_orders)
        .unionByName(metrics_payment_success)
        .unionByName(metrics_active_users)
        .unionByName(metrics_low_stock)
    )


def build_metrics_from_kafka(raw_df: DataFrame, settings: StreamingSettings) -> DataFrame:
    parsed_df = parse_kafka_events(raw_df)
    normalized_df = normalize_events(parsed_df, settings)
    return build_metrics(normalized_df, settings)