from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, inspect, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
)
from insurance_operations.database.seed import (
    DEVELOPMENT_ACTOR_USER_ID,
    DEVELOPMENT_AGENCY_ID,
    DEVELOPMENT_AGENCY_SLUG,
    DEVELOPMENT_APPROVED_FAQ_IDS,
    DEVELOPMENT_CALL_POLICY_ID,
    DEVELOPMENT_FAQ_CONTENT,
    DEVELOPMENT_INBOUND_NUMBER_ID,
    DEVELOPMENT_MEMBERSHIP_ID,
    DEVELOPMENT_RECEPTIONIST_SETTINGS_ID,
    seed_development_foundation,
)
from insurance_operations.hvac.schemas import ScheduleInput
from insurance_operations.hvac.service import SchedulingService
from insurance_operations.settings import (
    DatabaseSettings,
    RuntimeEnvironment,
)

EXPECTED_TABLES = {
    "homepage_chat_visitors", "homepage_chat_daily_usage",
    "customer_mfa_factors", "customer_mfa_challenges", "customer_mfa_recovery_codes",
    "customer_memory_policies", "customer_memory_facts", "customer_memory_summaries",
    "customer_whatsapp_identities", "customer_memory_pairings",
    "whatsapp_conversations",
    "calendar_connections",
    "calendar_authorizations",
    "calendar_bookings",
    "booking_notifications",
    "booking_email_events",
    "customer_accounts",
    "customer_login_sessions",
    "customer_auth_limits",
    "business_schedules",
    "hvac_service_requests",
    "hvac_appointments",
    "agencies",
    "app_users",
    "agency_memberships",
    "customers",
    "audit_events",
    "idempotency_records",
    "conversation_sessions",
    "conversation_intakes",
    "conversation_intake_confirmation_receipts",
    "agency_receptionist_settings",
    "agency_approved_faqs",
    "agency_leads",
    "lead_handoff_requests",
    "agency_call_policies",
    "agency_inbound_numbers",
    "inbound_calls",
    "inbound_call_events",
}

