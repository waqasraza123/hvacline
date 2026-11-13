from dataclasses import dataclass
from uuid import UUID

import phonenumbers
from sqlalchemy import Text, cast, exists, or_, select
from sqlalchemy.orm import Session

from insurance_operations.database.models.booking_integrations import CalendarBooking
from insurance_operations.database.models.conversation import (
    ConversationIntake,
    ConversationSession,
)
from insurance_operations.database.models.customer import Customer
from insurance_operations.database.models.hvac import (
    Appointment,
    BusinessSchedule,
    HvacServiceRequest,
)
from insurance_operations.database.models.lead import AgencyLead, LeadHandoffRequest
from insurance_operations.database.models.operations import AuditEvent
from insurance_operations.ghl.provider import GhlError
from insurance_operations.ghl.schemas import Outcome


@dataclass(frozen=True)
class LeadProjection:
    name: str
    email: str | None
    phone: str | None
    summary: str
    outcome: Outcome
    booking: str

    def contact_values(self) -> dict[str, object]:
        values: dict[str, object] = {"name": self.name, "source": "HVACLine"}
        if self.email:
            values["email"] = self.email
        if self.phone:
            values["phone"] = self.phone
        return values


def project_lead(session: Session, agency_id: UUID, lead_id: UUID) -> LeadProjection:
    row = session.execute(
        select(AgencyLead, Customer, ConversationSession)
        .join(
            Customer,
            (Customer.id == AgencyLead.customer_id)
            & (Customer.agency_id == AgencyLead.agency_id),
        )
        .join(
            ConversationIntake,
            (ConversationIntake.id == AgencyLead.conversation_intake_id)
            & (ConversationIntake.agency_id == AgencyLead.agency_id),
        )
        .join(
            ConversationSession,
            (ConversationSession.id == ConversationIntake.conversation_session_id)
            & (ConversationSession.agency_id == ConversationIntake.agency_id),
        )
        .where(AgencyLead.agency_id == agency_id, AgencyLead.id == lead_id)
    ).one_or_none()
    if row is None:
        raise GhlError("GHL_LOCAL_LEAD_UNAVAILABLE")
    lead, customer, conversation = row
    if lead.status == "ARCHIVED" or customer.archived_at:
        raise GhlError("GHL_LOCAL_LEAD_UNAVAILABLE")
    phone = None
    if customer.phone:
        try:
            number = phonenumbers.parse(customer.phone, customer.country_code)
            if not phonenumbers.is_valid_number(number) or number.extension:
                raise ValueError
            phone = phonenumbers.format_number(
                number, phonenumbers.PhoneNumberFormat.E164
            )
        except (phonenumbers.NumberParseException, ValueError):
            raise GhlError("GHL_PHONE_FORMAT_INVALID") from None
    request = session.scalar(
        select(HvacServiceRequest).where(
            HvacServiceRequest.agency_id == agency_id,
            or_(
                HvacServiceRequest.conversation_session_id == conversation.id,
                HvacServiceRequest.inbound_call_id == conversation.inbound_call_id
                if conversation.inbound_call_id
                else False,
            ),
        )
    )
    handoff = session.scalar(
        select(LeadHandoffRequest.id)
        .where(
            LeadHandoffRequest.agency_id == agency_id,
            LeadHandoffRequest.lead_id == lead_id,
            LeadHandoffRequest.status.in_(["REQUESTED", "ACKNOWLEDGED"]),
        )
        .limit(1)
    )
    outcome: Outcome = "attention" if handoff else "new"
    booking = "No confirmed appointment."
    if request:
        appointments = session.scalars(
            select(Appointment)
            .where(
                Appointment.agency_id == agency_id,
                Appointment.service_request_id == request.id,
                Appointment.status == "CONFIRMED",
            )
            .order_by(Appointment.starts_at.desc())
            .limit(2)
        ).all()
        if len(appointments) > 1:
            raise GhlError("GHL_MULTIPLE_ACTIVE_APPOINTMENTS")
        appointment = appointments[0] if appointments else None
        if appointment:
            outcome = "booked"
            binding = session.get(CalendarBooking, appointment.id)
            if (
                binding
                and binding.agency_id == agency_id
                and (binding.status == "ATTENTION" or binding.last_error)
            ):
                outcome = "attention"
            schedule = session.get(BusinessSchedule, agency_id)
            timezone = schedule.configuration.get("timezone") if schedule else None
            booking = (
                f"Appointment: {appointment.id}\nStatus: CONFIRMED\n"
                f"Start: {appointment.starts_at.isoformat()}\nEnd: {appointment.ends_at.isoformat()}\n"
                f"Timezone: {timezone or 'UTC'}\nTeam: {appointment.team_key}"
            )
        else:
            cancelled = session.scalar(
                select(Appointment)
                .where(
                    Appointment.agency_id == agency_id,
                    Appointment.service_request_id == request.id,
                    Appointment.status == "CANCELLED",
                    exists(
                        select(AuditEvent.id).where(
                            AuditEvent.agency_id == agency_id,
                            AuditEvent.event_type.in_(
                                [
                                    "HVAC_APPOINTMENT_CONFIRMED",
                                    "HVAC_APPOINTMENT_RESCHEDULED",
                                ]
                            ),
                            AuditEvent.details["appointment_id"].astext
                            == cast(Appointment.id, Text),
                        )
                    ),
                )
                .order_by(Appointment.starts_at.desc())
                .limit(1)
            )
            if cancelled:
                outcome = "cancelled"
                booking = f"Appointment: {cancelled.id}\nStatus: CANCELLED\nFormer start: {cancelled.starts_at.isoformat()}"
        if (
            handoff
            or request.service_details.get("hazardous_condition")
            or request.status in {"HANDOFF_REQUESTED", "CALLBACK_REQUESTED"}
        ):
            outcome = "attention"
    source = "website" if conversation.website_id else conversation.channel.lower()
    summary = f"Source: {source}\nUrgency: {lead.urgency}\n{lead.summary}"
    return LeadProjection(
        name=customer.full_name,
        email=customer.normalized_email,
        phone=phone,
        summary=summary,
        outcome=outcome,
        booking=booking,
    )
