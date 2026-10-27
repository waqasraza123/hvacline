from collections.abc import Callable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import Field

from insurance_operations.actors import ActorContext
from insurance_operations.conversations.spoken import require_spoken_confirmation
from insurance_operations.customer_memory.routes import no_memory_cache
from insurance_operations.customer_memory.schemas import (
    MemoryReadbackInput, MemorySpokenSaveInput, memory_readback,
)
from insurance_operations.customer_memory.service import CustomerMemoryService, memory_error
from insurance_operations.whatsapp.provider import spoken_history
from insurance_operations.whatsapp.service import WhatsAppService


class WhatsAppMemorySaveInput(MemorySpokenSaveInput):
    provider_history: str = Field(min_length=1, max_length=65_536)


def create_whatsapp_memory_router(
    calls: WhatsAppService, tool_dependency: Callable[..., UUID],
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(no_memory_cache)])
    memory = CustomerMemoryService(calls.sessions, calls.settings)
    Binding = Annotated[UUID, Depends(tool_dependency)]

    def verified_actor(binding_id: UUID) -> ActorContext:
        actor = memory.whatsapp_actor(binding_id)
        if actor is None:
            raise memory_error("Link this caller from your signed-in Memory settings first")
        return actor

    @router.post("/sessions/{session_id}/memory/context")
    def context(session_id: UUID, binding_id: Binding, request: Request) -> dict[str, object]:
        with calls.sessions() as session:
            binding, _ = calls.require_binding(
                session, binding_id, request.state.whatsapp_conversation_id
            )
            if binding.session_id != session_id:
                raise memory_error("The memory session does not match this call")
        actor = memory.whatsapp_actor(binding_id)
        if actor is None:
            return {"summary": "", "references": [], "identity_verified": False}
        return memory.view(actor, context_only=True, whatsapp_binding_id=binding_id)

    @router.post("/sessions/{session_id}/memory/pair")
    def pair(session_id: UUID, binding_id: Binding, request: Request) -> dict[str, object]:
        with calls.sessions() as session:
            binding, actor = calls.require_binding(
                session, binding_id, request.state.whatsapp_conversation_id
            )
            calls.require_session(session, binding, actor, session_id)
        return {
            "code": memory.begin_pairing(binding_id),
            "instructions": (
                "Enter this code in your signed-in HVACLine Memory settings "
                "to approve linking this WhatsApp caller. Never provide your password."
            ),
        }

    @router.post("/sessions/{session_id}/memory/readback")
    def readback(
        session_id: UUID, binding_id: Binding, data: MemoryReadbackInput,
    ) -> dict[str, object]:
        actor = verified_actor(binding_id)
        revision, intake_id = memory.prepare(
            actor, session_id, data.facts, whatsapp_binding_id=binding_id
        )
        return {
            "readback": memory_readback(data.facts), "expected_revision": revision,
            "source_intake_id": str(intake_id), "request_id": str(uuid4()),
        }

    @router.post("/sessions/{session_id}/memory/remember", status_code=204)
    def remember(
        session_id: UUID, binding_id: Binding, data: WhatsAppMemorySaveInput,
        request: Request,
    ) -> Response:
        actor = verified_actor(binding_id)
        try:
            require_spoken_confirmation(
                spoken_history(data.provider_history), memory_readback(data.facts),
                "remember these details",
            )
        except ValueError as error:
            raise memory_error("Read the full memory question and wait for a clear yes") from error
        memory.save(
            actor, data, UUID(request.state.correlation_id), session_id=session_id,
            whatsapp=True, whatsapp_binding_id=binding_id,
        )
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router