EXPECTED_COLUMNS = {
    "homepage_chat_visitors": {
        "agency_id",
        "token_hash",
        "state",
        "request_id",
        "request_hash",
        "created_at",
        "expires_at",
        "lease_expires_at",
    },
    "homepage_chat_daily_usage": {"agency_id", "day", "generations"},
    "customer_mfa_factors": {
        "account_id", "agency_id", "secret_ciphertext", "enabled_at", "last_counter",
        "version", "failed_attempts", "locked_until",
    },
    "customer_mfa_challenges": {
        "id", "account_id", "agency_id", "token_hash", "purpose", "secret_ciphertext",
        "factor_version", "attempts", "created_at", "expires_at", "consumed_at",
    },
    "customer_mfa_recovery_codes": {
        "id", "account_id", "agency_id", "code_hash", "created_at", "used_at",
    },
    "customer_memory_policies": {
        "account_id", "agency_id", "enabled", "revision", "history_after",
        "updated_at", "last_request_id", "last_fingerprint", "retention_days",
    },
    "customer_memory_facts": {
        "id", "agency_id", "account_id", "key", "value", "source_intake_id",
        "source_kind", "created_at", "updated_at", "expires_at",
    },
    "customer_memory_summaries": {
        "intake_id", "agency_id", "account_id", "summary", "created_at", "expires_at",
    },
    "customer_whatsapp_identities": {
        "id", "agency_id", "account_id", "phone_number_id", "caller_digest",
        "verified_at", "expires_at", "mfa_version",
    },
    "customer_memory_pairings": {
        "id", "agency_id", "binding_id", "code_digest", "expires_at", "consumed_at",
    },
    "whatsapp_conversations": {
        "id",
        "agency_id",
        "conversation_id",
        "phone_number_id",
        "caller_digest",
        "session_id",
        "initialized_at",
        "expires_at",
        "finalized_at",
        "customer_account_id",
    },
    "calendar_connections": {
        "id",
        "agency_id",
        "team_key",
        "calendar_id",
        "refresh_token_ciphertext",
        "status",
        "last_checked_at",
        "last_error",
    },
    "calendar_authorizations": {
        "id",
        "agency_id",
        "actor_id",
        "state_digest",
        "browser_digest",
        "verifier_ciphertext",
        "team_key",
        "calendar_id",
        "expires_at",
    },
    "calendar_bookings": {
        "appointment_id",
        "agency_id",
        "connection_id",
        "status",
        "next_attempt_at",
        "last_error",
    },
    "booking_notifications": {
        "id",
        "agency_id",
        "appointment_id",
        "kind",
        "status",
        "due_at",
        "attempts",
        "first_attempt_at",
        "payload",
        "provider_reference",
        "last_error",
        "delivery_status",
    },
    "booking_email_events": {"id", "provider_reference", "status", "occurred_at"},
    "customer_accounts": {
        "id",
        "agency_id",
        "app_user_id",
        "email",
        "password_hash",
        "created_at",
    },
    "customer_login_sessions": {
        "id",
        "account_id",
        "token_hash",
        "expires_at",
        "revoked_at",
        "mfa_verified_at",
        "mfa_version",
    },
    "customer_auth_limits": {"key", "attempts", "window_started_at"},
    "business_schedules": {"agency_id", "version", "configuration"},
    "hvac_service_requests": {
        "id",
        "agency_id",
        "inbound_call_id",
        "conversation_session_id",
        "customer_details",
        "service_details",
        "status",
        "fingerprint",
        "confirmed_at",
    },
    "hvac_appointments": {
        "id",
        "agency_id",
        "service_request_id",
        "team_key",
        "starts_at",
        "ends_at",
        "status",
        "hold_expires_at",
        "idempotency_key",
        "fingerprint",
    },
    "agencies": {
        "id",
        "name",
        "slug",
        "environment_kind",
        "created_at",
        "updated_at",
        "row_version",
        "archived_at",
    },
    "app_users": {
        "id",
        "auth_subject",
        "display_name",
        "email_snapshot",
        "status",
        "created_at",
        "updated_at",
        "row_version",
        "disabled_at",
    },
    "agency_memberships": {
        "id",
        "agency_id",
        "app_user_id",
        "status",
        "created_at",
        "updated_at",
        "row_version",
        "deactivated_at",
    },
    "customers": {
        "id",
        "agency_id",
        "demo_session_id",
        "full_name",
        "normalized_name",
        "email",
        "normalized_email",
        "phone",
        "normalized_phone",
        "address_line1",
        "address_line2",
        "city",
        "state_code",
        "postal_code",
        "country_code",
        "search_text",
        "created_by",
        "created_at",
        "updated_at",
        "row_version",
        "archived_at",
    },
    "audit_events": {
        "id",
        "agency_id",
        "demo_session_id",
        "actor_type",
        "actor_user_id",
        "event_type",
        "occurred_at",
        "customer_id",
        "document_id",
        "attempt_id",
        "review_id",
        "policy_version_id",
        "email_delivery_id",
        "summary",
        "details",
        "correlation_id",
        "event_version",
        "created_at",
    },
    "idempotency_records": {
        "id",
        "agency_id",
        "demo_session_id",
        "actor_scope_type",
        "actor_scope_id",
        "route_key",
        "idempotency_key",
        "request_fingerprint",
        "status",
        "response_status",
        "response_body",
        "resource_type",
        "resource_id",
        "failure_code",
        "created_at",
        "completed_at",
        "expires_at",
    },
    "conversation_sessions": {
        "id",
        "agency_id",
        "initiated_by",
        "channel",
        "input_mode",
        "inbound_call_id",
        "status",
        "provider_metadata",
        "disclosure_accepted_at",
        "microphone_consent_at",
        "synthetic_data_acknowledged_at",
        "maximum_duration_seconds",
        "authorization_expires_at",
        "confirmation_expires_at",
        "authorized_at",
        "ended_at",
        "confirmed_at",
        "failure_code",
        "created_at",
        "updated_at",
        "row_version",
    },
    "conversation_intakes": {
        "id",
        "agency_id",
        "customer_id",
        "conversation_session_id",
        "created_by",
        "confirmation_source",
        "intake_intent",
        "confirmed_transcript",
        "confirmed_at",
        "created_at",
    },
    "conversation_intake_confirmation_receipts": {
        "id",
        "agency_id",
        "conversation_session_id",
        "inbound_call_id",
        "full_name",
        "email",
        "phone",
        "intake_intent",
        "urgency",
        "request_fingerprint",
        "confirmed_at",
        "created_at",
    },
    "agency_receptionist_settings": {
        "id",
        "agency_id",
        "public_name",
        "greeting",
        "office_hours",
        "contact_email",
        "contact_phone",
        "supported_insurance_categories",
        "escalation_message",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "row_version",
    },
    "agency_approved_faqs": {
        "id",
        "agency_id",
        "question",
        "normalized_question",
        "approved_answer",
        "status",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "row_version",
    },
    "agency_leads": {
        "id",
        "agency_id",
        "customer_id",
        "conversation_intake_id",
        "status",
        "urgency",
        "summary",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "row_version",
    },
    "lead_handoff_requests": {
        "id",
        "agency_id",
        "lead_id",
        "conversation_session_id",
        "inbound_call_id",
        "request_kind",
        "preferred_contact_method",
        "reason",
        "availability",
        "transfer_attempted",
        "status",
        "created_by",
        "updated_by",
        "completed_at",
        "cancelled_at",
        "created_at",
        "updated_at",
        "row_version",
    },
    "agency_call_policies": {
        "id",
        "agency_id",
        "inbound_enabled",
        "timezone",
        "availability_windows",
        "transfer_enabled",
        "transfer_destination_e164",
        "transfer_ring_timeout_seconds",
        "max_concurrent_calls",
        "daily_call_limit",
        "callback_fallback_enabled",
        "after_hours_message",
        "unavailable_message",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "row_version",
    },
    "agency_inbound_numbers": {
        "id",
        "agency_id",
        "phone_number_e164",
        "label",
        "status",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "row_version",
    },
    "inbound_calls": {
        "id",
        "agency_id",
        "inbound_number_id",
        "lead_id",
        "status",
        "caller_number_e164",
        "adapter_name",
        "source_call_reference",
        "adapter_metadata",
        "policy_snapshot",
        "received_at",
        "answered_at",
        "ended_at",
        "failure_code",
        "created_at",
        "updated_at",
        "row_version",
    },
    "inbound_call_events": {
        "id",
        "agency_id",
        "inbound_call_id",
        "event_key",
        "event_type",
        "occurred_at",
        "details",
        "created_at",
    },
}


