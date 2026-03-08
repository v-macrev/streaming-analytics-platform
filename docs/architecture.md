# Architecture Specification

## 1. Purpose

This document defines the architecture of the Streaming Analytics Platform, a production-grade local real-time analytics system designed to ingest, process, aggregate, store, and visualise live operational events.

The platform is built to simulate a realistic event-driven analytics environment used by modern digital businesses. It is intended both as a working engineering artefact and as a portfolio project demonstrating strong system design, streaming architecture, and delivery discipline.

## 2. Architectural Goals

The platform is designed to satisfy the following goals:

- ingest live business events continuously
- decouple event producers from analytical consumers
- compute near-real-time metrics using stream processing
- persist analytical outputs in a store optimised for fast queries
- expose live dashboards for operational visibility
- run reproducibly in a local environment
- remain extensible toward Kubernetes-based deployment

## 3. Non-Goals

The first version of the platform is not intended to provide:

- exactly-once guarantees across the full pipeline
- enterprise-grade multi-node resilience
- schema registry infrastructure
- raw event lakehouse persistence
- long-term historical backfill workflows
- multi-tenant security isolation

These are valid future concerns, but they are outside the initial scope of a credible local streaming analytics delivery.

## 4. System Overview

The platform consists of the following major components:

1. **Producer Service**  
   A Python application that simulates live event traffic across multiple business domains.

2. **Kafka Broker**  
   The event backbone used to ingest and distribute events asynchronously.

3. **Spark Structured Streaming Job**  
   The stream processor that consumes Kafka events, parses and validates the event contract, computes windowed analytical metrics, and writes results to ClickHouse.

4. **ClickHouse**  
   The analytical database used to store real-time aggregate metrics for fast read access.

5. **Grafana**  
   The visualisation layer used to query ClickHouse and present operational dashboards.

6. **Docker Compose**  
   The local orchestration layer used to run the full platform in a reproducible way.

7. **Kubernetes Extension (Planned)**  
   A future deployment mode for orchestration beyond local Compose-based execution.

## 5. High-Level Component Diagram

