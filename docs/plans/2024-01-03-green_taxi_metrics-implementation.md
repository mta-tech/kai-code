# Green Taxi Trip Metrics Implementation Plan

**Date**: 2024-01-03
**Status**: To Do

---

## 1. Set up dbt project

- [ ] 1.1. Create a new dbt project using `dbt init`.
- [ ] 1.2. Configure dbt to connect to a suitable data warehouse (e.g., DuckDB).
- [ ] 1.3. Create a dbt profile.
- [ ] 1.4. Verify the dbt setup using `dbt debug`.

## 2. Implement staging model

- [ ] 2.1. Create a new staging model `stg_green_tripdata` in the `models/staging` directory.
- [ ] 2.2. Configure the model to load data from the `green_tripdata_2023-05.parquet` file.
- [ ] 2.3. Rename columns for consistency (e.g., `lpep_pickup_datetime` to `pickup_datetime`).
- [ ] 2.4. Cast data types as needed (e.g., convert string IDs to integers).
- [ ] 2.5. Select only the necessary columns for downstream analysis.
- [ ] 2.6. Add data quality tests (e.g., not null, data type) to the staging model.

## 3. Implement zone lookup

- [ ] 3.1. Check for an existing zone lookup table in the project.
- [ ] 3.2. If a zone lookup table exists, document its structure and usage.
- [ ] 3.3. If a zone lookup table does not exist, implement a Python script (or dbt macro) to call a reverse geocoding API (e.g., Google Maps, Nominatim) and create a new zone lookup table.
- [ ] 3.4. Store the zone lookup table in the data warehouse.

## 4. Implement intermediate model

- [ ] 4.1. Create a new intermediate model `int_trip_data` in the `models/intermediate` directory.
- [ ] 4.2. Configure the model to use the staging model (`stg_green_tripdata`) as its source.
- [ ] 4.3. Calculate trip duration in minutes.
- [ ] 4.4. Join pickup and dropoff location IDs with the zone lookup table.
- [ ] 4.5. Extract the hour of day and day of week from the pickup datetime.

## 5. Implement marts model

- [ ] 5.1. Create a new marts model `fct_monthly_trip_metrics` in the `models/marts` directory.
- [ ] 5.2. Configure the model to use the intermediate model (`int_trip_data`) as its source.
- [ ] 5.3. Aggregate the data to calculate monthly metrics for each zone (total number of trips, average fare amount, average trip duration, distribution of payment types).

## 6. Test the models

- [ ] 6.1. Write dbt tests to ensure the data transformations are correct.
- [ ] 6.2. Write dbt tests to verify the accuracy of the calculated metrics.
- [ ] 6.3. Implement data quality tests (e.g., checking for null values, verifying data type constraints).
- [ ] 6.4. Implement accuracy tests (e.g., comparing the total number of trips to a known value).
- [ ] 6.5. Implement uniqueness tests (e.g., ensuring uniqueness of primary keys).
- [ ] 6.6. Implement relationship tests (e.g., verifying relationships between tables).
