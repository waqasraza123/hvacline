from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from insurance_operations.database.models import TABLE_OWNERSHIP, Base

EXPECTED_OWNERSHIP = {
    "customer_mfa_factors": ("customer_access", "agency_id"),
    "customer_mfa_challenges": ("customer_access", "agency_id"),
    "customer_mfa_recovery_codes": ("customer_access", "agency_id"),
    "customer_memory_policies": ("customer_memory", "agency_id"),
    "customer_memory_facts": ("customer_memory", "agency_id"),
    "customer_memory_summaries": ("customer_memory", "agency_id"),
    "customer_whatsapp_identities": ("customer_memory", "agency_id"),
    "customer_memory_pairings": ("customer_memory", "agency_id"),
    "whatsapp_conversations": ("conversations", "agency_id"),
    "calendar_connections": ("hvac", "agency_id"),
    "calendar_authorizations": ("hvac", "agency_id"),
    "calendar_bookings": ("hvac", "agency_id"),
    "booking_notifications": ("notifications", "agency_id"),
    "booking_email_events": ("notifications", None),
    "customer_accounts": ("customer_access", "agency_id"),
    "customer_login_sessions": ("customer_access", None),
    "customer_auth_limits": ("customer_access", None),
    "business_schedules": ("hvac", "agency_id"),
    "hvac_service_requests": ("hvac", "agency_id"),
    "hvac_appointments": ("hvac", "agency_id"),
    "agencies": ("identity", None),
    "app_users": ("identity", None),
    "agency_memberships": ("identity", "agency_id"),
    "customers": ("customers", "agency_id"),
    "conversation_sessions": ("conversations", "agency_id"),
    "conversation_intakes": ("conversations", "agency_id"),
    "conversation_intake_confirmation_receipts": (
        "conversations",
        "agency_id",
    ),
    "agency_receptionist_settings": ("receptionist", "agency_id"),
    "agency_approved_faqs": ("approved_faqs", "agency_id"),
    "agency_leads": ("leads", "agency_id"),
    "lead_handoff_requests": ("leads", "agency_id"),
    "agency_call_policies": ("telephony", "agency_id"),
    "agency_inbound_numbers": ("telephony", "agency_id"),
    "inbound_calls": ("telephony", "agency_id"),
    "inbound_call_events": ("telephony", "agency_id"),
    "audit_events": ("audit", "agency_id"),
    "idempotency_records": ("idempotency", "agency_id"),
}


def test_every_foundation_table_has_explicit_ownership() -> None:
    assert set(TABLE_OWNERSHIP) == set(Base.metadata.tables)
    assert {
        table_name: (ownership.module, ownership.agency_column)
        for table_name, ownership in TABLE_OWNERSHIP.items()
    } == EXPECTED_OWNERSHIP


def test_agency_owned_tables_use_restrictive_foreign_keys(
    migrated_database: Engine,
) -> None:
    database_inspector = inspect(migrated_database)

    for table_name, ownership in TABLE_OWNERSHIP.items():
        if ownership.agency_column is None:
            continue

        agency_foreign_keys = [
            foreign_key
            for foreign_key in database_inspector.get_foreign_keys(table_name)
            if foreign_key["constrained_columns"] == [ownership.agency_column]
            and foreign_key["referred_table"] == "agencies"
        ]

        assert len(agency_foreign_keys) == 1
        assert agency_foreign_keys[0]["options"]["ondelete"] == "RESTRICT"