def test_migration_creates_only_the_approved_foundation_tables(
    migrated_database: Engine,
) -> None:
    table_names = set(inspect(migrated_database).get_table_names())

    assert table_names >= EXPECTED_TABLES
    assert table_names <= EXPECTED_TABLES | {"alembic_version"}


def test_migration_columns_match_the_approved_contract(
    migrated_database: Engine,
) -> None:
    database_inspector = inspect(migrated_database)

    actual_columns = {
        table_name: {
            column["name"] for column in database_inspector.get_columns(table_name)
        }
        for table_name in EXPECTED_TABLES
    }

    assert actual_columns == EXPECTED_COLUMNS


def test_synthetic_acknowledgement_is_optional_but_disclosure_is_required(
    migrated_database: Engine,
) -> None:
    columns = {
        column["name"]: column
        for column in inspect(migrated_database).get_columns("conversation_sessions")
    }
    assert columns["synthetic_data_acknowledged_at"]["nullable"] is True
    assert columns["disclosure_accepted_at"]["nullable"] is False


def test_migration_creates_only_the_documented_foundation_indexes(
    migrated_database: Engine,
) -> None:
    database_inspector = inspect(migrated_database)
    agency_indexes = {
        index["name"] for index in database_inspector.get_indexes("agencies")
    }
    customer_indexes = {
        index["name"] for index in database_inspector.get_indexes("customers")
    }
    audit_indexes = {
        index["name"] for index in database_inspector.get_indexes("audit_events")
    }
    conversation_session_indexes = {
        index["name"]
        for index in database_inspector.get_indexes("conversation_sessions")
    }
    conversation_intake_indexes = {
        index["name"]
        for index in database_inspector.get_indexes("conversation_intakes")
    }
    receptionist_settings_indexes = {
        index["name"]
        for index in database_inspector.get_indexes("agency_receptionist_settings")
    }
    approved_faq_indexes = {
        index["name"]
        for index in database_inspector.get_indexes("agency_approved_faqs")
    }
    lead_indexes = {
        index["name"] for index in database_inspector.get_indexes("agency_leads")
    }
    handoff_indexes = {
        index["name"]
        for index in database_inspector.get_indexes("lead_handoff_requests")
    }
    call_policy_indexes = {
        index["name"]
        for index in database_inspector.get_indexes("agency_call_policies")
    }
    inbound_number_indexes = {
        index["name"]
        for index in database_inspector.get_indexes("agency_inbound_numbers")
    }
    inbound_call_indexes = {
        index["name"] for index in database_inspector.get_indexes("inbound_calls")
    }
    inbound_call_event_indexes = {
        index["name"] for index in database_inspector.get_indexes("inbound_call_events")
    }

    assert agency_indexes == {
        "ix_agencies_environment_kind",
        "uq_agencies_slug",
    }
    assert customer_indexes == {
        "ix_customers_agency_archive_updated",
        "ix_customers_search_text_trgm",
    }
    assert audit_indexes == {
        "ix_audit_events_customer_occurred",
        "ix_audit_events_document_occurred",
        "ix_audit_events_policy_version_occurred",
    }
    assert conversation_session_indexes == {
        "ix_conversation_sessions_agency_authorized",
        "ix_conversation_sessions_agency_created",
        "ix_conversation_sessions_agency_status_expires",
        "uq_conversation_sessions_inbound_call",
    }
    assert conversation_intake_indexes == {
        "ix_conversation_intakes_customer_confirmed",
        "uq_conversation_intakes_session",
    }
    assert receptionist_settings_indexes == {"uq_agency_receptionist_settings_agency"}
    assert approved_faq_indexes == {
        "ix_agency_approved_faqs_agency_status",
        "uq_agency_approved_faqs_agency_question",
    }
    assert lead_indexes == {
        "ix_agency_leads_agency_status_created",
        "ix_agency_leads_customer_created",
        "uq_agency_leads_conversation_intake",
    }
    assert handoff_indexes == {
        "ix_handoff_requests_agency_status",
        "ix_handoff_requests_lead_created",
        "uq_handoff_requests_inbound_call",
    }
    assert call_policy_indexes == {"uq_agency_call_policies_agency"}
    assert inbound_number_indexes == {
        "ix_inbound_numbers_agency_status",
        "uq_agency_inbound_numbers_phone",
    }
    assert inbound_call_indexes == {
        "ix_inbound_calls_agency_status_created",
        "ix_inbound_calls_number_created",
        "uq_inbound_calls_adapter_reference",
    }
    assert inbound_call_event_indexes == {
        "ix_inbound_call_events_call_occurred",
        "uq_inbound_call_events_call_key",
    }


