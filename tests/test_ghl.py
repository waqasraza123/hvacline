import json
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from insurance_operations.database.models.ghl import GhlConnection, GhlDelivery
from insurance_operations.ghl.jobs import retry_seconds
from insurance_operations.ghl.provider import (
    API_VERSION,
    GhlClient,
    GhlError,
    retry_delay,
)
from insurance_operations.ghl.schemas import (
    ConnectionInput,
    CredentialInput,
    RetryInput,
)
from insurance_operations.ghl.service import GhlVault, require_managed_opportunity
from insurance_operations.settings import DatabaseSettings


def settings(**overrides: object) -> DatabaseSettings:
    values: dict[str, object] = {
        "app_environment": "development",
        "database_url": "postgresql://synthetic:synthetic@localhost/synthetic",
        "ghl_enabled": True,
        "ghl_token_encryption_key": Fernet.generate_key().decode(),
    }
    return DatabaseSettings.model_validate({**values, **overrides})


def configuration() -> ConnectionInput:
    return ConnectionInput.model_validate(
        {
            "location_id": "location-one",
            "token": "synthetic-private-token",
            "pipeline_id": "pipeline-one",
            "stages": {
                "new": "new",
                "booked": "booked",
                "cancelled": "cancelled",
                "attention": "attention",
            },
            "fields": {
                "reference": "reference",
                "summary": "summary",
                "booking": "booking",
            },
            "multiple_opportunities_confirmed": True,
        }
    )


def test_ghl_settings_require_valid_encryption_and_preserve_production_gate() -> None:
    with pytest.raises(ValidationError, match="Fernet"):
        settings(ghl_token_encryption_key="invalid")
    with pytest.raises(ValidationError, match="identity gates"):
        settings(app_environment="production")
    assert not settings(ghl_enabled=False, ghl_token_encryption_key=None).ghl_enabled


def test_credentials_are_bound_to_business_and_connection() -> None:
    vault = GhlVault(settings())
    agency, identifier = uuid4(), uuid4()
    row = GhlConnection(id=identifier, agency_id=agency)
    row.token_ciphertext = vault.encrypt("synthetic-private-token", agency, identifier)
    assert "synthetic-private-token" not in row.token_ciphertext
    assert vault.decrypt(row) == "synthetic-private-token"
    row.agency_id = uuid4()
    with pytest.raises(GhlError, match="CREDENTIALS_UNAVAILABLE"):
        vault.decrypt(row)
    row.agency_id, row.id = agency, uuid4()
    with pytest.raises(GhlError, match="CREDENTIALS_UNAVAILABLE"):
        vault.decrypt(row)


def test_input_rejects_invalid_ids_duplicate_mappings_and_ambiguous_recovery() -> None:
    with pytest.raises(ValidationError):
        CredentialInput(
            location_id="../../foreign", token=SecretStr("synthetic-private-token")
        )
    values = configuration().model_dump()
    values["stages"] = {
        "new": "same",
        "booked": "same",
        "cancelled": "same",
        "attention": "same",
    }
    with pytest.raises(ValidationError, match="different pipeline stages"):
        ConnectionInput.model_validate(values)
    with pytest.raises(ValidationError):
        RetryInput(remote_opportunity_id="deal", confirm_remote_absent=True)
    with pytest.raises(ValidationError):
        ConnectionInput.model_validate(
            {**configuration().model_dump(), "multiple_opportunities_confirmed": False}
        )


