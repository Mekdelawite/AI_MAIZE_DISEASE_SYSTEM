
"""Import Ethiopia's administrative divisions and resolve legacy agent locations.

Unresolved or ambiguous legacy agent locations are deliberately left unchanged.
"""

from __future__ import annotations

import json
import sys
from urllib.request import Request, urlopen

from sqlalchemy import func, text

from backend.app.extensions import db
from backend.app.main import create_app
from backend.app.models import (
    ExtensionAgent,
    ExtensionAgentAssignmentHistory,
    GeographyRegion,
    GeographyWoreda,
    GeographyZone,
    User,
)


DATA_URL = "https://api.openadmindata.org/api/v1/et"


def fetch_level(level: str) -> list[dict[str, str]]:
    """Download and validate one administrative geography level."""
    request = Request(
        f"{DATA_URL}/{level}.json",
        headers={"User-Agent": "MaizeCareAI/1.0"},
    )

    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    entities = payload.get("entities")

    if not isinstance(entities, list) or not entities:
        raise RuntimeError(
            f"The Open Admin Data {level} list is empty or invalid."
        )

    normalized = []

    for item in entities:
        if not isinstance(item, dict):
            raise RuntimeError(
                f"The Open Admin Data {level} list contains an invalid entry."
            )

        entity_id = item.get("id")
        name_en = item.get("name_en")
        parent_id = item.get("parent_id")

        if not entity_id or not isinstance(name_en, str) or not name_en.strip():
            raise RuntimeError(
                f"The Open Admin Data {level} list contains a missing ID or name."
            )

        if level != "region" and not parent_id:
            raise RuntimeError(
                f"The Open Admin Data {level} entry {entity_id} has no parent."
            )

        normalized.append(
            {
                "id": str(entity_id),
                "parent_id": str(parent_id) if parent_id else "",
                "name_en": name_en.strip(),
                "name_local": str(item.get("name_local") or "").strip() or None,
            }
        )

    return normalized


def import_data() -> tuple[int, list[int], dict[str, int]]:
    """Import geography and resolve only unambiguous exact agent matches."""
    # Fetch all remote data before making database changes.
    regions = fetch_level("region")
    zones = fetch_level("zone")
    woredas = fetch_level("woreda")

    # Validate all parent relationships before importing.
    region_ids = {row["id"] for row in regions}
    zone_ids = {row["id"] for row in zones}

    if any(row["parent_id"] not in region_ids for row in zones):
        raise RuntimeError(
            "The Open Admin Data zone list references an unknown region."
        )

    if any(row["parent_id"] not in zone_ids for row in woredas):
        raise RuntimeError(
            "The Open Admin Data woreda list references an unknown zone."
        )

    # Import regions.
    for row in regions:
        region = db.session.get(GeographyRegion, row["id"])

        if region is None:
            region = GeographyRegion(id=row["id"])
            db.session.add(region)

        region.name_en = row["name_en"]
        region.name_local = row["name_local"]

    db.session.flush()

    # Import zones.
    for row in zones:
        zone = db.session.get(GeographyZone, row["id"])

        if zone is None:
            zone = GeographyZone(id=row["id"])
            db.session.add(zone)

        zone.region_id = row["parent_id"]
        zone.name_en = row["name_en"]
        zone.name_local = row["name_local"]

    db.session.flush()

    # Import woredas.
    for row in woredas:
        woreda = db.session.get(GeographyWoreda, row["id"])

        if woreda is None:
            woreda = GeographyWoreda(id=row["id"])
            db.session.add(woreda)

        woreda.zone_id = row["parent_id"]
        woreda.name_en = row["name_en"]
        woreda.name_local = row["name_local"]

    db.session.flush()

    # Resolve existing extension agents.
    agents = (
        ExtensionAgent.query
        .join(User, ExtensionAgent.user_id == User.id)
        .all()
    )

    assignments_created = 0
    unresolved: list[int] = []

    for agent in agents:
        # Do not change agents that already have complete geography IDs.
        if agent.region_id and agent.zone_id and agent.woreda_id:
            continue

        candidates = (
            GeographyWoreda.query
            .join(
                GeographyZone,
                GeographyWoreda.zone_id == GeographyZone.id,
            )
            .join(
                GeographyRegion,
                GeographyZone.region_id == GeographyRegion.id,
            )
            .filter(
                func.lower(GeographyWoreda.name_en)
                == (agent.woreda or "").strip().lower(),
                func.lower(GeographyRegion.name_en)
                == (agent.region or "").strip().lower(),
            )
            .all()
        )

        # Never guess or modify an unresolved/ambiguous agent.
        if len(candidates) != 1:
            unresolved.append(agent.user_id)
            continue

        woreda = candidates[0]

        # Assign verified geography IDs.
        agent.region_id = woreda.zone.region_id
        agent.zone_id = woreda.zone_id
        agent.woreda_id = woreda.id

        # Normalize the existing location labels.
        agent.region = woreda.zone.region.name_en
        agent.zone = woreda.zone.name_en
        agent.woreda = woreda.name_en

        # Create initial assignment history only if no history exists.
        history = ExtensionAgentAssignmentHistory.query.filter_by(
            user_id=agent.user_id,
        ).first()

        if history is None:
            db.session.add(
                ExtensionAgentAssignmentHistory(
                    user_id=agent.user_id,
                    new_woreda_id=woreda.id,
                    changed_by_admin_id=None,
                )
            )
            assignments_created += 1

    db.session.flush()

    # Check whether any active agent still lacks complete geography IDs.
    active_unassigned = db.session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM extension_agents
                WHERE account_status = 'active'
                  AND (
                      region_id IS NULL
                      OR zone_id IS NULL
                      OR woreda_id IS NULL
                  )
            )
            """
        )
    ).scalar()

    # Validate the active geography constraint only when safe.
    if not active_unassigned:
        db.session.execute(
            text(
                "ALTER TABLE extension_agents "
                "VALIDATE CONSTRAINT ck_extension_agent_active_woreda"
            )
        )

    # Validate the other migration constraints.
    db.session.execute(
        text(
            "ALTER TABLE extension_agents "
            "VALIDATE CONSTRAINT ck_extension_agent_account_status"
        )
    )

    db.session.execute(
        text(
            "ALTER TABLE extension_agents "
            "VALIDATE CONSTRAINT ck_extension_agent_professional_verification"
        )
    )

    # Commit all geography and assignment changes together.
    db.session.commit()

    counts = {
        "regions": len(regions),
        "zones": len(zones),
        "woredas": len(woredas),
    }

    return assignments_created, unresolved, counts


def main() -> int:
    app = create_app("development")

    with app.app_context():
        try:
            assignments_created, unresolved, counts = import_data()

        except Exception:
            db.session.rollback()
            raise

    print("Geography import completed successfully.")
    print(f"Regions processed: {counts['regions']}")
    print(f"Zones processed: {counts['zones']}")
    print(f"Woredas processed: {counts['woredas']}")
    print(f"New assignment-history records: {assignments_created}")

    if unresolved:
        print(
            "Unresolved legacy extension agents were left unchanged "
            "and need manual review: "
            + ", ".join(str(user_id) for user_id in unresolved),
            file=sys.stderr,
        )
    else:
        print("All legacy extension-agent locations were resolved.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
