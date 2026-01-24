with trip_data as (
    select * from {{ ref('int_trip_data') }}
)

select
    -- 1. Average Trip Duration
    avg(trip_duration_minutes) as avg_trip_duration_minutes,
    
    -- 2. Average Fare per Mile
    avg(case when trip_distance > 0 then fare_amount / trip_distance else null end) as avg_fare_per_mile,
    
    -- 3. Total Tip Amount
    sum(tip_amount) as total_tip_amount,
    
    -- 4. Average Tip Percentage (of fare)
    avg(case when fare_amount > 0 then (tip_amount / fare_amount) * 100 else 0 end) as avg_tip_percentage,
    
    -- 5. Percentage of Credit Card Payments (Type 1)
    (count(case when payment_type = 1 then 1 end) * 100.0 / count(*)) as pct_credit_card_payments
from trip_data