def test_migration_unique_constraints_match_the_approved_scopes(
    migrated_database: Engine,
) -> None:
    database_inspector = inspect(migrated_database)
    expected_unique_columns: dict[str, set[tuple[str, ...]]] = {
        "customer_mfa_challenges": {("token_hash",)},
        "customer_mfa_recovery_codes": {("code_hash",)},
        "whatsapp_conversations": {("conversation_id",), ("session_id",)},
        "agencies": {("slug",)},
        "app_users": {("auth_subject",)},
        "agency_memberships": {("agency_id", "app_user_id")},
        "customers": set(),
        "audit_events": set(),
        "idempotency_records": {
            (
                "actor_scope_type",
                "actor_scope_id",
                "route_key",
                "idempotency_key",
            )
        },
        "conversation_sessions": {("inbound_call_id",)},
        "conversation_intakes": {("conversation_session_id",)},
        "conversation_intake_confirmation_receipts": {
            ("conversation_session_id",),
            ("inbound_call_id",),
        },
        "agency_receptionist_settings": {("agency_id",)},
        "agency_approved_faqs": {("agency_id", "normalized_question")},
        "agency_leads": {("conversation_intake_id",)},
        "lead_handoff_requests": {("inbound_call_id",)},
        "agency_call_policies": {("agency_id",)},
        "agency_inbound_numbers": {("phone_number_e164",)},
        "inbound_calls": {("adapter_name", "source_call_reference")},
        "inbound_call_events": {("inbound_call_id", "event_key")},
    }
    actual_unique_columns = {
        table_name: {
            tuple(constraint["column_names"])
            for constraint in database_inspector.get_unique_constraints(table_name)
        }
        for table_name in expected_unique_columns
    }

    assert actual_unique_columns == expected_unique_columns


