from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.database.models.conversation import (
    ConversationIntakeConfirmationReceipt,
)
from insurance_operations.errors import ApiError
from insurance_operations.hvac.schemas import (
    AppointmentView,
    AvailabilityResponse,
    PhoneAppointmentInput,
    PhoneAvailabilityInput,
    PhoneReservationInput,
    PhoneServiceRequestInput,
)
from insurance_operations.hvac.service import SchedulingService
from insurance_operations.telephony.phone_schemas import PhoneCallContext
from insurance_operations.telephony.phone_service import (
    require_phone_call,
    require_phone_session_context,
)


def create_hvac_phone_router(
    sessions: sessionmaker[Session], verify_tool: Callable[[str | None], None]
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/providers/elevenlabs/tools", include_in_schema=False
    )
    service = SchedulingService(sessions)

    def context(
        request: PhoneCallContext,
        authorization: str | None,
        request_id: UUID | None = None,
        appointment_id: UUID | None = None,
    ) -> UUID:
        verify_tool(authorization)
        with sessions() as session:
            conversation = require_phone_session_context(session, request)
            call = require_phone_call(session, request.inbound_call_id)
            if (
                conversation.agency_id != call.agency_id
                or conversation.authorization_expires_at <= datetime.now(UTC)
            ):
                raise ApiError(
                    status_code=409,
                    code="PHONE_CONTEXT_EXPIRED",
                    message="The phone session is not active",
                )
            if appointment_id:
                appointment = SchedulingService._appointment(
                    session, call.agency_id, appointment_id
                )
                request_id = appointment.service_request_id
            if request_id:
                row = SchedulingService._request(session, call.agency_id, request_id)
                if row.inbound_call_id != call.id:
                    raise ApiError(
                        status_code=404,
                        code="SERVICE_REQUEST_NOT_FOUND",
                        message="Service request not found",
                    )
            return call.agency_id

    @router.post("/service-request")
    def submit(
        request: Request,
        data: PhoneServiceRequestInput,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        agency_id = context(data, authorization)
        with sessions() as session:
            receipt = session.scalar(
                select(ConversationIntakeConfirmationReceipt).where(
                    ConversationIntakeConfirmationReceipt.inbound_call_id
                    == data.inbound_call_id,
                    ConversationIntakeConfirmationReceipt.agency_id == agency_id,
                )
            )
            if (
                receipt is None
                or receipt.full_name != data.customer.full_name
                or receipt.phone != data.customer.phone
            ):
                raise ApiError(
                    status_code=409,
                    code="READBACK_REQUIRED",
                    message=(
                        "Confirm the caller name and callback number "
                        "with confirm-intake first"
                    ),
                )
        request_id = service.create_request(
            agency_id, data, UUID(request.state.correlation_id), data.inbound_call_id
        )
        return {
            "service_request_id": str(request_id),
            "persisted": True,
            "human_attention_required": data.service.hazardous_condition,
        }

    @router.post("/availability", response_model=AvailabilityResponse)
    def availability(
        data: PhoneAvailabilityInput,
        authorization: Annotated[str | None, Header()] = None,
    ) -> AvailabilityResponse:
        agency_id = context(data, authorization)
        return service.availability(agency_id, data)

    @router.post("/reserve-appointment", response_model=AppointmentView)
    def reserve(
        request: Request,
        data: PhoneReservationInput,
        authorization: Annotated[str | None, Header()] = None,
    ) -> AppointmentView:
        agency_id = context(data, authorization, request_id=data.service_request_id)
        return service.reserve(agency_id, data, UUID(request.state.correlation_id))

    @router.post("/confirm-appointment", response_model=AppointmentView)
    def confirm(
        request: Request,
        data: PhoneAppointmentInput,
        authorization: Annotated[str | None, Header()] = None,
    ) -> AppointmentView:
        agency_id = context(data, authorization, appointment_id=data.appointment_id)
        return service.confirm(
            agency_id,
            data.appointment_id,
            data.explicit_confirmation,
            UUID(request.state.correlation_id),
        )

    return router
