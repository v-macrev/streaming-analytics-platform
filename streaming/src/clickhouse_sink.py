from __future__ import annotations

import logging
from dataclasses import dataclass

import clickhouse_connect
from pyspark.sql import DataFrame

from config import StreamingSettings


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClickHouseInsertConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    table: str

    @classmethod
    def from_settings(cls, settings: StreamingSettings) -> "ClickHouseInsertConfig":
        return cls(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            database=settings.clickhouse_database,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            table=settings.clickhouse_metrics_table,
        )


class ClickHouseMetricsSink:

    def __init__(self, settings: StreamingSettings) -> None:
        self._config = ClickHouseInsertConfig.from_settings(settings)

    def write_batch(self, batch_df: DataFrame, batch_id: int) -> None:
        if batch_df.isEmpty():
            log.info("Skipping empty metrics batch: batch_id=%s", batch_id)
            return

        row_count = batch_df.count()
        rows = self._collect_rows(batch_df)

        if not rows:
            log.info("Skipping batch with no insertable rows: batch_id=%s", batch_id)
            return

        client = self._create_client()
        try:
            client.insert(
                table=self._config.table,
                data=rows,
                column_names=[
                    "window_start",
                    "window_end",
                    "metric_name",
                    "metric_value",
                    "dimension_key",
                    "dimension_value",
                    "processed_at",
                ],
                database=self._config.database,
            )
        finally:
            client.close()

        log.info(
            "Inserted metrics batch into ClickHouse: batch_id=%s row_count=%s table=%s",
            batch_id,
            row_count,
            self._config.table,
        )

    def _create_client(self):
        return clickhouse_connect.get_client(
            host=self._config.host,
            port=self._config.port,
            database=self._config.database,
            username=self._config.username,
            password=self._config.password,
        )

    @staticmethod
    def _collect_rows(batch_df: DataFrame) -> list[tuple]:
        selected_df = batch_df.select(
            "window_start",
            "window_end",
            "metric_name",
            "metric_value",
            "dimension_key",
            "dimension_value",
            "processed_at",
        )

        return [
            (
                row["window_start"],
                row["window_end"],
                row["metric_name"],
                float(row["metric_value"]) if row["metric_value"] is not None else 0.0,
                row["dimension_key"],
                row["dimension_value"],
                row["processed_at"],
            )
            for row in selected_df.collect()
        ]


def build_clickhouse_batch_writer(settings: StreamingSettings):
    sink = ClickHouseMetricsSink(settings)

    def _writer(batch_df: DataFrame, batch_id: int) -> None:
        sink.write_batch(batch_df, batch_id)

    return _writer