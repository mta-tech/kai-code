"""Schema introspection tools for DbtAgent."""
from __future__ import annotations

import fnmatch
import json
import re
from typing import Any

from langchain_core.tools import tool

from kai_code.agents.dbt.adapters.base import DatabaseAdapter


def create_schema_tools(adapter: DatabaseAdapter) -> list:
    """Create schema introspection tools bound to an adapter.

    Args:
        adapter: Database adapter instance.

    Returns:
        List of LangChain tools.
    """

    @tool("get_database_schema")
    def get_database_schema(include_samples: bool = False) -> str:
        """Get the complete database schema including all tables, columns, and descriptions.

        IMPORTANT: Call this tool FIRST before writing any SQL queries to understand
        the available tables, columns, data types, and relationships.

        Args:
            include_samples: If True, include sample data rows for each table.

        Returns:
            JSON string with complete database schema information.
        """
        try:
            tables = adapter.get_tables()

            if not tables:
                return json.dumps(
                    {"success": False, "error": "No tables found in database."}
                )

            schema_info: dict[str, Any] = {
                "success": True,
                "tables": [],
                "filterable_columns": [],
            }

            for table in tables:
                columns = adapter.get_columns(table.name)

                table_info: dict[str, Any] = {
                    "name": table.name,
                    "schema": table.schema,
                    "full_name": table.full_name,
                    "description": table.description,
                    "row_count": table.row_count,
                    "columns": [],
                }

                for col in columns:
                    col_info: dict[str, Any] = {
                        "name": col.name,
                        "type": col.data_type,
                        "description": col.description,
                    }

                    if col.is_primary_key:
                        col_info["primary_key"] = True

                    if col.foreign_key:
                        col_info["foreign_key"] = {
                            "references_table": col.foreign_key.reference_table,
                            "references_column": col.foreign_key.reference_column,
                        }

                    if col.is_low_cardinality and col.categories:
                        col_info["filterable"] = True
                        col_info["allowed_values"] = col.categories

                        schema_info["filterable_columns"].append(
                            {
                                "table": table.full_name,
                                "column": col.name,
                                "values": col.categories,
                            }
                        )

                    table_info["columns"].append(col_info)

                schema_info["tables"].append(table_info)

            schema_info["summary"] = {
                "total_tables": len(tables),
                "table_names": [t.name for t in tables],
            }

            return json.dumps(schema_info, indent=2, default=str)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool("get_table_details")
    def get_table_details(table_name: str) -> str:
        """Get detailed information about a specific table.

        Args:
            table_name: Name of the table (e.g., 'users' or 'public.users').

        Returns:
            JSON string with table details including columns and sample data.
        """
        try:
            tables = adapter.get_tables()

            target = None
            for t in tables:
                if t.name == table_name or t.full_name == table_name:
                    target = t
                    break

            if not target:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Table '{table_name}' not found",
                        "available_tables": [t.name for t in tables],
                    }
                )

            columns = adapter.get_columns(target.name)

            # Get sample data
            result = adapter.execute_query(f'SELECT * FROM "{target.name}" LIMIT 5')

            return json.dumps(
                {
                    "success": True,
                    "table": {
                        "name": target.name,
                        "schema": target.schema,
                        "full_name": target.full_name,
                        "description": target.description,
                        "row_count": target.row_count,
                        "columns": [
                            {
                                "name": c.name,
                                "type": c.data_type,
                                "description": c.description,
                                "is_primary_key": c.is_primary_key,
                                "is_nullable": c.is_nullable,
                            }
                            for c in columns
                        ],
                        "sample_data": result.rows if result.success else [],
                    },
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool("get_column_cardinality")
    def get_column_cardinality(table_name: str, column_name: str) -> str:
        """Get distinct value count and samples for a column.

        Args:
            table_name: Table name.
            column_name: Column name.

        Returns:
            JSON with cardinality info and sample values.
        """
        try:
            card = adapter.get_cardinality(table_name, column_name)

            return json.dumps(
                {
                    "success": True,
                    "table": card.table,
                    "column": card.column,
                    "distinct_count": card.distinct_count,
                    "total_count": card.total_count,
                    "is_low_cardinality": card.is_low_cardinality,
                    "sample_values": card.sample_values,
                },
                indent=2,
                default=str,
            )

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @tool("search_schema")
    def search_schema(
        pattern: str,
        search_in: str = "all",
    ) -> str:
        """Search tables and columns using patterns.

        Supports wildcards: '*' matches any characters, '?' matches single character.

        Args:
            pattern: Search pattern (e.g., '*customer*', 'order_*').
            search_in: Where to search - 'tables', 'columns', or 'all'.

        Returns:
            JSON with matching tables and columns.
        """
        try:
            tables = adapter.get_tables()

            # Convert glob pattern to regex
            if "*" not in pattern and "?" not in pattern:
                regex_pattern = f".*{re.escape(pattern)}.*"
            else:
                regex_pattern = fnmatch.translate(pattern).replace(r"\Z", "")

            compiled = re.compile(regex_pattern, re.IGNORECASE)

            matches: dict[str, list] = {
                "tables": [],
                "columns": [],
            }

            for table in tables:
                # Search table names
                if search_in in ("all", "tables"):
                    if compiled.search(table.name):
                        matches["tables"].append(
                            {
                                "name": table.name,
                                "full_name": table.full_name,
                                "description": table.description,
                            }
                        )

                # Search columns
                if search_in in ("all", "columns"):
                    columns = adapter.get_columns(table.name)
                    for col in columns:
                        if compiled.search(col.name):
                            matches["columns"].append(
                                {
                                    "table": table.full_name,
                                    "column": col.name,
                                    "type": col.data_type,
                                }
                            )

            return json.dumps(
                {
                    "success": True,
                    "pattern": pattern,
                    "total_matches": len(matches["tables"]) + len(matches["columns"]),
                    "matches": matches,
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    return [
        get_database_schema,
        get_table_details,
        get_column_cardinality,
        search_schema,
    ]
