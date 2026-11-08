from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from insurance_operations.approved_faqs.text import normalize_faq_question

ApprovedFaqStatusValue = Literal["ACTIVE", "INACTIVE"]
QuestionVariation = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]


class ApprovedFaqContent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, hide_input_in_errors=True)

    question: str = Field(min_length=1, max_length=300)
    approved_answer: str = Field(min_length=1, max_length=2_000)
    question_variations: list[QuestionVariation] = Field(
        default_factory=list, max_length=8
    )

    @model_validator(mode="after")
    def distinct_questions(self) -> Self:
        seen: set[str] = set()
        for question in [self.question, *self.question_variations]:
            normalized = normalize_faq_question(question)
            if not normalized:
                raise ValueError("Questions must contain letters or numbers")
            if normalized in seen:
                raise ValueError("Question variations must be distinct")
            seen.add(normalized)
        return self


class ApprovedFaqCreateInput(ApprovedFaqContent):
    status: ApprovedFaqStatusValue = "INACTIVE"


class ApprovedFaqUpdateInput(ApprovedFaqContent):
    expected_row_version: int = Field(ge=1)


class ApprovedFaqStatusInput(BaseModel):
    expected_row_version: int = Field(ge=1)


class ApprovedFaqResponse(ApprovedFaqContent):
    id: UUID
    agency_id: UUID
    status: ApprovedFaqStatusValue
    row_version: int
    created_at: datetime
    updated_at: datetime


class ApprovedFaqLookupInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=500)


class ApprovedFaqSource(BaseModel):
    faq_id: UUID
    question: str
    row_version: int


class ApprovedFaqLookupResponse(BaseModel):
    matched: bool
    answer: str | None
    fallback_message: str
    source: ApprovedFaqSource | None
