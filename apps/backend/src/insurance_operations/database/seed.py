import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, time
from uuid import UUID, uuid4, uuid5

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from insurance_operations.approved_faqs.schemas import ApprovedFaqContent
from insurance_operations.approved_faqs.service import normalize_faq_question
from insurance_operations.database.connection import create_database_engine
from insurance_operations.database.development_content import (
    DEVELOPMENT_ADDITIONAL_FAQS,
)
from insurance_operations.database.models import (
    Agency,
    AgencyApprovedFaq,
    AgencyCallPolicy,
    AgencyInboundNumber,
    AgencyMembership,
    AgencyReceptionistSettings,
    AppUser,
    AuditEvent,
    BusinessSchedule,
    InboundNumberStatus,
)
from insurance_operations.database.models.identity import AgencyEnvironment
from insurance_operations.hvac.schemas import ScheduleInput, Team, WorkingWindow
from insurance_operations.settings import DatabaseSettings, RuntimeEnvironment
from insurance_operations.telephony.phone_service import system_audit

DEVELOPMENT_AGENCY_ID = UUID("00000000-0000-4000-8000-000000000001")
DEVELOPMENT_AGENCY_NAME = "Harborline Heating & Air"
DEVELOPMENT_AGENCY_SLUG = "development-agency"
DEVELOPMENT_ACTOR_USER_ID = UUID("00000000-0000-4000-8000-000000000002")
DEVELOPMENT_ACTOR_AUTH_SUBJECT = UUID("00000000-0000-4000-8000-000000000003")
DEVELOPMENT_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000004")
DEVELOPMENT_RECEPTIONIST_SETTINGS_ID = UUID("00000000-0000-4000-8000-000000000005")
DEVELOPMENT_APPROVED_FAQ_IDS = (
    UUID("00000000-0000-4000-8000-000000000006"),
    UUID("00000000-0000-4000-8000-000000000007"),
    UUID("00000000-0000-4000-8000-000000000008"),
)
DEVELOPMENT_CALL_POLICY_ID = UUID("00000000-0000-4000-8000-000000000009")
DEVELOPMENT_INBOUND_NUMBER_ID = UUID("00000000-0000-4000-8000-000000000010")
DEVELOPMENT_ACTOR_DISPLAY_NAME = "Synthetic Voice AI Tester"
DEVELOPMENT_RECEPTIONIST_PUBLIC_NAME = "Harborline Heating & Air"
DEVELOPMENT_GREETING = (
    "Thanks for contacting Harborline Heating & Air. I'm Line, "
    "the AI booking assistant. Please use fictional details only."
)
DEVELOPMENT_ESCALATION_MESSAGE = (
    "I do not have an approved answer for that request. "
    "Staff assistance is needed. I cannot promise a transfer, "
    "callback time or delivered urgent alert."
)


DEVELOPMENT_FAQ_CONTENT: tuple[tuple[UUID, str, str, str], ...] = (
    (
        DEVELOPMENT_APPROVED_FAQ_IDS[0],
        "What are your office hours?",
        "what are your office hours",
        "Our office is open Monday through Friday from 9:00 AM "
        "to 5:00 PM Eastern Time.",
    ),
    (
        DEVELOPMENT_APPROVED_FAQ_IDS[1],
        "What HVAC services do you offer?",
        "what hvac services do you offer",
        "Our synthetic showcase handles air conditioning repair, "
        "heating repair, installation, and maintenance.",
    ),
    (
        DEVELOPMENT_APPROVED_FAQ_IDS[2],
        "How can I request an installation estimate?",
        "how can i request an installation estimate",
        "I can collect your contact details and HVAC service needs. "
        "A service team member must provide estimates and pricing.",
    ),
) + tuple(
    (
        uuid5(DEVELOPMENT_AGENCY_ID, f"approved-faq:{key}"),
        question,
        normalize_faq_question(question),
        answer,
    )
    for key, question, answer in DEVELOPMENT_ADDITIONAL_FAQS
)


@dataclass(frozen=True)
class DevelopmentSeedResult:
    agency_created: bool
    actor_created: bool
    membership_created: bool
    receptionist_settings_created: bool
    approved_faqs_created: int
    business_schedule_created: bool = False
    call_policy_configured: bool = False
    inbound_number_configured: bool = False


