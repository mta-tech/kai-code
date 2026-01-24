with trip_data as (
    select * from {{ ref('int_trip_data') }}
),

metrics as (
    select
        pickup_location_id,
        -- Metric 1: Trip Volume
        count(*) as total_trips,
        -- Metric 2: Gross Revenue
        sum(total_amount) as total_revenue,
        -- Metric 3: Average Trip Distance (Miles)
        avg(trip_distance) as avg_distance,
        -- Metric 4: Average Tip Percentage
        avg(case when fare_amount > 0 then (tip_amount / fare_amount) * 100 else 0 end) as avg_tip_percentage,
        -- Metric 5: Average Trip Duration (Minutes)
        avg(trip_duration_minutes) as avg_duration_minutes
    from trip_data
    group by 1
)

select * from metrics
