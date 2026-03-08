CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.metrics_realtime_1m
(
    window_start DateTime,
    window_end DateTime,
    metric_name LowCardinality(String),
    metric_value Float64,
    dimension_key LowCardinality(String),
    dimension_value String,
    processed_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toDate(window_start)
ORDER BY (metric_name, window_start, dimension_key, dimension_value)
SETTINGS index_granularity = 8192;