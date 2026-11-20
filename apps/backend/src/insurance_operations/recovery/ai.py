import http.client
import ipaddress
import json
import socket
import ssl
import time
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from insurance_operations.actors import ActorContext
from insurance_operations.database.models.identity import Agency
from insurance_operations.database.models.recovery import RecoveryAiConnection
from insurance_operations.errors import ApiError
from insurance_operations.recovery.domain import audit
from insurance_operations.recovery.schemas import AiInput
from insurance_operations.settings import DatabaseSettings


def problem(code: str, message: str, status: int = 409) -> ApiError:
    return ApiError(status_code=status, code=code, message=message, headers={"Cache-Control": "no-store"})


def endpoint_for(provider: str, endpoint: str, allowed_origins: list[str]) -> str:
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError:
        raise problem("AI_ENDPOINT_REJECTED", "Enter a valid HTTPS provider endpoint.") from None
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
        or parsed.query or parsed.fragment or port not in {None, 443} or parsed.path.rstrip("/") != "/v1"):
        raise problem("AI_ENDPOINT_REJECTED", "Use an HTTPS endpoint on port 443 ending in /v1, without credentials, queries or fragments.")
    origin = f"https://{parsed.hostname}"
    if provider == "OPENAI" and origin != "https://api.openai.com":
        raise problem("AI_ENDPOINT_REJECTED", "OpenAI requires its official API endpoint.")
    if provider == "OPENAI_COMPATIBLE" and origin not in allowed_origins:
        raise problem("AI_ENDPOINT_NOT_ALLOWED", "Ask the administrator to allow this exact public HTTPS origin in backend configuration.")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise problem("AI_ENDPOINT_REJECTED", "A public DNS hostname is required.")
    if parsed.hostname.endswith((".localhost", ".local", ".internal")) or parsed.hostname == "localhost":
        raise problem("AI_ENDPOINT_REJECTED", "Internal destinations are unsupported.")
    return origin + "/v1"


