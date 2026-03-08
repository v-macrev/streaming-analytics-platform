# Event Model

## 1. Purpose

This document defines the event model used by the Streaming Analytics Platform.

The platform ingests synthetic business events into Kafka and processes them through Spark Structured Streaming to produce real-time analytical metrics. To make that pipeline coherent, all emitted events must follow a shared canonical structure.

This document describes:

- the canonical event envelope
- supported event types
- payload semantics
- identifier conventions
- timestamp rules
- modelling guidelines for future extension

It is the human-readable companion to the JSON schema located at:

`shared/event_contract/event_schema.json`

## 2. Design Goals

The event model is designed to satisfy the following goals:

- maintain a consistent event envelope across domains
- allow multiple business event types to share one Kafka topic
- support streaming-friendly parsing in Spark
- preserve enough semantics to generate meaningful analytical metrics
- stay simple enough for local portfolio-scale delivery

The event model is intentionally practical rather than enterprise-maximalist. It favors clear structure, stable naming, and compatibility with a single-topic streaming architecture.

## 3. Topic Context

All events are currently published to the Kafka topic:

- `events.raw`

Because this topic contains multiple event types, each event must include:

- a canonical envelope
- an `event_type` field
- a domain-specific `payload`

This allows the streaming job to branch processing logic while keeping the ingestion topology simple.

## 4. Canonical Event Envelope

All events emitted into `events.raw` follow the same top-level structure.

### 4.1 Envelope Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `event_id` | string | Yes | Globally unique identifier for the event |
| `event_type` | string | Yes | Logical event category used to interpret the payload |
| `event_time` | string (ISO 8601) | Yes | Business event timestamp in UTC |
| `producer_time` | string (ISO 8601) | Yes | Timestamp when the producer emitted the event in UTC |
| `user_id` | string | Yes | Logical user identifier associated with the event |
| `session_id` | string | Yes | Logical session identifier associated with the event |
| `source` | string | Yes | Producer source name or channel |
| `payload` | object | Yes | Event-type-specific payload |

### 4.2 Example Envelope

