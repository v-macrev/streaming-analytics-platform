from __future__ import annotations

import logging
import signal
import sys
import time
from types import FrameType

from config import get_settings
from generator import EventGenerator
from kafka_producer import KafkaEventProducer
from models import ProducerRecord


class ProducerService:

    def __init__(self) -> None:
        self._settings = get_settings()
        self._configure_logging()

        self._log = logging.getLogger(__name__)
        self._generator = EventGenerator(self._settings)
        self._producer = KafkaEventProducer(self._settings)
        self._running = True
        self._published_count = 0
        self._start_time = time.monotonic()

    def run(self) -> int:
        self._install_signal_handlers()

        self._log.info(
            "Starting producer service: app=%s env=%s kafka=%s topic=%s interval_ms=%s batch_size=%s enabled_event_types=%s",
            self._settings.app_name,
            self._settings.app_env,
            self._settings.kafka_bootstrap_servers,
            self._settings.kafka_topic_events,
            self._settings.producer_event_interval_ms,
            self._settings.producer_batch_size,
            ",".join(self._settings.enabled_event_types),
        )

        try:
            while self._running:
                self._publish_batch()
                time.sleep(self._settings.event_interval_seconds)
        except KeyboardInterrupt:
            self._log.info("Keyboard interrupt received. Stopping producer service.")
            self.stop()
        except Exception:
            self._log.exception("Producer service failed with an unrecoverable error.")
            self.stop()
            return 1
        finally:
            self._shutdown()

        return 0

    def stop(self) -> None:
        self._running = False

    def _publish_batch(self) -> None:
        for _ in range(self._settings.producer_batch_size):
            event = self._generator.next_event()
            record = ProducerRecord.from_event(event)
            self._producer.publish(record)
            self._published_count += 1

            self._log.debug(
                "Published event: count=%s event_id=%s event_type=%s user_id=%s",
                self._published_count,
                event.event_id,
                event.event_type,
                event.user_id,
            )

        if self._published_count % 50 == 0:
            self._log.info(
                "Producer progress: published_count=%s uptime_seconds=%.2f rate_per_sec=%.2f",
                self._published_count,
                self._uptime_seconds,
                self._publish_rate,
            )

    def _install_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        del frame
        self._log.info("Shutdown signal received: signal=%s", signum)
        self.stop()

    def _shutdown(self) -> None:
        self._log.info(
            "Shutting down producer service: published_count=%s uptime_seconds=%.2f",
            self._published_count,
            self._uptime_seconds,
        )
        self._producer.close(timeout=10.0)

    @property
    def _uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    @property
    def _publish_rate(self) -> float:
        uptime = self._uptime_seconds
        if uptime <= 0:
            return 0.0
        return self._published_count / uptime

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
    service = ProducerService()
    return service.run()


if __name__ == "__main__":
    sys.exit(main())