def test_migration_check_constraints_cover_approved_invariants(
    migrated_database: Engine,
) -> None:
    database_inspector = inspect(migrated_database)
    expected_constraint_names = {
        "customer_login_sessions": {"ck_customer_login_sessions_mfa_consistent"},
        "customer_mfa_factors": {
            "ck_customer_mfa_factors_version_valid",
            "ck_customer_mfa_factors_counter_valid",
            "ck_customer_mfa_factors_attempts_valid",
            "ck_customer_mfa_factors_enrollment_consistent",
        },
        "customer_mfa_challenges": {
            "ck_customer_mfa_challenges_purpose_valid",
            "ck_customer_mfa_challenges_attempts_valid",
            "ck_customer_mfa_challenges_version_valid",
            "ck_customer_mfa_challenges_secret_consistent",
        },
        "whatsapp_conversations": {
            "ck_whatsapp_conversations_caller_digest_valid",
            "ck_whatsapp_conversations_expiry_valid",
        },
        "agencies": {
            "ck_agencies_name_length_valid",
            "ck_agencies_slug_lowercase",
            "ck_agencies_environment_kind_valid",
            "ck_agencies_row_version_positive",
        },
        "app_users": {
            "ck_app_users_display_name_length_valid",
            "ck_app_users_status_valid",
            "ck_app_users_disabled_at_consistent",
            "ck_app_users_row_version_positive",
        },
        "agency_memberships": {
            "ck_agency_memberships_status_valid",
            "ck_agency_memberships_row_version_positive",
        },
        "customers": {
            "ck_customers_full_name_length_valid",
            "ck_customers_state_code_length_valid",
            "ck_customers_country_code_length_valid",
            "ck_customers_row_version_positive",
        },
        "audit_events": {
            "ck_audit_events_actor_type_valid",
            "ck_audit_events_event_version_positive",
        },
        "idempotency_records": {
            "ck_idempotency_records_key_length_valid",
            "ck_idempotency_records_status_valid",
        },
        "conversation_sessions": {
            "ck_conversation_sessions_status_valid",
            "ck_conversation_sessions_duration_valid",
            "ck_conversation_sessions_provider_metadata_object",
            "ck_conversation_sessions_channel_valid",
            "ck_conversation_sessions_input_mode_valid",
            "ck_conversation_sessions_input_mode_consent_consistent",
            "ck_conversation_sessions_channel_call_consistent",
            "ck_conversation_sessions_confirmed_at_consistent",
            "ck_conversation_sessions_row_version_positive",
        },
        "conversation_intakes": {
            "ck_conversation_intakes_confirmation_source_valid",
            "ck_conversation_intakes_intake_intent_length_valid",
            "ck_conversation_intakes_transcript_array_valid",
        },
        "conversation_intake_confirmation_receipts": {
            "ck_conversation_intake_confirmation_receipts_name_valid",
            "ck_conversation_intake_confirmation_receipts_contact_required",
            "ck_conversation_intake_confirmation_receipts_intent_valid",
            "ck_conversation_intake_confirmation_receipts_urgency_valid",
            "ck_conversation_intake_confirmation_receipts_fingerprint_valid",
        },
        "agency_receptionist_settings": {
            "ck_agency_receptionist_settings_public_name_length_valid",
            "ck_agency_receptionist_settings_greeting_length_valid",
            "ck_agency_receptionist_settings_office_hours_length_valid",
            "ck_agency_receptionist_settings_contact_email_length_valid",
            "ck_agency_receptionist_settings_contact_phone_length_valid",
            "ck_agency_receptionist_settings_contact_method_required",
            "ck_agency_receptionist_settings_supported_categories_valid",
            "ck_agency_receptionist_settings_escalation_message_length_valid",
            "ck_agency_receptionist_settings_row_version_positive",
        },
        "agency_approved_faqs": {
            "ck_agency_approved_faqs_question_length_valid",
            "ck_agency_approved_faqs_normalized_question_valid",
            "ck_agency_approved_faqs_answer_length_valid",
            "ck_agency_approved_faqs_status_valid",
            "ck_agency_approved_faqs_row_version_positive",
        },
        "agency_leads": {
            "ck_agency_leads_status_valid",
            "ck_agency_leads_urgency_valid",
            "ck_agency_leads_summary_length_valid",
            "ck_agency_leads_row_version_positive",
        },
        "lead_handoff_requests": {
            "ck_lead_handoff_requests_request_kind_valid",
            "ck_lead_handoff_requests_contact_method_valid",
            "ck_lead_handoff_requests_reason_length_valid",
            "ck_lead_handoff_requests_availability_length_valid",
            "ck_lead_handoff_requests_status_valid",
            "ck_lead_handoff_requests_completed_at_consistent",
            "ck_lead_handoff_requests_cancelled_at_consistent",
            "ck_lead_handoff_requests_row_version_positive",
        },
        "agency_call_policies": {
            "ck_agency_call_policies_timezone_length_valid",
            "ck_agency_call_policies_transfer_number_length_valid",
            "ck_agency_call_policies_transfer_destination_required",
            "ck_agency_call_policies_ring_timeout_valid",
            "ck_agency_call_policies_concurrent_limit_valid",
            "ck_agency_call_policies_daily_limit_valid",
            "ck_agency_call_policies_availability_windows_array",
            "ck_agency_call_policies_after_hours_message_valid",
            "ck_agency_call_policies_unavailable_message_valid",
            "ck_agency_call_policies_row_version_positive",
        },
        "agency_inbound_numbers": {
            "ck_agency_inbound_numbers_phone_number_length_valid",
            "ck_agency_inbound_numbers_label_length_valid",
            "ck_agency_inbound_numbers_status_valid",
            "ck_agency_inbound_numbers_row_version_positive",
        },
        "inbound_calls": {
            "ck_inbound_calls_status_valid",
            "ck_inbound_calls_caller_number_length_valid",
            "ck_inbound_calls_adapter_name_length_valid",
            "ck_inbound_calls_source_reference_length_valid",
            "ck_inbound_calls_failure_code_length_valid",
            "ck_inbound_calls_answered_time_valid",
            "ck_inbound_calls_ended_time_valid",
            "ck_inbound_calls_failure_code_consistent",
            "ck_inbound_calls_adapter_metadata_object",
            "ck_inbound_calls_policy_snapshot_object",
            "ck_inbound_calls_row_version_positive",
        },
        "inbound_call_events": {
            "ck_inbound_call_events_event_type_length_valid",
            "ck_inbound_call_events_event_key_length_valid",
            "ck_inbound_call_events_details_object",
        },
    }
    actual_constraint_names = {
        table_name: {
            constraint["name"]
            for constraint in database_inspector.get_check_constraints(table_name)
        }
        for table_name in expected_constraint_names
    }

    assert actual_constraint_names == expected_constraint_names