def seed_development_foundation(
    settings: DatabaseSettings, *, include_telephony: bool = True
) -> DevelopmentSeedResult:
    if settings.app_environment is not RuntimeEnvironment.DEVELOPMENT:
        raise ValueError("development seed requires APP_ENVIRONMENT=development")

    database_engine = create_database_engine(settings, service_name="development-seed")
    try:
        agency_statement = (
            insert(Agency)
            .values(
                id=DEVELOPMENT_AGENCY_ID,
                name=DEVELOPMENT_AGENCY_NAME,
                slug=DEVELOPMENT_AGENCY_SLUG,
                environment_kind=AgencyEnvironment.DEVELOPMENT.value,
            )
            .on_conflict_do_nothing(index_elements=[Agency.id])
            .returning(Agency.id)
        )
        actor_statement = (
            insert(AppUser)
            .values(
                id=DEVELOPMENT_ACTOR_USER_ID,
                auth_subject=DEVELOPMENT_ACTOR_AUTH_SUBJECT,
                display_name=DEVELOPMENT_ACTOR_DISPLAY_NAME,
            )
            .on_conflict_do_nothing(index_elements=[AppUser.id])
            .returning(AppUser.id)
        )
        membership_statement = (
            insert(AgencyMembership)
            .values(
                id=DEVELOPMENT_MEMBERSHIP_ID,
                agency_id=DEVELOPMENT_AGENCY_ID,
                app_user_id=DEVELOPMENT_ACTOR_USER_ID,
            )
            .on_conflict_do_nothing(index_elements=[AgencyMembership.id])
            .returning(AgencyMembership.id)
        )
        receptionist_settings_statement = (
            insert(AgencyReceptionistSettings)
            .values(
                id=DEVELOPMENT_RECEPTIONIST_SETTINGS_ID,
                agency_id=DEVELOPMENT_AGENCY_ID,
                public_name=DEVELOPMENT_RECEPTIONIST_PUBLIC_NAME,
                greeting=DEVELOPMENT_GREETING,
                office_hours=("Monday through Friday, 9:00 AM to 5:00 PM Eastern Time"),
                contact_email="receptionist@example.com",
                contact_phone="+1 555 010 0142",
                supported_insurance_categories=[
                    "AC repair",
                    "Heating repair",
                    "Installation",
                    "Maintenance",
                ],
                escalation_message=DEVELOPMENT_ESCALATION_MESSAGE,
                created_by=DEVELOPMENT_ACTOR_USER_ID,
                updated_by=DEVELOPMENT_ACTOR_USER_ID,
            )
            .on_conflict_do_nothing(constraint="uq_agency_receptionist_settings_agency")
            .returning(AgencyReceptionistSettings.id)
        )
        approved_faq_statements = []
        for faq_id, question, _, approved_answer in DEVELOPMENT_FAQ_CONTENT:
            content = ApprovedFaqContent(
                question=question, approved_answer=approved_answer
            )
            approved_faq_statements.append(
                insert(AgencyApprovedFaq)
                .values(
                    id=faq_id,
                    agency_id=DEVELOPMENT_AGENCY_ID,
                    question=content.question,
                    normalized_question=normalize_faq_question(content.question),
                    approved_answer=content.approved_answer,
                    status="ACTIVE",
                    created_by=DEVELOPMENT_ACTOR_USER_ID,
                    updated_by=DEVELOPMENT_ACTOR_USER_ID,
                )
                .on_conflict_do_nothing()
                .returning(AgencyApprovedFaq.id)
            )
        with database_engine.begin() as connection:
            agency_created = connection.scalar(agency_statement) is not None
            agency = connection.execute(
                select(Agency.environment_kind, Agency.archived_at)
                .where(Agency.id == DEVELOPMENT_AGENCY_ID)
                .with_for_update()
            ).one()
            if (
                agency.environment_kind != AgencyEnvironment.DEVELOPMENT.value
                or agency.archived_at is not None
            ):
                raise ValueError(
                    "business content requires the active development business"
                )
            connection.execute(
                update(Agency)
                .where(
                    Agency.id == DEVELOPMENT_AGENCY_ID,
                    Agency.environment_kind == AgencyEnvironment.DEVELOPMENT.value,
                    Agency.name == "Development Agency",
                )
                .values(name=DEVELOPMENT_AGENCY_NAME)
            )
            connection.execute(
                update(AgencyReceptionistSettings)
                .where(
                    AgencyReceptionistSettings.id
                    == DEVELOPMENT_RECEPTIONIST_SETTINGS_ID,
                    AgencyReceptionistSettings.agency_id == DEVELOPMENT_AGENCY_ID,
                    AgencyReceptionistSettings.public_name == "Harborline Insurance",
                    AgencyReceptionistSettings.row_version == 1,
                )
                .values(
                    public_name=DEVELOPMENT_RECEPTIONIST_PUBLIC_NAME,
                    greeting=DEVELOPMENT_GREETING,
                    supported_insurance_categories=[
                        "AC repair",
                        "Heating repair",
                        "Installation",
                        "Maintenance",
                    ],
                    escalation_message=DEVELOPMENT_ESCALATION_MESSAGE,
                )
            )
            for faq_id, old_question in (
                (
                    DEVELOPMENT_APPROVED_FAQ_IDS[1],
                    "what types of insurance can your agency help with",
                ),
                (DEVELOPMENT_APPROVED_FAQ_IDS[2], "how can i get an insurance quote"),
            ):
                _, question, normalized_question, answer = DEVELOPMENT_FAQ_CONTENT[
                    DEVELOPMENT_APPROVED_FAQ_IDS.index(faq_id)
                ]
                connection.execute(
                    update(AgencyApprovedFaq)
                    .where(
                        AgencyApprovedFaq.id == faq_id,
                        AgencyApprovedFaq.agency_id == DEVELOPMENT_AGENCY_ID,
                        AgencyApprovedFaq.normalized_question == old_question,
                        AgencyApprovedFaq.row_version == 1,
                    )
                    .values(
                        question=question,
                        normalized_question=normalized_question,
                        approved_answer=answer,
                    )
                )
            actor_created = connection.scalar(actor_statement) is not None
            membership_created = connection.scalar(membership_statement) is not None
            receptionist_settings_created = (
                connection.scalar(receptionist_settings_statement) is not None
            )
            fallback_updated = connection.scalar(
                update(AgencyReceptionistSettings)
                .where(
                    AgencyReceptionistSettings.id
                    == DEVELOPMENT_RECEPTIONIST_SETTINGS_ID,
                    AgencyReceptionistSettings.agency_id == DEVELOPMENT_AGENCY_ID,
                    AgencyReceptionistSettings.escalation_message.in_(
                        (
                            "A service team member will follow up for urgent requests, "
                            "hazards, estimates, or any request I cannot safely answer.",
                            "A service team member will follow up for urgent requests, "
                            "hazards, estimates, or questions I cannot safely answer.",
                        )
                    ),
                )
                .values(escalation_message=DEVELOPMENT_ESCALATION_MESSAGE)
                .returning(AgencyReceptionistSettings.id)
            )
            if fallback_updated is not None:
                connection.execute(
                    insert(AuditEvent).values(
                        agency_id=DEVELOPMENT_AGENCY_ID,
                        actor_type="SYSTEM",
                        event_type="AGENCY_RECEPTIONIST_SETTINGS_UPDATED",
                        occurred_at=datetime.now(UTC),
                        summary="Development fallback promise removed",
                        details={"source": "development_seed"},
                        correlation_id=uuid4(),
                        event_version=1,
                    )
                )
            created_faq_ids = [
                faq_id
                for statement in approved_faq_statements
                if (faq_id := connection.scalar(statement)) is not None
            ]
            approved_faqs_created = len(created_faq_ids)
            if created_faq_ids:
                correlation_id = uuid4()
                connection.execute(
                    insert(AuditEvent),
                    [
                        {
                            "agency_id": DEVELOPMENT_AGENCY_ID,
                            "actor_type": "SYSTEM",
                            "event_type": "AGENCY_APPROVED_FAQ_CREATED",
                            "occurred_at": datetime.now(UTC),
                            "summary": "Fictional development FAQ initialized",
                            "details": {
                                "faq_id": str(faq_id),
                                "faq_status": "ACTIVE",
                                "faq_row_version": 1,
                                "source": "development_seed",
                            },
                            "correlation_id": correlation_id,
                            "event_version": 1,
                        }
                        for faq_id in created_faq_ids
                    ],
                )
        business_schedule_created = configure_development_schedule(database_engine)
        call_policy_configured, inbound_number_configured = False, False
        if include_telephony:
            call_policy_configured, inbound_number_configured = configure_demo_telephony(
                database_engine, settings
            )
        return DevelopmentSeedResult(
            agency_created=agency_created,
            actor_created=actor_created,
            membership_created=membership_created,
            receptionist_settings_created=receptionist_settings_created,
            approved_faqs_created=approved_faqs_created,
            business_schedule_created=business_schedule_created,
            call_policy_configured=call_policy_configured,
            inbound_number_configured=inbound_number_configured,
        )
    finally:
        database_engine.dispose()


