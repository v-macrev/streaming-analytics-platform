# Streaming Analytics Platform

A production-grade real-time analytics platform for ingesting, processing, aggregating, and visualising live event streams using Kafka, Spark Structured Streaming, ClickHouse, and Grafana.

## Overview

This project simulates a modern event-driven analytics system used by digital platforms to process operational data in near real time.

The platform ingests business events such as page views, cart interactions, orders, payments, and inventory updates, processes them through a streaming pipeline, computes analytical metrics continuously, stores the results in ClickHouse, and exposes them through Grafana dashboards.

The goal is to provide a portfolio-grade implementation of a real-world streaming architecture with strong engineering discipline, reproducible local deployment, and clear architectural boundaries.

## Business Problem

Modern digital systems cannot rely exclusively on batch analytics for operational visibility.

Teams need near-real-time answers to questions such as:

- How much revenue are we generating per minute?
- Are payments succeeding or failing right now?
- Is user activity increasing or dropping?
- Are orders converting from cart activity?
- Are inventory levels approaching operational risk?

This platform addresses that need by transforming raw event streams into continuously updated analytical metrics.

## Primary Use Cases

The system is designed to support use cases such as:

- product activity monitoring
- commerce operations tracking
- payment health monitoring
- inventory signal analysis
- streaming architecture demonstration for portfolio and resume purposes

## Core Capabilities

- Event generation for multiple business domains
- Kafka-based event ingestion
- Spark Structured Streaming transformations and aggregations
- Windowed real-time metric computation
- ClickHouse analytical storage
- Grafana dashboard visualisation
- Local reproducible deployment with Docker Compose
- Planned Kubernetes deployment extension

## High-Level Architecture

```text
+------------------+        +------------------+        +-----------------------------+
| Event Producer   | -----> | Kafka            | -----> | Spark Structured Streaming  |
| (Python)         |        | Topic: events.raw|        | Aggregation Job             |
+------------------+        +------------------+        +-----------------------------+
                                                               |
                                                               v
                                                     +------------------+
                                                     | ClickHouse       |
                                                     | Metrics Tables   |
                                                     +------------------+
                                                               |
                                                               v
                                                     +------------------+
                                                     | Grafana          |
                                                     | Dashboards       |
                                                     +------------------+
````

## Event Flow

1. The producer service emits synthetic business events.
2. Events are published to Kafka topic `events.raw`.
3. Spark Structured Streaming consumes and parses the event stream.
4. The streaming job computes near-real-time aggregations using event-time windows.
5. Aggregated metrics are written to ClickHouse.
6. Grafana queries ClickHouse and renders operational dashboards.

## Event Domains

The platform will simulate events from multiple domains:

* `page_view`
* `add_to_cart`
* `order_created`
* `payment_processed`
* `inventory_updated`

All events will share a canonical envelope and carry domain-specific payloads.

## Initial Real-Time Metrics

The first version of the platform is expected to expose metrics such as:

* revenue per minute
* orders per minute
* payment success rate
* event throughput by type
* active users per minute
* low-stock inventory signal count

These metrics are intentionally chosen to demonstrate practical streaming analytics rather than generic message movement.

## Technology Stack

### Broker

**Apache Kafka**

Kafka is used as the event broker because it is the industry-standard platform for event streaming and provides strong resume and architectural relevance.

### Stream Processing

**Spark Structured Streaming**

Spark Structured Streaming was chosen because it is highly relevant in data engineering environments, integrates well with Python, and provides a practical path for implementing real-time aggregations locally.

### Producer Runtime

**Python**

Python is used for the event producer because it supports fast iteration, clear modelling, and aligns well with the rest of the platform.

### Analytical Store

**ClickHouse**

ClickHouse is used for low-latency analytical querying over continuously updated metrics.

### Dashboarding

**Grafana**

Grafana is used to visualise operational analytics in real time.

### Orchestration

**Docker Compose**

Docker Compose is the primary deployment mechanism for the first delivery phase because it provides local reproducibility with minimal operational overhead.

### Planned Extension

**Kubernetes**

Kubernetes is planned as a future deployment extension after the full end-to-end platform is working in Docker Compose.

## Why Docker Compose First

This project is intentionally structured to deliver a working real-time analytics product before introducing orchestration complexity.

Starting with Docker Compose provides:

* faster end-to-end validation
* lower setup friction for reviewers
* easier local reproducibility
* clearer debugging of service interactions

Kubernetes will be added later as an infrastructure extension rather than as the initial operational dependency.

That sequencing is deliberate: first prove the streaming system works, then prove it can be orchestrated in a more production-shaped environment.

## Repository Structure

```text
streaming-analytics-platform/
├── README.md
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   └── event-model.md
├── producer/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── config.py
│       ├── main.py
│       ├── generator.py
│       ├── models.py
│       └── kafka_producer.py
├── streaming/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── config.py
│       ├── main.py
│       ├── schemas.py
│       ├── transformations.py
│       └── clickhouse_sink.py
├── infra/
│   ├── kafka/
│   ├── clickhouse/
│   │   └── init/
│   │       └── 001_init_metrics.sql
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── clickhouse.yml
│       │   └── dashboards/
│       │       └── dashboards.yml
│       └── dashboards/
│           └── realtime-overview.json
├── shared/
│   └── event_contract/
│       └── event_schema.json
├── scripts/
│   ├── run_producer.sh
│   └── run_streaming.sh
└── k8s/
    └── README.md
