from dataclasses import dataclass

from insurance_operations.database.models.approved_faq import (
    AgencyApprovedFaq,
    ApprovedFaqStatus,
)
from insurance_operations.database.models.base import Base
from insurance_operations.database.models.booking_integrations import (
    BookingEmailEvent,
    BookingNotification,
    CalendarAuthorization,
    CalendarBooking,
    CalendarConnection,
)
from insurance_operations.database.models.conversation import (
    ConversationChannel,
    ConversationIntake,
    ConversationIntakeConfirmationReceipt,
    ConversationSession,
)
from insurance_operations.database.models.customer import Customer
from insurance_operations.database.models.customer_account import (
    CustomerAccount,
    CustomerAuthLimit,
    CustomerLoginSession,
)
from insurance_operations.database.models.customer_mfa import (
    CustomerMfaChallenge, CustomerMfaFactor, CustomerMfaRecoveryCode,
)
from insurance_operations.database.models.customer_memory import (
    CustomerMemoryFact, CustomerMemoryPairing, CustomerMemoryPolicy,
    CustomerMemorySummary, CustomerWhatsAppIdentity,
)
from insurance_operations.database.models.homepage_chat import (
    HomepageChatDailyUsage,
    HomepageChatVisitor,
)
from insurance_operations.database.models.hvac import (
    Appointment,
    BusinessSchedule,
    HvacServiceRequest,
)
from insurance_operations.database.models.identity import (
    Agency,
    AgencyMembership,
    AppUser,
)
from insurance_operations.database.models.lead import (
    AgencyLead,
    HandoffContactMethod,
    HandoffRequestKind,
    HandoffStatus,
    LeadHandoffRequest,
    LeadStatus,
    LeadUrgency,
)
from insurance_operations.database.models.operations import (
    AuditEvent,
    IdempotencyRecord,
)
from insurance_operations.database.models.receptionist import (
    AgencyReceptionistSettings,
)
from insurance_operations.database.models.telephony import (
    AgencyCallPolicy,
    AgencyInboundNumber,
    InboundCall,
    InboundCallEvent,
    InboundCallStatus,
    InboundNumberStatus,
)
from insurance_operations.database.models.whatsapp import WhatsAppConversation


@dataclass(frozen=True)
class TableOwnership:
    module: str
    agency_column: str | None