def configure_development_schedule(database_engine: Engine) -> bool:
    with Session(database_engine) as session, session.begin():
        agency = session.scalar(
            select(Agency)
            .where(Agency.id == DEVELOPMENT_AGENCY_ID)
            .with_for_update()
        )
        if (
            agency is None
            or agency.environment_kind != AgencyEnvironment.DEVELOPMENT.value
            or agency.archived_at is not None
        ):
            raise ValueError(
                "default scheduling requires the active development business"
            )
        if session.get(BusinessSchedule, DEVELOPMENT_AGENCY_ID) is not None:
            return False

        windows = [
            WorkingWindow(weekday=weekday, start=time(9), end=time(17))
            for weekday in range(5)
        ]
        configuration = ScheduleInput(
            expected_version=0,
            enabled=True,
            timezone="America/New_York",
            postal_codes=["10001"],
            windows=windows,
            teams=[Team(key="test-team", name="Test Team", windows=windows)],
            duration_minutes=60,
            notice_minutes=120,
            cancellation_notice_minutes=120,
            horizon_days=30,
        )
        session.add(
            BusinessSchedule(
                agency_id=DEVELOPMENT_AGENCY_ID,
                version=1,
                configuration=configuration.model_dump(mode="json"),
            )
        )
        session.add(
            system_audit(
                agency_id=DEVELOPMENT_AGENCY_ID,
                event_type="HVAC_SCHEDULE_CONFIGURED",
                summary="Fictional development booking calendar initialized",
                details={"version": 1, "source": "development_seed"},
                correlation_id=uuid4(),
            )
        )
        return True