def public_addresses(host: str) -> list[str]:
    try:
        addresses = sorted({row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
    except OSError:
        raise problem("AI_DNS_FAILED", "The provider hostname could not be resolved.", 503) from None
    if not addresses or any(not address_allowed(address) for address in addresses):
        raise problem("AI_ENDPOINT_REJECTED", "Every resolved provider address must be publicly routable.")
    return addresses


def address_allowed(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if not ip.is_global or ip.is_multicast or ip.is_reserved:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo):
        return False
    return True


class PinnedHttpsConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str) -> None:
        super().__init__(host, 443, timeout=8, context=ssl.create_default_context())
        self.address = address

    def connect(self) -> None:
        connection = socket.create_connection((self.address, 443), timeout=8)
        try:
            self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
        except Exception:
            connection.close()
            raise


def chat_completion(endpoint: str, key: str, model: str, prompt: str, *, test: bool = False) -> str:
    host = urlsplit(endpoint).hostname
    if host is None:
        raise problem("AI_ENDPOINT_REJECTED", "Provider hostname unavailable.")
    addresses = public_addresses(host)
    connection = PinnedHttpsConnection(host, addresses[0])
    payload = json.dumps({"model": model, "messages": [{"role": "system", "content": "You assist HVAC staff. Never claim a booking, price, slot, delivery, call or external action occurred. No tools are available."}, {"role": "user", "content": prompt}], "max_tokens": 16 if test else 300, "stream": False})
    deadline = time.monotonic() + 12
    try:
        connection.request("POST", "/v1/chat/completions", payload.encode(), {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Type", "").split(";")[0].strip() != "application/json":
            raise problem("AI_CONNECTION_REJECTED", "The provider rejected this model or credential. Only text Chat Completions are supported.", 503)
        content = bytearray()
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError
            chunk = response.read(4096)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > 65536:
                raise ValueError
        data = json.loads(content)
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ValueError
        answer = message.get("content")
        if message.get("tool_calls") or message.get("function_call") or not isinstance(answer, str) or not 1 <= len(answer.strip()) <= 4000:
            raise ValueError
        return answer.strip()
    except ApiError:
        raise
    except (OSError, http.client.HTTPException, ValueError, TypeError, KeyError, IndexError):
        raise problem("AI_CONNECTION_FAILED", "The provider did not return a supported text response. No fallback provider was used.", 503) from None
    finally:
        connection.close()


class TextCompletionProvider(Protocol):
    def complete(self, endpoint: str, key: str, model: str, prompt: str, *, test: bool) -> str: ...


class OpenAiCompatibleTextProvider:
    def complete(self, endpoint: str, key: str, model: str, prompt: str, *, test: bool) -> str:
        return chat_completion(endpoint, key, model, prompt, test=test)


class RecoveryAiService:
    def __init__(self, sessions: sessionmaker[Session], settings: DatabaseSettings, provider: TextCompletionProvider | None = None) -> None:
        self.sessions, self.settings = sessions, settings
        self.provider = provider or OpenAiCompatibleTextProvider()

    def cipher(self) -> Fernet:
        key = self.settings.recovery_token_encryption_key
        if key is None:
            raise problem("AI_ENCRYPTION_UNAVAILABLE", "Set the backend recovery encryption key before saving credentials.")
        return Fernet(key.get_secret_value().encode())

    def encrypt(self, agency_id: UUID, provider: str, endpoint: str, key: str) -> str:
        return self.cipher().encrypt(json.dumps({"agency": str(agency_id), "provider": provider, "endpoint": endpoint, "key": key}).encode()).decode()

    def decrypt(self, row: RecoveryAiConnection) -> str:
        try:
            data = json.loads(self.cipher().decrypt((row.credential_ciphertext or "").encode()))
            if data["agency"] != str(row.agency_id) or data["provider"] != row.provider or data["endpoint"] != row.endpoint or not isinstance(data["key"], str):
                raise ValueError
            return str(data["key"])
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise problem("AI_CREDENTIAL_UNAVAILABLE", "The stored credential cannot be decrypted. Update it before continuing.") from None

    def view(self, row: RecoveryAiConnection | None) -> dict[str, object]:
        return {"provider": row.provider if row else None, "model": row.model if row else "", "endpoint": row.endpoint if row else "https://api.openai.com/v1", "status": row.status if row else "NOT_CONFIGURED",
            "row_version": row.row_version if row else 0, "has_credential": bool(row and row.credential_ciphertext), "last_tested_at": row.last_tested_at.isoformat() if row and row.last_tested_at else None,
            "last_error": row.last_error if row else None, "capabilities": ["STAFF_TEXT_DRAFTS"] if row and row.status == "CONNECTED" else [],
            "live_recovery_voice_supported": False, "voice_status": "Existing ElevenLabs browser/inbound voice is configured separately; custom-model recovery calling is unsupported.",
            "encryption_configured": self.settings.recovery_token_encryption_key is not None}

    def status(self, actor: ActorContext) -> dict[str, object]:
        with self.sessions() as session:
            return self.view(session.get(RecoveryAiConnection, actor.agency_id))

    def save(self, actor: ActorContext, data: AiInput) -> dict[str, object]:
        endpoint = endpoint_for(data.provider, data.endpoint, self.settings.recovery_ai_allowed_origins)
        with self.sessions() as session, session.begin():
            session.scalar(select(Agency.id).where(Agency.id == actor.agency_id).with_for_update())
            row = session.get(RecoveryAiConnection, actor.agency_id, with_for_update=True)
            if data.expected_row_version != (row.row_version if row else 0):
                raise problem("ROW_VERSION_CONFLICT", "The AI configuration changed. Refresh before saving.")
            if data.api_key is None:
                if not row or row.status == "REVOKED" or row.provider != data.provider or row.endpoint != endpoint:
                    raise problem("AI_CREDENTIAL_REQUIRED", "Enter a credential for this provider and endpoint.")
                key = self.decrypt(row)
            else:
                key = data.api_key.get_secret_value()
            ciphertext = self.encrypt(actor.agency_id, data.provider, endpoint, key)
            if row is None:
                row = RecoveryAiConnection(agency_id=actor.agency_id)
                session.add(row)
            row.provider, row.model, row.endpoint, row.credential_ciphertext = data.provider, data.model, endpoint, ciphertext
            row.status, row.last_error, row.last_tested_at = "UNTESTED", None, None
            session.flush()
            session.refresh(row)
            audit(session, actor.agency_id, "RECOVERY_AI_SAVED", {"provider": row.provider, "status": row.status}, actor.app_user_id)
            return self.view(row)

    def revoke(self, actor: ActorContext, expected: int) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            row = session.get(RecoveryAiConnection, actor.agency_id, with_for_update=True)
            if not row or row.row_version != expected:
                raise problem("ROW_VERSION_CONFLICT", "Refresh AI configuration before revoking.")
            row.credential_ciphertext, row.status, row.last_error = None, "REVOKED", None
            session.flush()
            session.refresh(row)
            audit(session, actor.agency_id, "RECOVERY_AI_REVOKED", {"status": "REVOKED"}, actor.app_user_id)
            return self.view(row)

    def generate(self, actor: ActorContext, expected: int, prompt: str, *, test: bool) -> dict[str, object]:
        with self.sessions() as session, session.begin():
            row = session.get(RecoveryAiConnection, actor.agency_id, with_for_update=True)
            if not row or row.row_version != expected or row.status == "REVOKED":
                raise problem("ROW_VERSION_CONFLICT", "Refresh the AI configuration before continuing.")
            if not test and row.status != "CONNECTED":
                raise problem("AI_MODEL_NOT_CONNECTED", "Test the connection before requesting text assistance.")
            if row.last_tested_at and row.last_tested_at > datetime.now(UTC) - timedelta(seconds=30):
                raise problem("AI_REQUEST_RATE_LIMITED", "Wait 30 seconds before another model request.", 429)
            endpoint = endpoint_for(row.provider, row.endpoint, self.settings.recovery_ai_allowed_origins)
            model, key = row.model, self.decrypt(row)
            row.last_tested_at = datetime.now(UTC)
            session.flush()
            session.refresh(row)
            version = row.row_version
        result, failure = None, None
        try:
            result = self.provider.complete(endpoint, key, model, prompt, test=test)
        except ApiError as error:
            failure = error
        with self.sessions() as session, session.begin():
            row = session.get(RecoveryAiConnection, actor.agency_id, with_for_update=True)
            if not row or row.row_version != version:
                raise problem("AI_CONFIGURATION_CHANGED", "Configuration changed during the request. Discarded the previous result.")
            row.status, row.last_error = ("ERROR", failure.code) if failure else ("CONNECTED", None)
            audit(session, actor.agency_id, "RECOVERY_AI_TESTED" if test else "RECOVERY_AI_DRAFTED", {"status": row.status}, actor.app_user_id)
            session.flush()
            session.refresh(row)
            response = self.view(row)
        if failure:
            raise failure
        return {"connection": response, **({"draft": result, "requires_staff_review": True} if not test else {})}