TABLE_OWNERSHIP = {
    "homepage_chat_visitors": TableOwnership(
        module="homepage_chat", agency_column="agency_id"
    ),
    "homepage_chat_daily_usage": TableOwnership(
        module="homepage_chat", agency_column="agency_id"
    ),
    "customer_mfa_factors": TableOwnership(module="customer_access", agency_column="agency_id"),
    "customer_mfa_challenges": TableOwnership(module="customer_access", agency_column="agency_id"),
    "customer_mfa_recovery_codes": TableOwnership(module="customer_access", agency_column="agency_id"),
    "customer_memory_policies": TableOwnership(module="customer_memory", agency_column="agency_id"),
    "customer_memory_facts": TableOwnership(module="customer_memory", agency_column="agency_id"),
    "customer_memory_summaries": TableOwnership(module="customer_memory", agency_column="agency_id"),
    "customer_whatsapp_identities": TableOwnership(module="customer_memory", agency_column="agency_id"),
    "customer_memory_pairings": TableOwnership(module="customer_memory", agency_column="agency_id"),
    "whatsapp_conversations": TableOwnership(
        module="conversations", agency_column="agency_id"
    ),
    "booking_email_events": TableOwnership(module="notifications", agency_column=None),
    "calendar_connections": TableOwnership(module="hvac", agency_column="agency_id"),
    "calendar_authorizations": TableOwnership(module="hvac", agency_column="agency_id"),
    "calendar_bookings": TableOwnership(module="hvac", agency_column="agency_id"),
    "booking_notifications": TableOwnership(
        module="notifications", agency_column="agency_id"
    ),
    "customer_accounts": TableOwnership(
        module="customer_access", agency_column="agency_id"
    ),
    "customer_login_sessions": TableOwnership(
        module="customer_access", agency_column=None
    ),
    "customer_auth_limits": TableOwnership(
        module="customer_access", agency_column=None
    ),
    "business_schedules": TableOwnership(module="hvac", agency_column="agency_id"),
    "hvac_service_requests": TableOwnership(module="hvac", agency_column="agency_id"),
    "hvac_appointments": TableOwnership(module="hvac", agency_column="agency_id"),
    "agencies": TableOwnership(module="identity", agency_column=None),
    "app_users": TableOwnership(module="identity", agency_column=None),
    "agency_memberships": TableOwnership(
        module="identity",
        agency_column="agency_id",
    ),
    "customers": TableOwnership(module="customers", agency_column="agency_id"),
    "conversation_sessions": TableOwnership(
        module="conversations",
        agency_column="agency_id",
    ),
    "conversation_intakes": TableOwnership(
        module="conversations",
        agency_column="agency_id",
    ),
    "conversation_intake_confirmation_receipts": TableOwnership(
        module="conversations",
        agency_column="agency_id",
    ),
    "agency_receptionist_settings": TableOwnership(
        module="receptionist",
        agency_column="agency_id",
    ),
    "agency_approved_faqs": TableOwnership(
        module="approved_faqs",
        agency_column="agency_id",
    ),
    "agency_leads": TableOwnership(module="leads", agency_column="agency_id"),
    "lead_handoff_requests": TableOwnership(
        module="leads",
        agency_column="agency_id",
    ),
    "agency_call_policies": TableOwnership(
        module="telephony",
        agency_column="agency_id",
    ),
    "agency_inbound_numbers": TableOwnership(
        module="telephony",
        agency_column="agency_id",
    ),
    "inbound_calls": TableOwnership(
        module="telephony",
        agency_column="agency_id",
    ),
    "inbound_call_events": TableOwnership(
        module="telephony",
        agency_column="agency_id",
    ),
    "audit_events": TableOwnership(module="audit", agency_column="agency_id"),
    "idempotency_records": TableOwnership(
        module="idempotency",
        agency_column="agency_id",
    ),
}

__all__ = [
    "HomepageChatDailyUsage",
    "HomepageChatVisitor",
    "TABLE_OWNERSHIP",
    "Agency",
    "AgencyApprovedFaq",
    "AgencyCallPolicy",
    "AgencyInboundNumber",
    "AgencyLead",
    "AgencyMembership",
    "AgencyReceptionistSettings",
    "AppUser",
    "Appointment",
    "ApprovedFaqStatus",
    "AuditEvent",
    "Base",
    "BookingEmailEvent",
    "BookingNotification",
    "CalendarAuthorization",
    "CalendarBooking",
    "CalendarConnection",
    "BusinessSchedule",
    "ConversationChannel",
    "ConversationIntake",
    "ConversationIntakeConfirmationReceipt",
    "ConversationSession",
    "Customer",
    "CustomerAccount",
    "CustomerMfaChallenge",
    "CustomerMfaFactor",
    "CustomerMfaRecoveryCode",
    "CustomerMemoryFact",
    "CustomerMemoryPairing",
    "CustomerMemoryPolicy",
    "CustomerMemorySummary",
    "CustomerWhatsAppIdentity",
    "CustomerAuthLimit",
    "CustomerLoginSession",
    "HandoffContactMethod",
    "HandoffRequestKind",
    "HandoffStatus",
    "HvacServiceRequest",
    "IdempotencyRecord",
    "InboundCall",
    "InboundCallEvent",
    "InboundCallStatus",
    "InboundNumberStatus",
    "LeadHandoffRequest",
    "LeadStatus",
    "LeadUrgency",
    "TableOwnership",
    "WhatsAppConversation",
]