def configure_demo_telephony(
    database_engine: Engine,
    settings: DatabaseSettings,
) -> tuple[bool, bool]:
    inbound_number = settings.demo_inbound_number_e164
    transfer_destination = settings.demo_transfer_destination_e164
    if inbound_number is None:
        return False, False

    availability_windows = [
        {
            "weekday": weekday,
            "start_local": "00:00",
            "end_local": "23:59",
        }
        for weekday in range(7)
    ]
    policy_values: dict[str, object] = {
        "inbound_enabled": True,
        "timezone": "UTC",
        "availability_windows": availability_windows,
        "transfer_enabled": transfer_destination is not None,
        "transfer_destination_e164": transfer_destination,
        "transfer_ring_timeout_seconds": 20,
        "max_concurrent_calls": 2,
        "daily_call_limit": 10,
        "callback_fallback_enabled": True,
        "after_hours_message": (
            "The synthetic demo team is unavailable and will follow up."
        ),
        "unavailable_message": (
            "The synthetic demo team could not answer and will follow up."
        ),
        "updated_by": DEVELOPMENT_ACTOR_USER_ID,
    }
    with Session(database_engine) as session, session.begin():
        policy = session.get(AgencyCallPolicy, DEVELOPMENT_CALL_POLICY_ID)
        if policy is None:
            policy = session.scalar(
                select(AgencyCallPolicy).where(
                    AgencyCallPolicy.agency_id == DEVELOPMENT_AGENCY_ID
                )
            )
        policy_changed = policy is None or any(
            getattr(policy, key) != value for key, value in policy_values.items()
        )
        if policy is None:
            session.add(
                AgencyCallPolicy(
                    id=DEVELOPMENT_CALL_POLICY_ID,
                    agency_id=DEVELOPMENT_AGENCY_ID,
                    created_by=DEVELOPMENT_ACTOR_USER_ID,
                    **policy_values,
                )
            )
        elif policy_changed:
            for key, value in policy_values.items():
                setattr(policy, key, value)

        mapped_number = session.scalar(
            select(AgencyInboundNumber).where(
                AgencyInboundNumber.phone_number_e164 == inbound_number
            )
        )
        if (
            mapped_number is not None
            and mapped_number.agency_id != DEVELOPMENT_AGENCY_ID
        ):
            raise ValueError("the demo inbound number belongs to another agency")
        number = session.get(AgencyInboundNumber, DEVELOPMENT_INBOUND_NUMBER_ID)
        if number is None:
            number = mapped_number
        number_values: dict[str, object] = {
            "phone_number_e164": inbound_number,
            "label": "Harborline phone-agent demo",
            "status": InboundNumberStatus.ACTIVE.value,
            "updated_by": DEVELOPMENT_ACTOR_USER_ID,
        }
        number_changed = number is None or any(
            getattr(number, key) != value for key, value in number_values.items()
        )
        if number is None:
            session.add(
                AgencyInboundNumber(
                    id=DEVELOPMENT_INBOUND_NUMBER_ID,
                    agency_id=DEVELOPMENT_AGENCY_ID,
                    created_by=DEVELOPMENT_ACTOR_USER_ID,
                    **number_values,
                )
            )
        elif number_changed:
            for key, value in number_values.items():
                setattr(number, key, value)
        return policy_changed, number_changed


def main() -> None:
    parser = argparse.ArgumentParser(prog="insurance-operations-seed-development")
    parser.add_argument(
        "--skip-telephony",
        action="store_true",
        help="Initialize development business content without changing phone routing.",
    )
    arguments = parser.parse_args()
    try:
        result = seed_development_foundation(
            DatabaseSettings(), include_telephony=not arguments.skip_telephony
        )
    except (ValueError, SQLAlchemyError) as error:
        parser.exit(1, f"development seed failed: {type(error).__name__}\n")

    created_count = (
        sum(
            (
                result.agency_created,
                result.actor_created,
                result.membership_created,
                result.receptionist_settings_created,
                result.business_schedule_created,
            )
        )
        + result.approved_faqs_created
    )
    print(f"development foundation: {created_count} record(s) created")


if __name__ == "__main__":
    main()