def test_row_version_and_membership_constraints_are_enforced(
    migrated_database: Engine,
) -> None:
    agency_id = uuid4()
    user_id = uuid4()
    with migrated_database.begin() as connection:
        connection.execute(
            insert(Agency).values(
                id=agency_id,
                name="Constraint Agency",
                slug=f"constraint-{agency_id}",
                environment_kind="DEVELOPMENT",
            )
        )
        connection.execute(
            insert(AppUser).values(
                id=user_id,
                auth_subject=uuid4(),
                display_name="Constraint User",
            )
        )

    with pytest.raises(IntegrityError), migrated_database.begin() as connection:
        connection.execute(
            insert(Agency).values(
                id=uuid4(),
                name="Invalid Version",
                slug=f"invalid-{uuid4()}",
                environment_kind="DEVELOPMENT",
                row_version=0,
            )
        )

    with pytest.raises(IntegrityError), migrated_database.begin() as connection:
        connection.execute(
            insert(AgencyMembership).values(
                agency_id=agency_id,
                app_user_id=user_id,
                status="UNKNOWN",
            )
        )


def test_mutable_records_increment_row_version_on_update(
    migrated_database: Engine,
) -> None:
    agency_id = uuid4()
    with migrated_database.begin() as connection:
        connection.execute(
            insert(Agency).values(
                id=agency_id,
                name="Versioned Agency",
                slug=f"versioned-{agency_id}",
                environment_kind="DEVELOPMENT",
            )
        )
        connection.execute(
            update(Agency).where(Agency.id == agency_id).values(name="Updated Agency")
        )
        row_version = connection.scalar(
            select(Agency.row_version).where(Agency.id == agency_id)
        )

    assert row_version == 2