```text
+-------------------------+
| Producer Service        |
| Python Event Generator  |
+------------+------------+
             |
             v
+-------------------------+
| Kafka                   |
| Topic: events.raw       |
+------------+------------+
             |
             v
+-------------------------+
| Spark Structured        |
| Streaming Aggregation   |
+------------+------------+
             |
             v
+-------------------------+
| ClickHouse              |
| metrics_realtime_1m     |
+------------+------------+
             |
             v
+-------------------------+
| Grafana                 |
| Operational Dashboards  |
+-------------------------+
````

## 6. End-to-End Data Flow

The end-to-end flow of data is:

1. The producer generates synthetic events for page activity, cart actions, orders, payments, and inventory updates.
2. Each event is wrapped in a canonical JSON envelope.
3. Events are published to Kafka topic `events.raw`.
4. Spark Structured Streaming consumes the topic from Kafka.
5. The streaming job parses the JSON payload into structured columns.
6. The job applies event-time semantics and watermarking.
7. Windowed aggregations are computed in one-minute windows.
8. The aggregated metrics are written into ClickHouse table `metrics_realtime_1m`.
9. Grafana queries ClickHouse and renders near-real-time dashboards.

## 7. Domain Event Model

The platform simulates several event domains in order to represent a realistic business stream.

### 7.1 Event Types

The initial set of event types is:

* `page_view`
* `add_to_cart`
* `order_created`
* `payment_processed`
* `inventory_updated`

These events are sufficient to model user behaviour, conversion funnel activity, commerce transactions, payment outcomes, and operational stock movement.

### 7.2 Canonical Event Envelope

All events will share a common top-level structure.

Expected top-level fields:

* `event_id`
* `event_type`
* `event_time`
* `producer_time`
* `user_id`
* `session_id`
* `source`
* `payload`

The envelope provides consistent ingestion semantics while allowing the payload to vary by business domain.

### 7.3 Payload Strategy

The `payload` object will contain event-specific fields.

Examples:

#### `page_view`

* `page`
* `product_id`
* `category`

#### `add_to_cart`

* `product_id`
* `quantity`
* `unit_price`

#### `order_created`

* `order_id`
* `items_count`
* `total_amount`
* `currency`

#### `payment_processed`

* `payment_id`
* `order_id`
* `payment_method`
* `payment_status`
* `amount`

#### `inventory_updated`

* `product_id`
* `warehouse_id`
* `delta_qty`
* `stock_after`

This design balances consistency with flexibility and avoids creating a separate ingestion pipeline for each domain too early.

## 8. Topic Design

### 8.1 Initial Topic Strategy

The initial design uses a single Kafka topic:

* `events.raw`

This is intentional.

For the first implementation phase, a single raw topic offers several advantages:

* simpler broker configuration
* simpler producer logic
* simpler consumer logic
* fewer moving parts during validation
* easier traceability during debugging

The event type will be carried inside the message payload via `event_type`.

### 8.2 Future Topic Evolution

If the project evolves, the following topic model may be introduced:

* `events.web`
* `events.commerce`
* `events.payments`
* `events.inventory`

However, this split is not necessary for the initial end-to-end platform and would add complexity before the pipeline fundamentals are proven.

## 9. Processing Model

### 9.1 Stream Processor Choice

Spark Structured Streaming is used because it offers:

* strong relevance for modern data engineering
* practical Python integration
* mature Kafka source support
* event-time windowing support
* a credible portfolio signal

### 9.2 Processing Semantics

The initial system will operate with practical at-least-once behaviour.

This means:

* duplicate writes are possible in certain failure cases
* strict exactly-once end-to-end semantics are not claimed
* the design prioritises clarity and credibility over false promises

That is a realistic and honest tradeoff for a local portfolio-grade system.

### 9.3 Event-Time Handling

The streaming job will use `event_time` as the primary event-time field.

A watermark delay will be applied to bound late-arriving events.

Initial configuration:

* watermark delay: `2 minutes`
* window duration: `1 minute`
* slide duration: `1 minute`

This supports minute-level operational monitoring while remaining simple and robust.

### 9.4 Aggregation Model

The first analytical outputs will be computed as one-minute windowed aggregates.

Initial metric families include:

* event throughput
* revenue
* order count
* payment success rate
* active users
* low-stock inventory signals

The processor will transform raw events into dashboard-friendly metric rows instead of simply moving data from one system to another.

## 10. Storage Design

### 10.1 Storage Choice

ClickHouse is the analytical store because it is well suited to:

* high-performance aggregations
* time-based queries
* dashboard workloads
* operational analytics patterns

### 10.2 Initial Sink Model

The initial sink table is:

* `metrics_realtime_1m`

This table will store metric rows in a long-format analytical structure rather than creating a separate table for every metric type.

Expected logical columns include:

* `window_start`
* `window_end`
* `metric_name`
* `metric_value`
* `dimension_key`
* `dimension_value`
* `processed_at`

This design keeps the storage model flexible and dashboard-oriented.

### 10.3 Why Aggregates First

The first version of the project prioritises aggregated metrics over raw event persistence.

Reasons:

* the primary system goal is real-time analytics
* Grafana needs query-friendly metric outputs
* storing raw events first would expand scope unnecessarily
* aggregated sinks provide a cleaner demonstration of streaming value

Raw event persistence can be added later if needed.

## 11. Dashboard Design

Grafana will query ClickHouse directly and expose operational dashboards for:

* revenue per minute
* orders per minute
* payment approval rate
* events per minute by type
* active users per minute
* low-stock inventory alert counts

The dashboard layer is intentionally operational rather than exploratory. The goal is to show live monitoring capability from a streaming pipeline.

## 12. Deployment Model

### 12.1 Primary Deployment Mode

The primary deployment model is **Docker Compose**.

This choice was made because it provides:

* local reproducibility
* lower complexity during initial delivery
* easier debugging
* faster reviewer setup

The Compose topology will include:

* Kafka
* Kafka UI
* Spark master
* Spark worker
* ClickHouse
* Grafana
* producer container
* streaming job container

### 12.2 Planned Deployment Extension

A future `k8s/` layer will be introduced after the Compose-based platform is fully functional.

That extension may include:

* Deployments
* Services
* ConfigMaps
* Secrets
* persistent volume claims
* optional Helm-based packaging

This sequencing is deliberate. The system must first prove its end-to-end behaviour before absorbing orchestration complexity.

## 13. Service Responsibilities

### 13.1 Producer Service

Responsibilities:

* generate synthetic events
* maintain canonical envelope shape
* publish events to Kafka
* provide configurable emission rate
* simulate multiple event domains

Non-responsibilities:

* complex business validation
* downstream analytics
* durable storage

### 13.2 Kafka

Responsibilities:

* accept published events
* buffer and distribute events to consumers
* decouple producers from processors

Non-responsibilities:

* analytical querying
* metric computation
* dashboard rendering

### 13.3 Streaming Job

Responsibilities:

* consume Kafka topic(s)
* parse structured event payloads
* validate event shape at processing level
* apply event-time windowing
* compute real-time metrics
* write aggregates to ClickHouse

Non-responsibilities:

* event production
* visualisation
* serving a user API

### 13.4 ClickHouse

Responsibilities:

* store analytical metric outputs
* support low-latency dashboard queries

Non-responsibilities:

* stream processing
* queueing
* event generation

### 13.5 Grafana

Responsibilities:

* visualise operational metrics
* provide dashboards for system behaviour

Non-responsibilities:

* transform source data
* compute aggregations itself
* act as a persistence layer

## 14. Configuration Strategy

Configuration is centralised through environment variables documented in `.env.example`.

This provides consistency across:

* local host execution
* Docker Compose execution
* future Kubernetes mapping

The naming strategy is intentionally generic so the same variables can later map to ConfigMaps and Secrets.

## 15. Scalability and Evolution

The initial platform is intentionally compact, but it is designed so that future evolution is reasonable.

Potential extensions include:

* splitting topics by domain
* adding dead-letter handling
* introducing a schema registry
* persisting raw events in ClickHouse or object storage
* supporting multiple streaming jobs
* running Spark on Kubernetes
* adding alerting rules in Grafana
* introducing Helm charts for deployment

The current architecture does not block these paths.

## 16. Risks and Tradeoffs

### 16.1 Single Topic Tradeoff

Using one raw topic simplifies the system but reduces domain isolation.

This is acceptable in the first phase because architectural clarity and delivery speed matter more than early topic proliferation.

### 16.2 JSON Without Registry

Using JSON without a schema registry is simpler and easier to inspect locally, but it reduces central contract enforcement.

This is acceptable for the first version because the project still maintains schema discipline through shared contract files and typed producer models.

### 16.3 Practical Delivery Guarantees

The platform does not claim strict end-to-end exactly-once guarantees.

This is a deliberate tradeoff to keep the project honest, understandable, and locally runnable.

### 16.4 Stateful Services in Local Containers

Kafka and ClickHouse are stateful systems, and local container orchestration always has some fragility.

That is acceptable here because the primary project objective is a reproducible engineering demo, not a hardened production cluster.

## 17. Engineering Principles

This project follows the following implementation rules:

* architecture before implementation
* one file per step
* complete files only
* strong naming consistency
* explicit configuration
* production-minded boundaries
* local reproducibility first
* Kubernetes as an extension, not a prerequisite

## 18. Current Design Baseline

The architecture baseline for implementation is:

* broker: Apache Kafka
* processor: Spark Structured Streaming
* producer: Python
* sink: ClickHouse
* dashboards: Grafana
* primary deployment: Docker Compose
* future extension: Kubernetes
* initial topic: `events.raw`
* initial sink table: `metrics_realtime_1m`

All future implementation files are expected to remain consistent with this baseline unless an intentional architecture revision is made.
