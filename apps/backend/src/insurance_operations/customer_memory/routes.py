from collections.abc import Callable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.conversations.spoken import require_spoken_confirmation
from insurance_operations.customer_memory.schemas import (
    MemoryConsentInput, MemoryFactSaveInput, MemoryMutation, MemoryPairInput,
    MemoryReadbackInput, MemorySpokenSaveInput, memory_readback,
)
from insurance_operations.customer_memory.service import CustomerMemoryService, memory_error
from insurance_operations.settings import ApiSettings


def no_memory_cache(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def create_customer_memory_router(
    settings: ApiSettings, sessions: sessionmaker[Session],
    actor_dependency: Callable[..., ActorContext],
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(no_memory_cache)])
    service = CustomerMemoryService(sessions, settings)
    Actor = Annotated[ActorContext, Depends(actor_dependency)]

    @router.get("/memory")
    def view(actor: Actor) -> dict[str, object]:
        return service.view(actor)

    @router.post("/memory/consent", status_code=204)
    def consent(data: MemoryConsentInput, actor: Actor, request: Request) -> Response:
        service.set_consent(actor, data, data.enabled, UUID(request.state.correlation_id))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.post("/memory/delete", status_code=204)
    def erase(data: MemoryMutation, actor: Actor, request: Request) -> Response:
        service.set_consent(actor, data, None, UUID(request.state.correlation_id))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.post("/memory/facts", status_code=204)
    def save(data: MemoryFactSaveInput, actor: Actor, request: Request) -> Response:
        service.save(actor, data, UUID(request.state.correlation_id))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.post("/memory/facts/{key}/delete", status_code=204)
    def remove(key: str, data: MemoryMutation, actor: Actor, request: Request) -> Response:
        service.remove_fact(actor, key, data, UUID(request.state.correlation_id))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.post("/memory/whatsapp/link", status_code=204)
    def link(data: MemoryPairInput, actor: Actor, request: Request) -> Response:
        service.approve_pairing(actor, data, data.code, UUID(request.state.correlation_id))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.post("/memory/whatsapp/unlink", status_code=204)
    def unlink(data: MemoryMutation, actor: Actor, request: Request) -> Response:
        service.unlink(actor, data, UUID(request.state.correlation_id))
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    @router.post("/conversation-sessions/{session_id}/memory/context")
    def context(session_id: UUID, actor: Actor) -> dict[str, object]:
        service.enabled()
        return service.view(actor, context_only=True, browser_session_id=session_id)

    @router.post("/conversation-sessions/{session_id}/memory/readback")
    def readback(session_id: UUID, data: MemoryReadbackInput, actor: Actor) -> dict[str, object]:
        revision, intake_id = service.prepare(actor, session_id, data.facts)
        return {
            "readback": memory_readback(data.facts), "expected_revision": revision,
            "source_intake_id": str(intake_id), "request_id": str(uuid4()),
        }

    @router.post("/conversation-sessions/{session_id}/memory/remember", status_code=204)
    def remember(
        session_id: UUID, data: MemorySpokenSaveInput, actor: Actor, request: Request,
    ) -> Response:
        try:
            require_spoken_confirmation(
                data.transcript, memory_readback(data.facts), "remember these details"
            )
        except ValueError as error:
            raise memory_error("Read the full memory question and wait for a clear yes") from error
        service.save(actor, data, UUID(request.state.correlation_id), session_id=session_id)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router