def test_development_seed_is_idempotent(
    migrated_database: Engine,
    database_settings: DatabaseSettings,
) -> None:
    settings = DatabaseSettings.model_validate(
        {
            "app_environment": RuntimeEnvironment.DEVELOPMENT,
            "database_url": database_settings.runtime_database_url,
            "direct_database_url": None,
            "test_database_url": None,
            "database_ssl_mode": database_settings.database_ssl_mode,
            "database_pool_size": database_settings.database_pool_size,
            "database_max_overflow": database_settings.database_max_overflow,
            "database_pool_timeout_seconds": (
                database_settings.database_pool_timeout_seconds
            ),
            "database_pool_recycle_seconds": (
                database_settings.database_pool_recycle_seconds
            ),
        }
    )

    assert settings.database_ssl_mode is database_settings.database_ssl_mode

    first_result = seed_development_foundation(settings)
    second_result = seed_development_foundation(settings)

    assert first_result.agency_created is True
    assert first_result.actor_created is True
    assert first_result.membership_created is True
    assert first_result.receptionist_settings_created is True
    assert first_result.approved_faqs_created == len(DEVELOPMENT_FAQ_CONTENT)
    assert first_result.business_schedule_created is True
    assert second_result.agency_created is False
    assert second_result.actor_created is False
    assert second_result.membership_created is False
    assert second_result.receptionist_settings_created is False
    assert second_result.approved_faqs_created == 0
    assert second_result.business_schedule_created is False

    with Session(migrated_database) as session:
        receptionist_settings = session.get(
            AgencyReceptionistSettings,
            DEVELOPMENT_RECEPTIONIST_SETTINGS_ID,
        )
        approved_faq_count = session.scalar(
            select(func.count())
            .select_from(AgencyApprovedFaq)
            .where(
                AgencyApprovedFaq.id.in_(
                    tuple(content[0] for content in DEVELOPMENT_FAQ_CONTENT)
                )
            )
        )
        faq_audit_count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.agency_id == DEVELOPMENT_AGENCY_ID,
                AuditEvent.event_type == "AGENCY_APPROVED_FAQ_CREATED",
            )
        )
        schedule = session.get(BusinessSchedule, DEVELOPMENT_AGENCY_ID)
        schedule_audit_count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.agency_id == DEVELOPMENT_AGENCY_ID,
                AuditEvent.event_type == "HVAC_SCHEDULE_CONFIGURED",
            )
        )

    assert receptionist_settings is not None
    assert approved_faq_count == len(DEVELOPMENT_FAQ_CONTENT)
    assert faq_audit_count == len(DEVELOPMENT_FAQ_CONTENT)
    assert schedule is not None
    assert schedule.version == 1
    configuration = ScheduleInput.model_validate(schedule.configuration)
    assert configuration.enabled is True
    assert configuration.timezone == "America/New_York"
    assert configuration.postal_codes == ["10001"]
    assert configuration.duration_minutes == 60
    assert configuration.notice_minutes == 120
    assert configuration.cancellation_notice_minutes == 120
    assert {window.weekday for window in configuration.windows} == set(range(5))
    assert all(
        window.start.isoformat() == "09:00:00" and window.end.isoformat() == "17:00:00"
        for window in configuration.windows
    )
    assert len(configuration.teams) == 1
    assert configuration.teams[0].windows == configuration.windows
    assert schedule_audit_count == 1

    with migrated_database.connect() as connection:
        seeded_agency = connection.execute(
            select(Agency.slug, Agency.environment_kind).where(
                Agency.id == DEVELOPMENT_AGENCY_ID
            )
        ).one()
        agency_count = connection.scalar(
            select(func.count())
            .select_from(Agency)
            .where(Agency.id == DEVELOPMENT_AGENCY_ID)
        )
        actor_count = connection.scalar(
            select(func.count())
            .select_from(AppUser)
            .where(AppUser.id == DEVELOPMENT_ACTOR_USER_ID)
        )
        membership_count = connection.scalar(
            select(func.count())
            .select_from(AgencyMembership)
            .where(AgencyMembership.id == DEVELOPMENT_MEMBERSHIP_ID)
        )

    assert agency_count == 1
    assert actor_count == 1
    assert membership_count == 1
    assert seeded_agency.slug == DEVELOPMENT_AGENCY_SLUG
    assert seeded_agency.environment_kind == "DEVELOPMENT"


def test_development_seed_preserves_custom_schedule_and_other_businesses(
    migrated_database: Engine,
    database_settings: DatabaseSettings,
) -> None:
    settings = database_settings.model_copy(
        update={
            "app_environment": RuntimeEnvironment.DEVELOPMENT,
            "database_url": database_settings.runtime_database_url,
            "direct_database_url": None,
            "test_database_url": None,
        }
    )
    seed_development_foundation(settings)
    scheduling = SchedulingService(
        sessionmaker(bind=migrated_database, expire_on_commit=False)
    )
    current = scheduling.configuration(DEVELOPMENT_AGENCY_ID)
    configuration = ScheduleInput.model_validate(current["configuration"])
    updated = scheduling.configure(
        DEVELOPMENT_AGENCY_ID,
        ScheduleInput.model_validate(
            {
                **configuration.model_dump(mode="json"),
                "expected_version": current["version"],
                "enabled": False,
                "timezone": "America/Chicago",
                "postal_codes": ["60601"],
            }
        ),
        uuid4(),
    )
    with Session(migrated_database) as session, session.begin():
        other_business = Agency(
            name="Fictional business without a booking calendar",
            slug=f"unconfigured-calendar-{uuid4()}",
            environment_kind="DEVELOPMENT",
        )
        session.add(other_business)
        session.flush()
        other_business_id = other_business.id
        audit_count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.agency_id == DEVELOPMENT_AGENCY_ID,
                AuditEvent.event_type == "HVAC_SCHEDULE_CONFIGURED",
            )
        )

    result = seed_development_foundation(settings)

    assert result.business_schedule_created is False
    assert scheduling.configuration(DEVELOPMENT_AGENCY_ID) == updated
    assert scheduling.configuration(other_business_id) == {
        "version": 0,
        "configuration": None,
    }
    with Session(migrated_database) as session:
        current_audit_count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.agency_id == DEVELOPMENT_AGENCY_ID,
                AuditEvent.event_type == "HVAC_SCHEDULE_CONFIGURED",
            )
        )
    assert current_audit_count == audit_count


