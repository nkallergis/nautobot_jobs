import csv
from datetime import datetime
from io import StringIO
from pathlib import Path

from django.db import connection, transaction

from nautobot.apps.jobs import Job, register_jobs

ERD_FILENAME = "erd_export.sql"


class ERDExport(Job):
    """Export the Nautobot schema as a Lucidchart-compatible CSV.

    Includes Custom Fields and Custom Relationships alongside the core schema.
    """

    class Meta:
        """Job metadata."""

        name = "Export ERD (Lucidchart)"
        description = (
            "Exports the Nautobot database schema, including Custom Fields "
            "and Custom Relationships, as a Lucidchart-compatible CSV."
        )

    def read_sql(self, filename: str) -> str:
        """Locate and read a SQL file bundled with this Job.

        Args:
            filename: Name of the SQL file, relative to this module's directory.

        Returns:
            The contents of the SQL file.

        Raises:
            RuntimeError: If the file cannot be located or read.
        """
        sql_file = Path(__file__).parent / filename

        if not sql_file.exists():
            raise RuntimeError(f"Unable to locate SQL file: {sql_file}")

        try:
            return sql_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Unable to read SQL file '{sql_file}': {exc}") from exc

    def execute_query(self, sql: str) -> tuple[list[str], list[tuple]]:
        """Run the schema export query against the database.

        Runs inside a transaction because the SQL uses ``SET LOCAL`` to tune
        the query planner for the ``information_schema`` joins it performs.

        Args:
            sql: The SQL statement to execute.

        Returns:
            A tuple of ``(headers, rows)`` where ``headers`` is the list of
            column names and ``rows`` is the list of result tuples.

        Raises:
            RuntimeError: If the database query fails.
        """
        self.logger.info("Executing schema export query...")

        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(sql)
                headers = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
        except Exception as exc:
            raise RuntimeError(f"Database query failed:\n{exc}") from exc

        self.logger.info("Retrieved %d rows.", len(rows))
        return headers, rows

    def build_csv(self, headers: list[str], rows: list[tuple]) -> str:
        """Serialize query results into a CSV string.

        Args:
            headers: Column names for the header row.
            rows: Result rows to write.

        Returns:
            The CSV document as a string.
        """
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(headers)
        writer.writerows(rows)
        return csv_buffer.getvalue()

    def save_artifact(self, csv_content: str) -> str:
        """Store the CSV content as a timestamped Job file artifact.

        Args:
            csv_content: The CSV document to store.

        Returns:
            The generated filename.
        """
        filename = f"nautobot_erd_{datetime.now():%Y%m%d_%H%M%S}.csv"
        self.create_file(filename, csv_content.encode("utf-8"))
        return filename

    def run(self):
        """Execute the schema export and store the result as a Job artifact."""
        sql = self.read_sql(ERD_FILENAME)
        headers, rows = self.execute_query(sql)
        csv_content = self.build_csv(headers, rows)
        filename = self.save_artifact(csv_content)

        self.logger.success(
            "Successfully created '%s' containing %d records.",
            filename,
            len(rows),
        )


jobs = [ERDExport]
register_jobs(*jobs)
