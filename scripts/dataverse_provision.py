"""Create the synthetic vendor-assurance tables in the training Dataverse environment.

Existing tables and columns are checked before writes; other failures stop the script.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vendor_assurance.dataverse import DataverseClient, DataverseError  # noqa: E402

PREFIX = os.environ.get("DATAVERSE_PREFIX", "cr522")


def label(text: str) -> dict:
    """Build a Dataverse localized label."""
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": 1033,
            }
        ],
    }


def string_column(name: str, display: str, length: int) -> dict:
    """Define a single-line text column."""
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "SchemaName": f"{PREFIX}_{name}",
        "MaxLength": length,
        "RequiredLevel": {"Value": "None"},
        "DisplayName": label(display),
    }


def memo_column(name: str, display: str) -> dict:
    """Define a multi-line text column."""
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
        "SchemaName": f"{PREFIX}_{name}",
        "MaxLength": 4000,
        "RequiredLevel": {"Value": "None"},
        "DisplayName": label(display),
    }


def integer_column(name: str, display: str, minimum: int, maximum: int) -> dict:
    """Define a bounded whole-number column."""
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
        "SchemaName": f"{PREFIX}_{name}",
        "MinValue": minimum,
        "MaxValue": maximum,
        "RequiredLevel": {"Value": "None"},
        "DisplayName": label(display),
    }


def date_column(name: str, display: str) -> dict:
    """Define a date-only column."""
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
        "SchemaName": f"{PREFIX}_{name}",
        "Format": "DateOnly",
        "DateTimeBehavior": {"Value": "DateOnly"},
        "RequiredLevel": {"Value": "None"},
        "DisplayName": label(display),
    }


def create_table(client: DataverseClient, name: str, display: str, plural: str, primary: str) -> None:
    """Create a user-owned table with a primary name column."""
    if client.exists(f"EntityDefinitions(LogicalName='{PREFIX}_{name}')?$select=MetadataId"):
        print(f"table {PREFIX}_{name}: already exists")
        return
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": f"{PREFIX}_{name}",
        "EntitySetName": f"{PREFIX}_{name}s",
        "DisplayName": label(display),
        "DisplayCollectionName": label(plural),
        "OwnershipType": "UserOwned",
        "HasActivities": False,
        "HasNotes": False,
        "IsActivity": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{PREFIX}_{primary}",
                "MaxLength": 200,
                "IsPrimaryName": True,
                "RequiredLevel": {"Value": "ApplicationRequired"},
                "DisplayName": label(primary),
            }
        ],
    }
    client.request("POST", "EntityDefinitions", body)
    print(f"table {PREFIX}_{name}: created")


def add_column(client: DataverseClient, table: str, column: dict) -> None:
    """Add one column to an existing table."""
    path = f"EntityDefinitions(LogicalName='{PREFIX}_{table}')/Attributes"
    if client.exists(f"{path}(LogicalName='{column['SchemaName'].lower()}')?$select=MetadataId"):
        print(f"  column {column['SchemaName']}: already exists")
        return
    client.request("POST", path, column)
    print(f"  column {column['SchemaName']}: created")


def main() -> None:
    """Provision both training tables."""
    client = DataverseClient.from_environment(allow_cli=True)
    create_table(client, "vendorreview", "Vendor Review", "Vendor Reviews", "Vendor")
    for column in (
        string_column("Attendee", "Attendee", 100),
        string_column("System", "System", 200),
        string_column("DataTypes", "Data types", 200),
        string_column("HostingRegion", "Hosting region", 200),
        string_column("DataResidency", "Data residency", 400),
        string_column("SubProcessors", "Sub-processors", 400),
        string_column("Soc2Type", "SOC 2 type", 50),
        date_column("ReportDate", "Report date"),
        integer_column("Score", "Score", 0, 10),
        string_column("Sensitivity", "Sensitivity", 20),
        memo_column("Gaps", "Gaps"),
    ):
        add_column(client, "vendorreview", column)

    create_table(client, "controlfinding", "Control Finding", "Control Findings", "Control")
    for column in (
        string_column("Status", "Status", 20),
        memo_column("Evidence", "Evidence"),
        string_column("Reasoning", "Reasoning", 500),
    ):
        add_column(client, "controlfinding", column)


if __name__ == "__main__":
    try:
        main()
    except (DataverseError, OSError, ValueError) as error:
        sys.exit(str(error))
