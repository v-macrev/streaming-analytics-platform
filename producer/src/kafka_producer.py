from __future__ import annotations

import logging
from typing import Any

import orjson
from confluent_kafka import Producer
from confluent_kafka import KafkaException

from config import ProducerSettings
from models import ProducerRecord


log = logging.getLogger(__name__)


class KafkaEventProducer:

    def __init__(self, settings: ProducerSettings) -> None:
        self._settings = settings
        self._producer = Producer(self._build_config(settings))
        self._topic = settings.kafka_topic_events

    @staticmethod
    def _build_config(settings: ProducerSettings) -> dict[str, Any]:
        return {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": settings.app_name,
            "acks": "all",
            "enable.idempotence": True,
            "linger.ms": 25,
            "batch.size": 32768,
            "compression.type": "lz4",
            "message.timeout.ms": 30000,
            "retries": 10,
            "retry.backoff.ms": 500,
            "socket.timeout.ms": 30000,
            "queue.buffering.max.messages": 100000,
        }

    def publish(self, record: ProducerRecord) -> None:
        payload = self._serialize_record(record)

        try:
            self._producer.produce(
                topic=self._topic,
                key=record.key.encode("utf-8"),
                value=payload,
                on_delivery=self._delivery_callback,
            )
            self._producer.poll(0)
        except BufferError as exc:
            log.warning(
                "Kafka local queue is full while publishing to topic '%s'. "
                "Forcing producer poll/flush cycle before retry.",
                self._topic,
            )
            self._producer.poll(1.0)
            try:
                self._producer.produce(
                    topic=self._topic,
                    key=record.key.encode("utf-8"),
                    value=payload,
                    on_delivery=self._delivery_callback,
                )
                self._producer.poll(0)
            except Exception as retry_exc:  # noqa: BLE001
                raise RuntimeError(
                    "Failed to publish record to Kafka after local queue recovery."
                ) from retry_exc
        except KafkaException as exc:
            raise RuntimeError("Kafka producer error while publishing record.") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Unexpected error while publishing record to Kafka.") from exc

    def flush(self, timeout: float = 10.0) -> int:
        remaining = self._producer.flush(timeout=timeout)
        if remaining > 0:
            log.warning(
                "Kafka producer flush completed with %s message(s) still pending.",
                remaining,
            )
        return remaining

    def close(self, timeout: float = 10.0) -> None:
        remaining = self.flush(timeout=timeout)
        if remaining == 0:
            log.info("Kafka producer closed cleanly.")
        else:
            log.warning(
                "Kafka producer closed with %s message(s) still pending delivery.",
                remaining,
            )

    @staticmethod
    def _serialize_record(record: ProducerRecord) -> bytes:
        try:
            return orjson.dumps(record.value.model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Failed to serialize producer record to JSON.") from exc

    @staticmethod
    def _delivery_callback(err: Any, msg: Any) -> None:
        if err is not None:
            log.error(
                "Kafka delivery failed: topic=%s partition=%s error=%s",
                msg.topic() if msg is not None else "unknown",
                msg.partition() if msg is not None else "unknown",
                err,
            )
            return

        log.debug(
            "Kafka delivery succeeded: topic=%s partition=%s offset=%s",
            msg.topic(),
            msg.partition(),
            msg.offset(),
        )