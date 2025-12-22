-- Example staging model following conventions

{{
    config(
        materialized='view',
        tags=['staging', 'daily']
    )
}}

WITH source AS (
    SELECT * FROM {{ source('ecommerce', 'orders') }}
),

cleaned AS (
    SELECT
        -- Primary key
        CAST(order_id AS INTEGER) AS order_id,

        -- Foreign keys
        CAST(customer_id AS INTEGER) AS customer_id,
        CAST(product_id AS INTEGER) AS product_id,

        -- Attributes
        TRIM(UPPER(status)) AS order_status,
        CAST(quantity AS INTEGER) AS quantity,
        CAST(unit_price AS DECIMAL(10, 2)) AS unit_price,
        CAST(discount AS DECIMAL(5, 2)) AS discount_amount,

        -- Calculated
        (quantity * unit_price) - COALESCE(discount, 0) AS line_total,

        -- Timestamps
        CAST(created_at AS TIMESTAMP) AS created_at,
        CAST(updated_at AS TIMESTAMP) AS updated_at

    FROM source
    WHERE order_id IS NOT NULL
)

SELECT * FROM cleaned
