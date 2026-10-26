"""Create the Dataverse application user for the deployed app's identity.

Without this, the app registration authenticates to Entra successfully and then receives 403
from every Dataverse call, because it is not a user inside the environment.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vendor_assurance.dataverse import DataverseClient, DataverseError  # noqa: E402


def main() -> None:
    """Create the application user if needed and grant it a security role."""
    app_id = str(UUID(os.environ.get("DATAVERSE_APP_ID", "")))
    role_name = os.environ.get("DATAVERSE_ROLE", "").strip()
    if not role_name:
        raise ValueError("Set DATAVERSE_ROLE to an approved role; no administrator role is assumed")
    client = DataverseClient.from_environment(allow_cli=True)
    params = {"$select": "systemuserid,_businessunitid_value", "$filter": f"applicationid eq {app_id}"}
    existing = client.rows("systemusers", **params)
    if not existing:
        units = client.rows("businessunits", **{"$select": "businessunitid", "$filter": "parentbusinessunitid eq null"})
        if len(units) != 1:
            raise DataverseError("Could not identify the root business unit")
        unit_id = units[0]["businessunitid"]
        client.request(
            "POST",
            "systemusers",
            {"applicationid": app_id, "businessunitid@odata.bind": f"/businessunits({unit_id})"},
        )
        existing = client.rows("systemusers", **params)
    if len(existing) != 1:
        raise DataverseError("Expected one application user; verify the application ID")
    user_id = existing[0]["systemuserid"]
    unit_id = existing[0]["_businessunitid_value"]
    escaped_role = role_name.replace("'", "''")
    roles = client.rows("roles", **{
        "$select": "roleid,name",
        "$filter": f"name eq '{escaped_role}' and _businessunitid_value eq {unit_id}",
    })
    if len(roles) != 1:
        raise DataverseError("Expected one matching role in the application user's business unit")
    role_id = roles[0]["roleid"]
    association = f"systemusers({user_id})/systemuserroles_association"
    if client.rows(association, **{"$select": "roleid", "$filter": f"roleid eq {role_id}"}):
        print(f"role {role_name}: already assigned")
        return
    client.request(
        "POST",
        f"{association}/$ref",
        {"@odata.id": f"{client.url}/api/data/v9.2/roles({role_id})"},
    )
    print(f"role {role_name}: assigned")


if __name__ == "__main__":
    try:
        main()
    except (DataverseError, OSError, ValueError) as error:
        sys.exit(str(error))
