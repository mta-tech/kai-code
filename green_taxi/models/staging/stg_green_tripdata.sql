with source as (
    select * from read_parquet('../green_tripdata_2023-05.parquet')
),

renamed as (
    select
        VendorID as vendor_id,
        lpep_pickup_datetime as pickup_datetime,
        lpep_dropoff_datetime as dropoff_datetime,
        store_and_fwd_flag,
        RatecodeID as rate_code_id,
        PULocationID as pickup_location_id,
        DOLocationID as dropoff_location_id,
        passenger_count,
        trip_distance,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        ehail_fee,
        improvement_surcharge,
        total_amount,
        payment_type,
        trip_type,
        congestion_surcharge
    from source
)

select * from renamed