```

## Planned Components

### 1. Producer Service

A Python service that continuously generates realistic synthetic events and publishes them to Kafka.

### 2. Kafka

The central event broker responsible for durable event ingestion and decoupling producers from consumers.

### 3. Streaming Job

A Spark Structured Streaming application that reads from Kafka, validates and transforms events, computes windowed metrics, and writes results to ClickHouse.

### 4. ClickHouse

The analytical store used to persist streaming aggregates for fast dashboard queries.

### 5. Grafana

The dashboard layer used to visualise operational metrics.

### 6. Kubernetes Extension

A later deployment track that will package the system for Kubernetes-based execution.

## Data Contract Strategy

The platform will use a shared event contract with a canonical event envelope.

Expected top-level fields include:

* `event_id`
* `event_type`
* `event_time`
* `producer_time`
* `user_id`
* `session_id`
* `source`
* `payload`

This gives the pipeline a consistent ingestion shape while allowing domain-specific event payloads.

## Topic Strategy

The initial topic design is intentionally simple:

* `events.raw`

A single raw topic reduces complexity during the first implementation phase and keeps stream processing logic focused.

If needed, the project can later evolve toward topic-per-domain patterns.

## Metric Storage Strategy

The initial storage approach will prioritise aggregated metrics over raw event persistence.

The first sink design will focus on a real-time metrics table in ClickHouse to support dashboard queries efficiently.

This keeps the project aligned with its analytics objective and avoids unnecessary operational sprawl in the early phase.

## Deployment Modes

### Mode 1 — Local Development and Demo

**Docker Compose**

This is the primary way to run the platform locally.

### Mode 2 — Orchestration Extension

**Kubernetes**

This will be introduced after the Compose-based platform is complete and validated end to end.

## Implementation Principles

The project is being built under the following engineering rules:

* architecture first
* one file per step
* complete files only
* consistent naming and contracts
* production-minded structure
* reproducible local delivery
* commit discipline at logical boundaries

## Planned Implementation Sequence

1. `README.md`
2. `docker-compose.yml`
3. `.env.example`
4. `docs/architecture.md`
5. `shared/event_contract/event_schema.json`
6. `producer/requirements.txt`
7. `producer/src/config.py`
8. `producer/src/models.py`
9. `producer/src/generator.py`
10. `producer/src/kafka_producer.py`
11. `producer/src/main.py`
12. `producer/Dockerfile`
13. `streaming/requirements.txt`
14. `streaming/src/config.py`
15. `streaming/src/schemas.py`
16. `streaming/src/transformations.py`
17. `streaming/src/clickhouse_sink.py`
18. `streaming/src/main.py`
19. `streaming/Dockerfile`
20. `infra/clickhouse/init/001_init_metrics.sql`
21. `infra/grafana/provisioning/datasources/clickhouse.yml`
22. `infra/grafana/provisioning/dashboards/dashboards.yml`
23. `infra/grafana/dashboards/realtime-overview.json`
24. `docs/event-model.md`
25. `scripts/run_producer.sh`
26. `scripts/run_streaming.sh`
27. `k8s/README.md`

## Expected Outcome

When complete, this repository should demonstrate:

* event-driven architecture understanding
* Kafka-based ingestion design
* practical streaming analytics implementation
* real-time aggregation patterns
* ClickHouse analytical modelling
* operational dashboard integration
* local reproducibility
* extensibility toward Kubernetes deployment

## Status

This repository is currently under incremental implementation.

The architecture and delivery plan are defined first, and the project is built one production-ready file at a time.