```json
{
  "event_id": "7f5a1d3d-9504-4db8-86ac-5c0cb120ccf2",
  "event_type": "order_created",
  "event_time": "2026-03-07T18:14:02+00:00",
  "producer_time": "2026-03-07T18:14:03+00:00",
  "user_id": "4821",
  "session_id": "sess_4fe1a0f61aa2",
  "source": "web-simulator",
  "payload": {
    "order_id": "ord_c3f3f07a2d51",
    "items_count": 3,
    "total_amount": 249.90,
    "currency": "BRL",
    "channel": "web"
  }
}
````

## 5. Timestamp Semantics

### 5.1 `event_time`

`event_time` represents when the business event logically happened.

This is the primary time field used by the streaming job for:

* event-time windowing
* watermarking
* metric aggregation by minute

### 5.2 `producer_time`

`producer_time` represents when the event was actually emitted by the producer.

This field is useful for:

* producer diagnostics
* lag inspection
* comparing event occurrence time vs publication time

### 5.3 Timezone Rule

All timestamps must be expressed in **UTC** and serialized as ISO 8601 date-time strings.

This keeps parsing predictable across:

* producer logic
* Spark transformations
* ClickHouse storage
* Grafana visualisation

## 6. Identifier Conventions

The platform uses string identifiers throughout the event model.

### 6.1 Why Strings

Identifiers are modeled as strings because they are more flexible than integers for distributed event systems. They support prefixes, source-specific patterns, and future evolution without changing the contract shape.

### 6.2 Current Identifier Patterns

The current synthetic producer uses patterns such as:

* `session_id`: `sess_<random>`
* `order_id`: `ord_<random>`
* `payment_id`: `pay_<random>`
* `product_id`: `prd_<code>`
* `warehouse_id`: `wh_<nn>`

These patterns are implementation details, but they are useful for readability and debugging.

## 7. Supported Event Types

The initial version of the platform supports the following event types:

* `page_view`
* `add_to_cart`
* `order_created`
* `payment_processed`
* `inventory_updated`

These event types were selected to cover:

* user browsing activity
* pre-conversion activity
* commerce transactions
* payment outcomes
* operational stock movement

Together, they provide enough business context to compute meaningful real-time metrics.

---

## 8. Event Type: `page_view`

### 8.1 Purpose

Represents a user viewing a product-related page or screen.

This event is mainly used to simulate activity volume and user engagement.

### 8.2 Payload Fields

| Field        | Type   | Required | Description                                                     |
| ------------ | ------ | -------: | --------------------------------------------------------------- |
| `page`       | string |      Yes | Logical page or route viewed by the user                        |
| `product_id` | string |      Yes | Product identifier associated with the view                     |
| `category`   | string |      Yes | Product category associated with the viewed item                |
| `referrer`   | string |       No | Traffic source or referrer; defaults to `direct` when generated |

### 8.3 Example

```json
{
  "page": "/product",
  "product_id": "prd_1001",
  "category": "electronics",
  "referrer": "google"
}
```

---

## 9. Event Type: `add_to_cart`

### 9.1 Purpose

Represents a user adding a product to cart.

This event acts as a pre-purchase intent signal and can be used later for funnel-style metrics.

### 9.2 Payload Fields

| Field        | Type    | Required | Description                                |
| ------------ | ------- | -------: | ------------------------------------------ |
| `product_id` | string  |      Yes | Identifier of the product added to cart    |
| `quantity`   | integer |      Yes | Number of units added                      |
| `unit_price` | number  |      Yes | Unit price at the time of add-to-cart      |
| `currency`   | string  |       No | Currency code; currently defaults to `BRL` |

### 9.3 Example

```json
{
  "product_id": "prd_1002",
  "quantity": 2,
  "unit_price": 79.90,
  "currency": "BRL"
}
```

---

## 10. Event Type: `order_created`

### 10.1 Purpose

Represents a commerce order being created.

This event is used to derive:

* revenue per minute
* orders per minute

In the current platform, `order_created.total_amount` is the source for the revenue metric.

### 10.2 Payload Fields

| Field          | Type    | Required | Description                                               |
| -------------- | ------- | -------: | --------------------------------------------------------- |
| `order_id`     | string  |      Yes | Logical order identifier                                  |
| `items_count`  | integer |      Yes | Number of items in the order                              |
| `total_amount` | number  |      Yes | Total order value                                         |
| `currency`     | string  |      Yes | Currency code for the order value                         |
| `channel`      | string  |       No | Commercial or source channel; currently defaults to `web` |

### 10.3 Example

```json
{
  "order_id": "ord_7f9f14dbac11",
  "items_count": 3,
  "total_amount": 249.90,
  "currency": "BRL",
  "channel": "web"
}
```

---

## 11. Event Type: `payment_processed`

### 11.1 Purpose

Represents the outcome of a payment attempt associated with an order.

This event is used to derive:

* payment success rate

It is intentionally separated from `order_created` so the platform can model operational payment health as a distinct stream concept.

### 11.2 Payload Fields

| Field            | Type   | Required | Description                                |
| ---------------- | ------ | -------: | ------------------------------------------ |
| `payment_id`     | string |      Yes | Logical payment identifier                 |
| `order_id`       | string |      Yes | Order identifier linked to the payment     |
| `payment_method` | string |      Yes | Payment method used                        |
| `payment_status` | string |      Yes | Payment outcome status                     |
| `amount`         | number |      Yes | Amount processed                           |
| `currency`       | string |       No | Currency code; currently defaults to `BRL` |

### 11.3 Allowed Values

#### `payment_method`

* `credit_card`
* `pix`
* `debit_card`
* `wallet`
* `boleto`

#### `payment_status`

* `approved`
* `declined`
* `pending`

### 11.4 Example

```json
{
  "payment_id": "pay_204fa4714cfe",
  "order_id": "ord_7f9f14dbac11",
  "payment_method": "pix",
  "payment_status": "approved",
  "amount": 249.90,
  "currency": "BRL"
}
```

---

## 12. Event Type: `inventory_updated`

### 12.1 Purpose

Represents a stock change for a product in a warehouse or fulfilment location.

This event is used to derive:

* low-stock signal counts

It also gives the stream some operational flavour beyond pure clickstream and orders.

### 12.2 Payload Fields

| Field          | Type    | Required | Description                                 |
| -------------- | ------- | -------: | ------------------------------------------- |
| `product_id`   | string  |      Yes | Product whose inventory changed             |
| `warehouse_id` | string  |      Yes | Warehouse or fulfilment location identifier |
| `delta_qty`    | integer |      Yes | Signed quantity change applied to stock     |
| `stock_after`  | integer |      Yes | Resulting inventory level after the change  |
| `reason`       | string  |       No | Business reason for the stock change        |

### 12.3 Allowed Values

#### `reason`

* `sale`
* `restock`
* `adjustment`
* `return`

### 12.4 Example

```json
{
  "product_id": "prd_1007",
  "warehouse_id": "wh_02",
  "delta_qty": -3,
  "stock_after": 8,
  "reason": "sale"
}
```

---

## 13. Field Usage in Streaming Metrics

The streaming job currently uses event fields as follows:

| Metric                         | Source Event Type   | Key Fields                     |
| ------------------------------ | ------------------- | ------------------------------ |
| `events_per_minute`            | all events          | `event_type`, `event_time`     |
| `revenue_per_minute`           | `order_created`     | `total_amount`, `event_time`   |
| `orders_per_minute`            | `order_created`     | `order_id`, `event_time`       |
| `payment_success_rate`         | `payment_processed` | `payment_status`, `event_time` |
| `active_users_per_minute`      | all events          | `user_id`, `event_time`        |
| `low_stock_signals_per_minute` | `inventory_updated` | `stock_after`, `event_time`    |

This mapping is important because it makes the event model directly traceable to the analytics outputs in ClickHouse and Grafana.

## 14. Modelling Rules

All future event types added to the platform should follow these rules.

### 14.1 Preserve the Canonical Envelope

Do not introduce a different top-level structure for new event types.

### 14.2 Keep `event_type` Stable and Explicit

Every event must have a stable `event_type` string with a single clear meaning.

### 14.3 Use Domain Payloads, Not Top-Level Field Sprawl

Domain-specific attributes belong in `payload`, not in ad hoc top-level fields.

### 14.4 Use UTC ISO 8601 Timestamps

Do not emit local-time strings or inconsistent timestamp formats.

### 14.5 Prefer String Identifiers

IDs should remain strings unless there is a compelling architectural reason otherwise.

### 14.6 Evolve by Extension, Not Breakage

Adding nullable payload fields is acceptable. Renaming or repurposing existing fields should be treated as a breaking contract change.

## 15. Current Limitations

The current event model intentionally has a few limitations:

* no schema registry
* no explicit event version field
* no dead-letter routing metadata
* no partitioning key documented as a formal contract field
* no guarantee that synthetic business relationships fully mirror real production systems

These are acceptable limitations for the current scope. The goal is a credible streaming analytics platform, not a cathedral of speculative infrastructure.

## 16. Summary

The Streaming Analytics Platform uses a canonical event envelope with typed domain payloads to support a multi-event streaming architecture over a single Kafka topic.

This model provides:

* consistent ingestion semantics
* readable domain boundaries
* compatibility with Spark parsing
* direct traceability to analytical metrics

It is intentionally compact, explicit, and practical for a portfolio-grade real-time analytics system.