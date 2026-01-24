with trips as (
    select * from {{ ref('stg_green_tripdata') }}
),

transformed as (
    select
        *,
        date_diff('minute', pickup_datetime, dropoff_datetime) as trip_duration_minutes,
        extract(hour from pickup_datetime) as pickup_hour,
        extract(dayofweek from pickup_datetime) as pickup_day_of_week
    from trips
)

select * from transformed
