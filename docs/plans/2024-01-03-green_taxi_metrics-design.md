# Green Taxi Trip Metrics Design Document

**Date**: 2024-01-03
**Status**: Draft
**Author**: Brainstorming session

---

## Overview

This document outlines the design for a dbt project that extracts and transforms green taxi trip data from a Parquet file to generate monthly metrics. These metrics will provide insights into general trends in green taxi usage, focusing on trip duration, distance, pickup/dropoff locations, payment types, fares, and time of day.

## Problem Statement

The existing green taxi trip data is stored in a raw Parquet file, making it difficult to directly analyze and derive meaningful insights. There is a need to transform this data into an aggregated and structured format that enables efficient analysis of key trends and patterns in green taxi usage, particularly identifying areas with high demand.

## Goals & Non-Goals

**Goals:**

- Create a dbt project that transforms the raw Parquet data into monthly aggregated metrics.
- Calculate metrics for trip duration, distance, pickup/dropoff locations (aggregated by zone), payment types, and fares.
- Identify the busiest pickup and dropoff zones on a monthly basis.
- Provide a clear and well-documented data pipeline for future analysis.

**Non-Goals:**

- Real-time data processing or analysis.
- Integration with external data sources beyond the provided Parquet file.
- Building a user interface for visualizing the metrics.
- Predicting future demand or trends.

## Design

### Architecture

The dbt project will follow a standard three-layer architecture:

- **Staging:** This layer will load the raw Parquet data and perform minimal transformations, such as renaming columns and casting data types.
- **Intermediate:** This layer will perform more complex transformations, such as calculating trip duration and joining with zone lookup tables to map coordinates to zones.
- **Marts:** This layer will aggregate the data to calculate monthly metrics, such as total trips per zone, average fare, and average trip duration.

The data will flow from the Parquet file through these three layers, with each layer building upon the previous one.

### Components

1.  **Staging Model (`stg_green_tripdata`):** This model will load the `green_tripdata_2023-05.parquet` file. It will perform the following transformations:

    *   Rename columns for consistency (e.g., `lpep_pickup_datetime` to `pickup_datetime`).
    *   Cast data types as needed (e.g., convert string IDs to integers).
    *   Select only the necessary columns for downstream analysis.

2.  **Intermediate Model (`int_trip_data`):** This model will build upon the staging model and perform more complex transformations:

    *   Calculate trip duration in minutes.
    *   Join pickup and dropoff location IDs with a zone lookup table. If a zone lookup table doesn't exist in the project, we will use a web API to reverse geocode the lat/lon coordinates and map them to neighborhoods/zones, storing this information in a new table.
    *   Extract the hour of day and day of week from the pickup datetime.

3.  **Marts Model (`fct_monthly_trip_metrics`):** This model will aggregate the data from the intermediate model to calculate monthly metrics:

    *   Total number of trips per pickup zone.
    *   Total number of trips per dropoff zone.
    *   Average trip duration.
    *   Average fare amount.
    *   Distribution of payment types.

### Data Flow

1.  The `stg_green_tripdata` model loads data from the `green_tripdata_2023-05.parquet` file.
2.  The `int_trip_data` model transforms the staged data, calculating trip duration and joining with the zone lookup table (either existing or created via web API).
3.  The `fct_monthly_trip_metrics` model aggregates the transformed data to generate monthly metrics for each zone.
4.  The final metrics can then be queried and analyzed to identify trends in green taxi usage.

## Implementation Plan

1.  **Create dbt project:** Initialize a new dbt project in the repository.
2.  **Configure dbt:** Configure dbt to connect to a suitable data warehouse (e.g., DuckDB, Snowflake, BigQuery).
3.  **Implement staging model:** Create the `stg_green_tripdata` model to load and stage the data from the Parquet file.
4.  **Implement zone lookup:**
    *   Check for existing zone lookup table.
    *   If it doesn't exist, implement a Python script (or dbt macro) to call a reverse geocoding API (e.g., Google Maps, Nominatim) and create a new zone lookup table.
5.  **Implement intermediate model:** Create the `int_trip_data` model to calculate trip duration and join with the zone lookup table.
6.  **Implement marts model:** Create the `fct_monthly_trip_metrics` model to aggregate the data and calculate monthly metrics.
7.  **Test the models:** Write dbt tests to ensure the data transformations are correct and the metrics are accurate.

## Testing Strategy

1.  **Data Quality Tests:** Implement dbt tests to ensure data quality, such as:
    *   Checking for null values in required columns.
    *   Verifying data type constraints.
    *   Ensuring trip durations are within a reasonable range.
2.  **Accuracy Tests:** Implement tests to verify the accuracy of the calculated metrics, such as:
    *   Comparing the total number of trips to a known value.
    *   Checking the distribution of payment types against expected proportions.
3.  **Uniqueness Tests:** Implement tests to ensure uniqueness of primary keys.
4.  **Relationship Tests:** Implement tests to verify relationships between tables (e.g., that `zone_id` in `int_trip_data` exists in the zone lookup table).

## Open Questions

1. What specific reverse geocoding API should be used for the zone lookup (if needed)?
2. What level of detail is required for the zone definitions (e.g., neighborhood, borough, zip code)?
3. What is the best way to handle missing or invalid location data?