def test_contact_matches_email_and_phone_separately_without_overwriting_fields() -> (
    None
):
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["Version"] == API_VERSION
        assert request.headers["Authorization"] == "Bearer synthetic-private-token"
        assert request.method == "GET"
        assert not ("email" in request.url.params and "phone" in request.url.params)
        return httpx.Response(
            200,
            json={
                "contacts": [
                    {"id": "existing", "locationId": "location-one", "dnd": True}
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client = GhlClient(transport, "synthetic-private-token", "location-one")
        assert (
            client.match_contact("synthetic@example.invalid", "+12025550123")
            == "existing"
        )
    assert len(requests) == 2


@pytest.mark.parametrize("mode", ["conflict", "duplicates", "foreign"])
def test_contact_conflicts_duplicates_and_foreign_locations_fail_closed(
    mode: str,
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        identifier = (
            "email-contact" if "email" in request.url.params else "phone-contact"
        )
        rows = [
            {
                "id": identifier,
                "locationId": "other" if mode == "foreign" else "location-one",
            }
        ]
        if mode == "duplicates":
            rows.append({"id": "duplicate", "locationId": "location-one"})
        return httpx.Response(200, json={"contacts": rows})

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        with pytest.raises(GhlError):
            GhlClient(
                transport, "synthetic-private-token", "location-one"
            ).match_contact("synthetic@example.invalid", "+12025550123")


def test_lost_create_response_is_ambiguous_and_does_not_expose_provider_body() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["locationId"] == "location-one"
        return httpx.Response(503, text="sensitive-provider-body")

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        with pytest.raises(GhlError) as result:
            GhlClient(
                transport, "synthetic-private-token", "location-one"
            ).create_contact({"email": "synthetic@example.invalid"})
    assert result.value.ambiguous and result.value.retryable
    assert "sensitive-provider-body" not in str(result.value)


def test_rate_limit_honors_retry_after_without_marking_create_unknown() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(429, headers={"Retry-After": "120"})
        )
    ) as transport:
        with pytest.raises(GhlError) as result:
            GhlClient(
                transport, "synthetic-private-token", "location-one"
            ).create_contact({"email": "synthetic@example.invalid"})
    assert result.value.retry_after == 120
    assert not result.value.ambiguous
    assert retry_seconds(1, 120) == 120
    assert retry_seconds(8) == 3600
    assert retry_delay("not-a-date") == 60
    assert retry_delay("inf") == 86400


def test_pipeline_and_field_discovery_rejects_nontext_mapping() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/opportunities/pipelines":
            return httpx.Response(
                200,
                json={
                    "pipelines": [
                        {
                            "id": "pipeline-one",
                            "name": "Synthetic pipeline",
                            "locationId": "location-one",
                            "stages": [
                                {"id": key, "name": key}
                                for key in ("new", "booked", "cancelled", "attention")
                            ],
                        }
                    ]
                },
            )
        if request.url.path.endswith("customFields"):
            return httpx.Response(
                200,
                json={
                    "customFields": [
                        {
                            "id": key,
                            "name": key,
                            "model": "opportunity",
                            "locationId": "location-one",
                            "dataType": "NUMERICAL"
                            if key == "reference"
                            else "LARGE_TEXT",
                        }
                        for key in ("reference", "summary", "booking")
                    ]
                },
            )
        return httpx.Response(200, json={"contacts": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        with pytest.raises(GhlError, match="FIELD_MAPPING_INVALID"):
            GhlClient(
                transport, "synthetic-private-token", "location-one"
            ).validate_mapping(configuration())


@pytest.mark.parametrize("change", ["closed", "stage", "contact", "reference"])
def test_external_sales_edits_and_foreign_opportunities_are_protected(
    change: str,
) -> None:
    config = configuration()
    lead_id = uuid4()
    connection = GhlConnection(
        location_id=config.location_id,
        pipeline_id=config.pipeline_id,
        stages=config.stages.model_dump(),
        fields=config.fields.model_dump(),
    )
    delivery = GhlDelivery(lead_id=lead_id, contact_id="contact", last_stage_id="new")
    record = {
        "id": "opportunity",
        "locationId": "location-one",
        "pipelineId": "pipeline-one",
        "pipelineStageId": "booked" if change == "stage" else "new",
        "contactId": "foreign" if change == "contact" else "contact",
        "status": "won" if change == "closed" else "open",
        "customFields": [
            {
                "id": "reference",
                "fieldValue": "foreign"
                if change == "reference"
                else f"hvacline:{lead_id}",
            }
        ],
    }
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"opportunity": record})
        )
    ) as transport:
        with pytest.raises(GhlError):
            require_managed_opportunity(
                GhlClient(transport, "synthetic-private-token", "location-one"),
                connection,
                delivery,
                "opportunity",
            )


def test_opportunity_recovery_paginates_and_matches_exact_reference() -> None:
    pages: list[int] = []

    def respond(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages.append(page)
        record = {
            "id": f"deal-{page}",
            "locationId": "location-one",
            "pipelineId": "pipeline-one",
            "pipelineStageId": "new",
            "contactId": "contact",
            "status": "open",
            "customFields": [
                {
                    "id": "reference",
                    "fieldValue": "expected" if page == 2 else "unrelated",
                }
            ],
        }
        return httpx.Response(
            200,
            json={
                "opportunities": [record],
                "meta": {"nextPage": 2 if page == 1 else ""},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        found = GhlClient(
            transport, "synthetic-private-token", "location-one"
        ).find_opportunity("expected", "pipeline-one", "reference")
    assert found is not None and found.id == "deal-2"
    assert pages == [1, 2]
