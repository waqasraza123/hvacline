import json
import time
from collections.abc import Callable
from typing import Protocol

from websockets.sync.client import connect

from insurance_operations.conversations.providers.elevenlabs import (
    ElevenLabsConversationProvider,
)


class HomepageProviderError(Exception):
    def __init__(self, *, message_sent: bool) -> None:
        super().__init__("The homepage conversation could not finish")
        self.message_sent = message_sent


class HomepageReplyProvider(Protocol):
    def reply(self, message: str, lookup: Callable[[str], str]) -> str: ...


class ElevenLabsHomepageProvider:
    def __init__(self, api_key: str, agent_id: str) -> None:
        self.api_key = api_key
        self.agent_id = agent_id

    def reply(self, message: str, lookup: Callable[[str], str]) -> str:
        deadline = time.monotonic() + 20
        message_sent = False
        provider = ElevenLabsConversationProvider(
            api_key=self.api_key, agent_id=self.agent_id
        )
        try:
            grant = provider.authorize_session(input_mode="TEXT")
            with connect(
                grant.credential,
                open_timeout=min(5, self._remaining(deadline)),
                close_timeout=1,
                max_size=65_536,
            ) as socket:
                socket.send(
                    json.dumps(
                        {
                            "type": "conversation_initiation_client_data",
                            "conversation_config_override": {
                                "conversation": {"text_only": True}
                            },
                            "dynamic_variables": {"homepage_guest": True},
                        }
                    )
                )
                responses: list[str] = []
                calls = 0
                initialized = False
                while True:
                    event = json.loads(socket.recv(timeout=self._remaining(deadline)))
                    if not isinstance(event, dict):
                        raise ValueError("Invalid provider event")
                    kind = event.get("type")
                    if kind == "ping":
                        socket.send(
                            json.dumps(
                                {
                                    "type": "pong",
                                    "event_id": event["ping_event"]["event_id"],
                                }
                            )
                        )
                    elif kind == "conversation_initiation_metadata":
                        initialized = True
                    elif (
                        kind == "agent_response_complete"
                        and initialized
                        and not message_sent
                    ):
                        message_sent = True
                        socket.send(
                            json.dumps({"type": "user_message", "text": message})
                        )
                    elif kind == "client_tool_call":
                        call = event["client_tool_call"]
                        calls += 1
                        if calls > 4:
                            raise ValueError("Too many guest tool requests")
                        parameters = call.get("parameters", {})
                        query = (
                            parameters.get("query")
                            if isinstance(parameters, dict)
                            else None
                        )
                        if (
                            call.get("tool_name") == "lookup_approved_faq"
                            and isinstance(query, str)
                            and 0 < len(query.strip()) <= 1000
                        ):
                            result = lookup(query.strip())
                            allowed = True
                        else:
                            allowed = False
                            result = json.dumps(
                                {
                                    "available": False,
                                    "code": "SIGN_IN_REQUIRED",
                                    "message": "Sign in to continue with booking or account services. No action was taken.",
                                }
                            )
                        socket.send(
                            json.dumps(
                                {
                                    "type": "client_tool_result",
                                    "tool_call_id": call["tool_call_id"],
                                    "result": result,
                                    "is_error": not allowed,
                                }
                            )
                        )
                    elif kind == "agent_response" and message_sent:
                        response = event.get("agent_response_event", {}).get(
                            "agent_response"
                        )
                        if not isinstance(response, str) or len(response) > 4000:
                            raise ValueError("Invalid guest response")
                        if response.strip():
                            responses.append(response.strip())
                            if sum(len(part) + 2 for part in responses) > 4002:
                                raise ValueError("Guest response is too long")
                    elif kind == "agent_response_complete" and message_sent:
                        reply = "\n\n".join(responses)
                        if not reply or len(reply) > 4000:
                            raise ValueError("Missing complete guest response")
                        return reply
                    elif kind in {"error", "client_error"}:
                        raise ValueError("Provider rejected guest conversation")
        except Exception as error:
            raise HomepageProviderError(message_sent=message_sent) from error
        finally:
            provider.close()

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Guest conversation deadline reached")
        return remaining
