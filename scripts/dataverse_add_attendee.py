"""Add the attendee ownership column to the vendor review table.

Each attendee filters the shared table by the label in config.json. This is not row-level
authorization. The main provisioning script also creates this column.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.dataverse_provision import add_column, string_column  # noqa: E402
from src.vendor_assurance.dataverse import DataverseClient, DataverseError  # noqa: E402


def main() -> None:
    """Add the attendee label column if it is absent."""
    client = DataverseClient.from_environment(allow_cli=True)
    add_column(client, "vendorreview", string_column("Attendee", "Attendee", 100))


if __name__ == "__main__":
    try:
        main()
    except (DataverseError, OSError, ValueError) as error:
        sys.exit(str(error))