def test_development_seed_preserves_edited_and_inactive_faqs(
    migrated_database: Engine,
    database_settings: DatabaseSettings,
) -> None:
    settings = database_settings.model_copy(
        update={
            "app_environment": RuntimeEnvironment.DEVELOPMENT,
            "database_url": database_settings.runtime_database_url,
            "direct_database_url": None,
            "test_database_url": None,
        }
    )
    seed_development_foundation(settings, include_telephony=False)
    faq_id = DEVELOPMENT_APPROVED_FAQ_IDS[0]
    with Session(migrated_database) as session, session.begin():
        faq = session.get(AgencyApprovedFaq, faq_id)
        assert faq is not None
        faq.question = "What are the operator-approved office hours?"
        faq.normalized_question = "what are the operator approved office hours"
        faq.approved_answer = "Staff must confirm the current office hours."
        faq.status = "INACTIVE"
        receptionist = session.get(
            AgencyReceptionistSettings, DEVELOPMENT_RECEPTIONIST_SETTINGS_ID
        )
        assert receptionist is not None
        receptionist.escalation_message = (
            "Please ask the fictional staff for assistance."
        )
        session.flush()
        session.refresh(faq)
        edited_version = faq.row_version

    with patch(
        "insurance_operations.database.seed.configure_demo_telephony"
    ) as telephony:
        result = seed_development_foundation(settings, include_telephony=False)

    telephony.assert_not_called()
    assert result.approved_faqs_created == 0
    with Session(migrated_database) as session:
        preserved = session.get(AgencyApprovedFaq, faq_id)
        assert preserved is not None
        assert preserved.question == "What are the operator-approved office hours?"
        assert preserved.approved_answer == (
            "Staff must confirm the current office hours."
        )
        assert preserved.status == "INACTIVE"
        assert preserved.row_version == edited_version
        receptionist = session.get(
            AgencyReceptionistSettings, DEVELOPMENT_RECEPTIONIST_SETTINGS_ID
        )
        assert receptionist is not None
        assert receptionist.escalation_message == (
            "Please ask the fictional staff for assistance."
        )


def test_development_seed_configures_demo_telephony_idempotently(
    migrated_database: Engine,
    database_settings: DatabaseSettings,
) -> None:
    settings = DatabaseSettings.model_validate(
        {
            "app_environment": RuntimeEnvironment.DEVELOPMENT,
            "database_url": database_settings.runtime_database_url,
            "direct_database_url": None,
            "test_database_url": None,
            "database_ssl_mode": database_settings.database_ssl_mode,
            "demo_inbound_number_e164": "+15550100100",
            "demo_transfer_destination_e164": "+15550100200",
        }
    )

    first_result = seed_development_foundation(settings)
    second_result = seed_development_foundation(settings)

    assert first_result.call_policy_configured is True
    assert first_result.inbound_number_configured is True
    assert second_result.call_policy_configured is False
    assert second_result.inbound_number_configured is False

    with Session(migrated_database) as session:
        policy = session.get(AgencyCallPolicy, DEVELOPMENT_CALL_POLICY_ID)
        number = session.get(AgencyInboundNumber, DEVELOPMENT_INBOUND_NUMBER_ID)

    assert policy is not None
    assert policy.transfer_destination_e164 == "+15550100200"
    assert policy.max_concurrent_calls == 2
    assert policy.daily_call_limit == 10
    assert len(policy.availability_windows) == 7
    assert number is not None
    assert number.phone_number_e164 == "+15550100100"
    assert number.status == "ACTIVE"


@pytest.mark.parametrize(
    "environment",
    [RuntimeEnvironment.TEST, RuntimeEnvironment.PRODUCTION],
)
def test_development_seed_refuses_non_development_environments(
    database_settings: DatabaseSettings,
    environment: RuntimeEnvironment,
) -> None:
    settings = database_settings.model_copy(
        update={"app_environment": environment},
    )

    with pytest.raises(ValueError, match="APP_ENVIRONMENT=development"):
        seed_development_foundation(settings)
