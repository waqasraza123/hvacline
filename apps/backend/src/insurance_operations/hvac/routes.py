from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.hvac import Appointment, HvacServiceRequest
from insurance_operations.database.models.lead import LeadHandoffRequest
from insurance_operations.database.models.telephony import InboundCall
from insurance_operations.hvac.schemas import (
    AppointmentAction,
    AppointmentView,
    AvailabilityInput,
    AvailabilityResponse,
    RescheduleInput,
    ReservationInput,
    ScheduleInput,
    ServiceRequestInput,
)
from insurance_operations.hvac.service import SchedulingService, unavailable


def create_hvac_router(
    sessions: sessionmaker[Session], actor_dependency: Callable[..., ActorContext]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/development/hvac")
    service = SchedulingService(sessions)
    Actor = Annotated[ActorContext, Depends(actor_dependency)]

    @router.get("/schedule")
    def get_schedule(actor: Actor) -> dict[str, object]:
        return service.configuration(actor.agency_id)

    @router.put("/schedule")
    def configure(
        data: ScheduleInput, request: Request, actor: Actor
    ) -> dict[str, object]:
        return service.configure(
            actor.agency_id, data, UUID(request.state.correlation_id)
        )

    @router.post("/availability", response_model=AvailabilityResponse)
    def availability(data: AvailabilityInput, actor: Actor) -> AvailabilityResponse:
        return service.availability(actor.agency_id, data)

    @router.post("/service-requests")
    def create_service_request(
        data: ServiceRequestInput, request: Request, actor: Actor
    ) -> dict[str, str]:
        return {
            "id": str(
                service.create_request(
                    actor.agency_id, data, UUID(request.state.correlation_id)
                )
            )
        }

    @router.get("/operations")
    def operations(actor: Actor, response: Response) -> dict[str, object]:
        response.headers["Cache-Control"] = "no-store"
        with sessions() as session:
            requests = session.scalars(
                select(HvacServiceRequest)
                .where(HvacServiceRequest.agency_id == actor.agency_id)
                .order_by(HvacServiceRequest.confirmed_at.desc())
                .limit(100)
            ).all()
            appointments = session.scalars(
                select(Appointment)
                .where(Appointment.agency_id == actor.agency_id)
                .order_by(Appointment.starts_at.desc())
                .limit(100)
            ).all()
            calls = session.scalars(
                select(InboundCall)
                .where(InboundCall.agency_id == actor.agency_id)
                .order_by(InboundCall.received_at.desc())
                .limit(100)
            ).all()
            handoffs = session.scalars(
                select(LeadHandoffRequest)
                .where(
                    LeadHandoffRequest.agency_id == actor.agency_id,
                    LeadHandoffRequest.status.in_(["REQUESTED", "ACKNOWLEDGED"]),
                )
                .order_by(LeadHandoffRequest.created_at.desc())
                .limit(100)
            ).all()
            return {
                "calls": [
                    {
                        "id": str(row.id),
                        "status": row.status,
                        "received_at": row.received_at.isoformat(),
                        "caller_number": row.caller_number_e164,
                    }
                    for row in calls
                ],
                "handoffs": [
                    {
                        "id": str(row.id),
                        "kind": row.request_kind,
                        "status": row.status,
                        "reason": row.reason,
                        "lead_id": str(row.lead_id),
                    }
                    for row in handoffs
                ],
                "service_requests": [
                    {
                        "id": str(row.id),
                        "inbound_call_id": str(row.inbound_call_id)
                        if row.inbound_call_id
                        else None,
                        "customer": row.customer_details,
                        "service": row.service_details,
                        "status": row.status,
                        "confirmed_at": row.confirmed_at.isoformat(),
                    }
                    for row in requests
                ],
                "appointments": [
                    AppointmentView.model_validate(row).model_dump(mode="json")
                    for row in appointments
                ],
            }

    @router.post("/reservations", response_model=AppointmentView)
    def reserve(
        data: ReservationInput, request: Request, actor: Actor
    ) -> AppointmentView:
        return service.reserve(
            actor.agency_id, data, UUID(request.state.correlation_id)
        )

    @router.post(
        "/appointments/{appointment_id}/confirm", response_model=AppointmentView
    )
    def confirm(
        appointment_id: UUID, data: AppointmentAction, request: Request, actor: Actor
    ) -> AppointmentView:
        return service.confirm(
            actor.agency_id,
            appointment_id,
            data.explicit_confirmation,
            UUID(request.state.correlation_id),
        )

    @router.post(
        "/appointments/{appointment_id}/cancel", response_model=AppointmentView
    )
    def cancel(
        appointment_id: UUID, data: AppointmentAction, request: Request, actor: Actor
    ) -> AppointmentView:
        if not data.explicit_confirmation:
            raise unavailable("Confirm the cancellation before continuing.")
        return service.cancel(
            actor.agency_id, appointment_id, UUID(request.state.correlation_id)
        )

    @router.post(
        "/appointments/{appointment_id}/reschedule", response_model=AppointmentView
    )
    def reschedule(
        appointment_id: UUID, data: RescheduleInput, request: Request, actor: Actor
    ) -> AppointmentView:
        if not data.explicit_confirmation:
            raise unavailable("Confirm the reschedule before continuing.")
        return service.reschedule(
            actor.agency_id, appointment_id, data, UUID(request.state.correlation_id)
        )

    return router
