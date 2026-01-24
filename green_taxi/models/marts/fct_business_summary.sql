with trip_data as (
    select * from {{ ref('stg_green_tripdata') }}
)

select
    count(*) as total_trips,
    sum(total_amount) as total_revenue,
    sum(passenger_count) as total_passengers,
    avg(trip_distance) as avg_trip_distance,
    avg(tip_amount) as avg_tip_amount
from trip_data