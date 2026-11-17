import logging
from collections import Counter
from datetime import UTC, datetime
from threading import Lock
from time import monotonic
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from insurance_operations.ghl.provider import GhlError, RemotePipeline, RemoteRecord
from insurance_operations.ghl.schemas import GhlId
from insurance_operations.ghl.service import ProviderFactory, open_provider
from insurance_operations.job_execution import JobDeadlineExceeded
from insurance_operations.settings import ApiSettings

SAMPLE_LIMIT = 100
REFRESH_SECONDS = 60
MAX_PIPELINES = 20
MAX_STAGES = 50
logger = logging.getLogger(__name__)


class DemoOpportunity(RemoteRecord):
    locationId: GhlId
    pipelineId: GhlId
    pipelineStageId: GhlId
    status: Literal["open", "won", "lost", "abandoned"]


class StageCount(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    count: int = Field(ge=0, le=SAMPLE_LIMIT)


class PipelineCounts(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    stages: list[StageCount] = Field(max_length=MAX_STAGES)


class DemoCounts(BaseModel):
    loaded: int = Field(ge=0, le=SAMPLE_LIMIT)
    open: int = Field(ge=0, le=SAMPLE_LIMIT)
    won: int = Field(ge=0, le=SAMPLE_LIMIT)
    lost: int = Field(ge=0, le=SAMPLE_LIMIT)
    abandoned: int = Field(ge=0, le=SAMPLE_LIMIT)


class DemoSnapshot(BaseModel):
    sampled_at: datetime
    sample_limit: Literal[100] = 100
    has_more: bool
    counts: DemoCounts
    pipelines: list[PipelineCounts] = Field(max_length=MAX_PIPELINES)


class DemoView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["live", "disabled", "unavailable"]
    snapshot: DemoSnapshot | None = None
    message: str


def public_name(value: str) -> str:
    return " ".join(value.split())[:100]


class GhlDemoService:
    def __init__(
        self,
        settings: ApiSettings,
        factory: ProviderFactory = open_provider,
    ) -> None:
        self.settings = settings
        self.factory = factory
        self.lock = Lock()
        self.cached: DemoView | None = None
        self.retry_at = 0.0

    def read(self) -> DemoView:
        if not self.settings.ghl_demo_enabled:
            return DemoView(
                state="disabled",
                message="The live GoHighLevel demo is not connected yet.",
            )
        if self.cached is not None and monotonic() < self.retry_at:
            return self.cached.model_copy(deep=True)
        if not self.lock.acquire(blocking=False):
            return DemoView(
                state="unavailable",
                snapshot=self.cached.snapshot if self.cached else None,
                message="The GoHighLevel demo is refreshing. Please try again shortly.",
            )
        try:
            if self.cached is not None and monotonic() < self.retry_at:
                return self.cached.model_copy(deep=True)
            try:
                snapshot = self.pull()
                self.cached = DemoView(
                    state="live",
                    snapshot=snapshot,
                    message="Read-only GoHighLevel data from a fictional demo business.",
                )
                self.retry_at = monotonic() + REFRESH_SECONDS
            except (GhlError, JobDeadlineExceeded) as error:
                logger.warning(
                    "GHL demo refresh failed",
                    extra={
                        "error_code": (
                            error.code
                            if isinstance(error, GhlError)
                            else "GHL_DEMO_DEADLINE"
                        )
                    },
                )
                self.cached = DemoView(
                    state="unavailable",
                    snapshot=self.cached.snapshot if self.cached else None,
                    message="GoHighLevel could not be refreshed. Please try again later.",
                )
                delay = error.retry_after if isinstance(error, GhlError) else 0
                self.retry_at = monotonic() + max(REFRESH_SECONDS, delay)
            return self.cached.model_copy(deep=True)
        finally:
            self.lock.release()

    def pull(self) -> DemoSnapshot:
        token = self.settings.ghl_demo_private_integration_token
        location = self.settings.ghl_demo_location_id
        if not self.settings.ghl_demo_fictional_data_only or not token or not location:
            raise GhlError("GHL_DEMO_NOT_CONFIGURED")
        with self.factory(token.get_secret_value(), location) as client:
            raw_pipelines = client.request(
                "GET", "/opportunities/pipelines", params={"locationId": location}
            ).get("pipelines")
            data = client.request(
                "GET",
                "/opportunities/search",
                params={
                    "locationId": location,
                    "limit": SAMPLE_LIMIT,
                    "page": 1,
                    "status": "all",
                    "order": "added_desc",
                    "getTasks": "false",
                    "getNotes": "false",
                    "getCalendarEvents": "false",
                },
            )
        raw_opportunities, meta = data.get("opportunities"), data.get("meta")
        if (
            not isinstance(raw_pipelines, list)
            or len(raw_pipelines) > MAX_PIPELINES
            or not isinstance(raw_opportunities, list)
            or len(raw_opportunities) > SAMPLE_LIMIT
            or not isinstance(meta, dict)
        ):
            raise GhlError("GHL_RESPONSE_INVALID")
        try:
            pipelines = [RemotePipeline.model_validate(row) for row in raw_pipelines]
            opportunities = [
                DemoOpportunity.model_validate(row) for row in raw_opportunities
            ]
            if (
                any(row.locationId != location for row in pipelines)
                or any(row.locationId != location for row in opportunities)
                or len({row.id for row in pipelines}) != len(pipelines)
                or len({row.id for row in opportunities}) != len(opportunities)
                or any(
                    len(row.stages) > MAX_STAGES
                    or len({stage.id for stage in row.stages}) != len(row.stages)
                    for row in pipelines
                )
            ):
                raise GhlError("GHL_DEMO_SCOPE_INVALID")
            stages = {
                (pipeline.id, stage.id)
                for pipeline in pipelines
                for stage in pipeline.stages
            }
            if any(
                (row.pipelineId, row.pipelineStageId) not in stages
                for row in opportunities
            ):
                raise GhlError("GHL_DEMO_SCOPE_INVALID")
            stage_counts = Counter(
                (row.pipelineId, row.pipelineStageId) for row in opportunities
            )
            status_counts = Counter(row.status for row in opportunities)
            return DemoSnapshot(
                sampled_at=datetime.now(UTC),
                has_more=(
                    len(opportunities) == SAMPLE_LIMIT
                    or bool(meta.get("nextPage"))
                    or bool(meta.get("nextPageUrl"))
                ),
                counts=DemoCounts(
                    loaded=len(opportunities),
                    open=status_counts["open"],
                    won=status_counts["won"],
                    lost=status_counts["lost"],
                    abandoned=status_counts["abandoned"],
                ),
                pipelines=[
                    PipelineCounts(
                        name=public_name(pipeline.name),
                        stages=[
                            StageCount(
                                name=public_name(stage.name),
                                count=stage_counts[(pipeline.id, stage.id)],
                            )
                            for stage in pipeline.stages
                        ],
                    )
                    for pipeline in pipelines
                ],
            )
        except ValidationError:
            raise GhlError("GHL_RESPONSE_INVALID") from None


def create_ghl_demo_router(
    settings: ApiSettings,
    service: GhlDemoService | None = None,
) -> APIRouter:
    demo = service or GhlDemoService(settings)
    router = APIRouter(prefix="/api/v1/public")

    @router.get("/ghl-demo", response_model=DemoView)
    def read_demo(response: Response) -> DemoView:
        result = demo.read()
        response.headers["Cache-Control"] = "no-store"
        if result.state == "unavailable":
            response.status_code = 503
            response.headers["Retry-After"] = str(REFRESH_SECONDS)
        return result

    return router
