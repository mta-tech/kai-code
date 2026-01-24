"""Example usage of SeeknalAgent for data engineering and data science."""

from pathlib import Path
from kai_code.agents.seeknal import SeeknalAgent


def main():
    """Demonstrate SeeknalAgent usage."""
    # Initialize the agent
    agent = SeeknalAgent(
        root_dir=Path.cwd(),
        seeknal_path=Path.home() / "project" / "mta" / "signal",
        yolo=True,  # Auto-approve actions
    )

    # Example 1: Create a new project
    print("Example 1: Creating a new project...")
    result = agent.run(
        "Create a new Seeknal project named 'ml_features' with description "
        "'ML feature store for customer analytics'"
    )
    print(result.output)
    print()

    # Example 2: Create an entity
    print("Example 2: Creating an entity...")
    result = agent.run(
        "Create an entity named 'customer' with join keys 'customer_id'"
    )
    print(result.output)
    print()

    # Example 3: Create a feature group
    print("Example 3: Creating a feature group...")
    result = agent.run(
        "Create a feature group named 'customer_features' with entity 'customer', "
        "using event_time_col 'created_at', in project 'ml_features'"
    )
    print(result.output)
    print()

    # Example 4: Create a data pipeline
    print("Example 4: Creating a data pipeline...")
    result = agent.run(
        "Create a flow named 'transform_customer_data' that reads from PARQUET file "
        "'data/customers.parquet' and runs a DuckDB task to select customer_id, "
        "count(*) as purchase_count from the data"
    )
    print(result.output)
    print()

    # Example 5: Validate SQL identifiers
    print("Example 5: Validating SQL identifiers...")
    result = agent.run(
        "Validate the SQL identifier 'customer_features' and table name 'raw.customers'"
    )
    print(result.output)
    print()

    # Example 6: List versions
    print("Example 6: Listing feature group versions...")
    result = agent.run(
        "List all versions of the feature group 'customer_features'"
    )
    print(result.output)
    print()

    # Save session
    agent.save()
    print("Session saved!")


if __name__ == "__main__":
    main()
