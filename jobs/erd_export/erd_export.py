from pathlib import Path
from datetime import datetime
from io import StringIO
import csv

from django.core.files.base import ContentFile
from django.db import connection

from nautobot.apps.jobs import Job


class ERDExport(Job):
    """
    Export the Nautobot schema, including Custom Fields and Custom Relationships,
    in a Lucidchart-compatible CSV format.
    """

    class Meta:
        name = "Export ERD (Lucidchart)"
        description = (
            "Exports the Nautobot database schema, including Custom Fields "
            "and Custom Relationships, as a Lucidchart-compatible CSV."
        )

    def run(self):
        #
        # Locate SQL file
        #
        sql_file = Path(__file__).parent / "erd_export.sql"

        if not sql_file.exists():
            raise RuntimeError(
                f"Unable to locate SQL file: {sql_file}"
            )

        #
        # Read SQL
        #
        try:
            sql = sql_file.read_text(encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(
                f"Unable to read SQL file '{sql_file}': {exc}"
            ) from exc

        #
        # Execute SQL
        #
        self.logger.info("Executing schema export query...")

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)

                headers = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

        except Exception as exc:
            raise RuntimeError(
                f"Database query failed:\n{exc}"
            ) from exc

        self.logger.info("Retrieved %d rows.", len(rows))

        #
        # Build CSV
        #
        csv_buffer = StringIO()

        writer = csv.writer(csv_buffer)
        writer.writerow(headers)
        writer.writerows(rows)

        #
        # Save as Job artifact
        #
        filename = (
            f"nautobot_erd_{datetime.now():%Y%m%d_%H%M%S}.csv"
        )

        self.create_file(
            filename,
            ContentFile(csv_buffer.getvalue().encode("utf-8")),
        )

        self.logger.success(
            "Successfully created '%s' containing %d records.",
            filename,
            len(rows),
        )

