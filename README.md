# Real-Time Streaming Analytics Platform

A production-style event-driven analytics platform that ingests live events, processes them in real time, and exposes operational metrics through dashboards.

This project simulates the architecture used in modern data platforms for processing high-volume event streams such as:

- clickstreams
- ecommerce orders
- payment events
- inventory updates
- IoT-style telemetry

The system demonstrates how a streaming data pipeline can transform raw events into near real-time business metrics.

---

# System Architecture

The platform implements a classic streaming analytics architecture:

Producer → Kafka → Spark Structured Streaming → ClickHouse → Grafana

Event Flow:

1. **Event Producer**

   A synthetic event generator simulates business activity such as:

   - page views
   - cart additions
   - order creation
   - payment processing
   - inventory changes

   These events are serialized as JSON and published to Kafka.

2. **Kafka Broker**

   Kafka acts as the event backbone for the system.

   Topic used:

```

events.raw

```

The topic contains multiple event types sharing a common event envelope.

3. **Stream Processing**

Spark Structured Streaming consumes events from Kafka and computes real-time metrics using event-time windows.

Examples of computed metrics:

- revenue per minute
- orders per minute
- payment success rate
- active users per minute
- event throughput
- low stock alerts

4. **Analytical Storage**

Processed metrics are written into ClickHouse for fast analytical queries.

5. **Visualization**

Grafana reads metrics from ClickHouse and renders real-time dashboards.

---

# Architecture Diagram

```

+----------------+
| Event Producer |
+--------+-------+
|
v
+----------------+
|     Kafka      |
|   events.raw   |
+--------+-------+
|
v
+--------------------------+
| Spark Structured Stream  |
| Real-time Aggregations   |
+------------+-------------+
|
v
+-------------------------+
|       ClickHouse        |
|  analytics.metrics_1m   |
+------------+------------+
|
v
+-------------------------+
|        Grafana          |
|   Real-time Dashboard   |
+-------------------------+

```

---

# Repository Structure

```

streaming-analytics-platform
│
├── producer
│   └── src
│       ├── main.py
│       ├── generator.py
│       ├── config.py
│       └── models.py
│
├── streaming
│   └── src
│       ├── main.py
│       ├── config.py
│       ├── metrics.py
│       └── clickhouse_sink.py
│
├── infra
│   ├── docker-compose.yml
│   ├── clickhouse
│   │   └── init
│   │       └── 001_init_metrics.sql
│   └── grafana
│       ├── dashboards
│       └── provisioning
│
├── shared
│   └── event_contract
│       └── event_schema.json
│
├── docs
│   └── event-model.md
│
├── tests
│   └── producer
│
├── scripts
│   └── run_producer.sh
│
└── README.md

````

---

# Event Model

All events follow a **canonical envelope**.

Example:

```json
{
  "event_id": "uuid",
  "event_type": "order_created",
  "event_time": "2026-03-07T18:14:02Z",
  "producer_time": "2026-03-07T18:14:03Z",
  "user_id": "1234",
  "session_id": "sess_abc",
  "source": "web-simulator",
  "payload": { ... }
}
````

Supported event types:

* `page_view`
* `add_to_cart`
* `order_created`
* `payment_processed`
* `inventory_updated`

Full specification available in:

```
docs/event-model.md
```

---

# Running the Platform

## 1. Start Infrastructure

```
docker compose up -d
```

This launches:

* Kafka
* Spark
* ClickHouse
* Grafana

## 2. Run Event Producer

```
./scripts/run_producer.sh
```

This begins publishing events to Kafka.

## 3. Start Streaming Processor

The streaming service runs inside Docker and consumes events automatically.

---

# Accessing the Dashboard

Grafana:

```
http://localhost:3000
```

Default login:

```
admin
admin
```

The dashboard **Streaming Analytics - Realtime Overview** displays live metrics.

---

# Example Metrics

The system computes real-time metrics such as:

| Metric                       | Description                                |
| ---------------------------- | ------------------------------------------ |
| revenue_per_minute           | total revenue generated per minute         |
| orders_per_minute            | order creation rate                        |
| payment_success_rate         | ratio of approved payments                 |
| active_users_per_minute      | unique users interacting with the platform |
| events_per_minute            | throughput per event type                  |
| low_stock_signals_per_minute | inventory alerts                           |

---

# Why This Project Exists

Modern companies rely heavily on event-driven systems.

Real-time data platforms power:

* ecommerce analytics
* fraud detection
* observability pipelines
* recommendation systems
* IoT monitoring

This project demonstrates core streaming engineering concepts including:

* event modeling
* distributed messaging
* stream processing
* windowed aggregations
* analytical sinks
* operational dashboards

---

# Technologies Used

| Component           | Technology                 |
| ------------------- | -------------------------- |
| Event Broker        | Kafka                      |
| Stream Processing   | Spark Structured Streaming |
| Analytical Database | ClickHouse                 |
| Visualization       | Grafana                    |
| Containerization    | Docker                     |
| Language            | Python                     |

---

# Engineering Principles

This repository was built using several principles common in production data platforms:

* **event-driven architecture**
* **stream-first analytics**
* **schema-based contracts**
* **containerized reproducibility**
* **separation of producer and processor services**
* **observable metrics pipelines**

---

# Future Improvements

Potential extensions include:

* schema registry integration
* exactly-once processing semantics
* multiple Kafka partitions
* additional event types
* anomaly detection metrics
* Kubernetes deployment
* alerting via Grafana

---

# License

GNU Affero General Public License v3