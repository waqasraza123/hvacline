"""Register an existing browser-only agent; never provisions or modifies a provider."""

import argparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from insurance_operations.database.connection import create_database_engine
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.website import WebsiteAgentBinding
from insurance_operations.settings import DatabaseSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agency-id", type=UUID, required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--confirm-browser-tools-only", action="store_true", required=True
    )
    args = parser.parse_args()
    if (
        not 1 <= len(args.agent_id.strip()) <= 200
        or not 1 <= len(args.label.strip()) <= 100
    ):
        parser.error(
            "Agent reference and label are required and must fit the documented bounds"
        )
    engine = create_database_engine(
        DatabaseSettings(), service_name="website-agent-registration"
    )
    try:
        with Session(engine) as session, session.begin():
            agency = session.scalar(
                select(Agency).where(
                    Agency.id == args.agency_id, Agency.archived_at.is_(None)
                )
            )
            if agency is None:
                parser.error("Active agency not found")
            binding = WebsiteAgentBinding(
                agency_id=agency.id,
                label=args.label.strip(),
                provider_agent_id=args.agent_id.strip(),
                enabled=True,
                browser_tools_confirmed=True,
            )
            session.add(binding)
            session.flush()
            print(f"Registered binding {binding.id}; no provider changes performed")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
