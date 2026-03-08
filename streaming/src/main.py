from __future__ import annotations

import logging
import sys

from pyspark.sql import SparkSession

from clickhouse_sink import build_clickhouse_batch_writer
from config import get_settings
from transformations import build_metrics_from_kafka


class StreamingJob:

    def __init__(self) -> None:
        self._settings = get_settings()
        self._configure_logging()
        self._log = logging.getLogger(__name__)
        self._spark: SparkSession | None = None

    def run(self) -> int:
        self._log.info(
            "Starting streaming job: app=%s env=%s kafka=%s topic=%s clickhouse=%s:%s/%s table=%s",
            self._settings.spark_app_name,
            self._settings.app_env,
            self._settings.kafka_bootstrap_servers,
            self._settings.kafka_topic_events,
            self._settings.clickhouse_host,
            self._settings.clickhouse_port,
            self._settings.clickhouse_database,
            self._settings.clickhouse_metrics_table,
        )

        try:
            self._spark = self._build_spark_session()
            raw_df = self._read_kafka_stream(self._spark)
            metrics_df = build_metrics_from_kafka(raw_df, self._settings)
            query = self._start_metrics_query(metrics_df)

            self._log.info(
                "Streaming query started successfully: query_name=%s checkpoint_dir=%s",
                self._settings.spark_query_name,
                self._settings.spark_checkpoint_metrics_dir,
            )

            query.awaitTermination()
            return 0

        except KeyboardInterrupt:
            self._log.info("Keyboard interrupt received. Stopping streaming job.")
            return 0
        except Exception:
            self._log.exception("Streaming job failed with an unrecoverable error.")
            return 1
        finally:
            self._shutdown()

    def _build_spark_session(self) -> SparkSession:
        spark = (
            SparkSession.builder.appName(self._settings.spark_app_name)
            .master(self._settings.spark_master_url)
            .config(
                "spark.sql.session.timeZone",
                self._settings.app_timezone,
            )
            .config(
                "spark.sql.shuffle.partitions",
                "4",
            )
            .config(
                "spark.streaming.stopGracefullyOnShutdown",
                "true",
            )
            .getOrCreate()
        )

        spark.sparkContext.setLogLevel("WARN")
        return spark

    def _read_kafka_stream(self, spark: SparkSession):
        self._log.info(
            "Configuring Kafka source: bootstrap_servers=%s topic=%s starting_offsets=%s",
            self._settings.kafka_bootstrap_servers,
            self._settings.kafka_topic_events,
            self._settings.spark_kafka_starting_offsets,
        )

        return (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", self._settings.kafka_bootstrap_servers)
            .option("subscribe", self._settings.kafka_topic_events)
            .option("startingOffsets", self._settings.spark_kafka_starting_offsets)
            .option("failOnDataLoss", "false")
            .load()
        )

    def _start_metrics_query(self, metrics_df):
        batch_writer = build_clickhouse_batch_writer(self._settings)

        return (
            metrics_df.writeStream.outputMode("append")
            .queryName(self._settings.spark_query_name)
            .trigger(processingTime=self._settings.spark_trigger_interval)
            .option("checkpointLocation", self._settings.spark_checkpoint_metrics_dir)
            .foreachBatch(batch_writer)
            .start()
        )

    def _shutdown(self) -> None:
        if self._spark is not None:
            self._log.info("Stopping Spark session.")
            self._spark.stop()
            self._spark = None

    def _configure_logging(self) -> None:
        root_logger = logging.getLogger()
        if root_logger.handlers:
            return

        level_name = self._settings.app_log_level.upper()
        level = getattr(logging, level_name, logging.INFO)

        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def main() -> int:
    job = StreamingJob()
    return job.run()


if __name__ == "__main__":
    sys.exit(main())