def test_foundation_relationships_match_available_parent_tables(
    migrated_database: Engine,
) -> None:
    database_inspector = inspect(migrated_database)
    expected_relationships: dict[str, set[tuple[tuple[str, ...], str]]] = {
        "customer_mfa_factors": {
            (("agency_id",), "agencies"), (("account_id",), "customer_accounts"),
        },
        "customer_mfa_challenges": {
            (("agency_id",), "agencies"), (("account_id",), "customer_accounts"),
        },
        "customer_mfa_recovery_codes": {
            (("agency_id",), "agencies"), (("account_id",), "customer_accounts"),
        },
        "customer_memory_policies": {
            (("agency_id",), "agencies"), (("account_id",), "customer_accounts"),
        },
        "customer_memory_facts": {
            (("agency_id",), "agencies"), (("account_id",), "customer_accounts"),
            (("source_intake_id",), "conversation_intakes"),
        },
        "customer_memory_summaries": {
            (("agency_id",), "agencies"), (("account_id",), "customer_accounts"),
            (("intake_id",), "conversation_intakes"),
        },
        "customer_whatsapp_identities": {
            (("agency_id",), "agencies"), (("account_id",), "customer_accounts"),
        },
        "customer_memory_pairings": {
            (("agency_id",), "agencies"), (("binding_id",), "whatsapp_conversations"),
        },
        "whatsapp_conversations": {
            (("agency_id",), "agencies"),
            (("session_id",), "conversation_sessions"),
            (("customer_account_id",), "customer_accounts"),
        },
        "calendar_connections": {(("agency_id",), "agencies")},
        "calendar_authorizations": {
            (("agency_id",), "agencies"),
            (("actor_id",), "app_users"),
        },
        "calendar_bookings": {
            (("agency_id",), "agencies"),
            (("agency_id", "appointment_id"), "hvac_appointments"),
            (("agency_id", "connection_id"), "calendar_connections"),
        },
        "booking_notifications": {
            (("agency_id",), "agencies"),
            (("agency_id", "appointment_id"), "hvac_appointments"),
        },
        "booking_email_events": set(),
        "customer_accounts": {
            (("agency_id",), "agencies"),
            (("app_user_id",), "app_users"),
        },
        "customer_login_sessions": {(("account_id",), "customer_accounts")},
        "customer_auth_limits": set(),
        "agencies": set(),
        "app_users": set(),
        "agency_memberships": {
            (("agency_id",), "agencies"),
            (("app_user_id",), "app_users"),
        },
        "customers": {
            (("agency_id",), "agencies"),
            (("created_by",), "app_users"),
        },
        "conversation_sessions": {
            (("agency_id",), "agencies"),
            (("initiated_by",), "app_users"),
            (("inbound_call_id",), "inbound_calls"),
        },
        "conversation_intakes": {
            (("agency_id",), "agencies"),
            (("customer_id",), "customers"),
            (("conversation_session_id",), "conversation_sessions"),
            (("created_by",), "app_users"),
        },
        "conversation_intake_confirmation_receipts": {
            (("agency_id",), "agencies"),
            (("conversation_session_id",), "conversation_sessions"),
            (("inbound_call_id",), "inbound_calls"),
        },
        "agency_receptionist_settings": {
            (("agency_id",), "agencies"),
            (("created_by",), "app_users"),
            (("updated_by",), "app_users"),
        },
        "agency_approved_faqs": {
            (("agency_id",), "agencies"),
            (("created_by",), "app_users"),
            (("updated_by",), "app_users"),
        },
        "agency_leads": {
            (("agency_id",), "agencies"),
            (("customer_id",), "customers"),
            (("conversation_intake_id",), "conversation_intakes"),
            (("created_by",), "app_users"),
            (("updated_by",), "app_users"),
        },
        "lead_handoff_requests": {
            (("agency_id",), "agencies"),
            (("lead_id",), "agency_leads"),
            (("conversation_session_id",), "conversation_sessions"),
            (("inbound_call_id",), "inbound_calls"),
            (("created_by",), "app_users"),
            (("updated_by",), "app_users"),
        },
        "agency_call_policies": {
            (("agency_id",), "agencies"),
            (("created_by",), "app_users"),
            (("updated_by",), "app_users"),
        },
        "agency_inbound_numbers": {
            (("agency_id",), "agencies"),
            (("created_by",), "app_users"),
            (("updated_by",), "app_users"),
        },
        "inbound_calls": {
            (("agency_id",), "agencies"),
            (("inbound_number_id",), "agency_inbound_numbers"),
            (("lead_id",), "agency_leads"),
        },
        "inbound_call_events": {
            (("agency_id",), "agencies"),
            (("inbound_call_id",), "inbound_calls"),
        },
        "audit_events": {
            (("agency_id",), "agencies"),
            (("actor_user_id",), "app_users"),
            (("customer_id",), "customers"),
        },
        "idempotency_records": {(("agency_id",), "agencies")},
    }

    actual_relationships = {
        table_name: {
            (tuple(foreign_key["constrained_columns"]), foreign_key["referred_table"])
            for foreign_key in database_inspector.get_foreign_keys(table_name)
        }
        for table_name in expected_relationships
    }

    assert actual_relationships == expected_relationships
