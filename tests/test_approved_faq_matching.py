from uuid import uuid4

import pytest
from pydantic import ValidationError

from insurance_operations.approved_faqs.schemas import ApprovedFaqCreateInput
from insurance_operations.approved_faqs.service import (
    faq_match_score,
    normalize_faq_question,
    select_faq_match,
)
from insurance_operations.database.models.approved_faq import AgencyApprovedFaq


def faq(question: str, *variations: str) -> AgencyApprovedFaq:
    return AgencyApprovedFaq(
        id=uuid4(), question=question, question_variations=list(variations)
    )


def test_normalization_and_matching_are_deterministic() -> None:
    office_hours = faq("What are your office hours?")

    assert normalize_faq_question("  OFFICE—Hours?! ") == "office hours"
    assert (
        faq_match_score(
            "Please tell me your office hours",
            office_hours.question,
        )
        >= 0.8
    )
    assert (
        select_faq_match(
            "Please tell me your office hours",
            [office_hours],
        )
        is office_hours
    )


def test_matching_rejects_weak_and_ambiguous_questions() -> None:
    auto = faq("What auto insurance options do you support?")
    home = faq("What home insurance options do you support?")

    assert select_faq_match("Can you recommend coverage?", [auto, home]) is None
    assert (
        select_faq_match(
            "What insurance options do you support?",
            [auto, home],
        )
        is None
    )


def test_approved_variations_match_without_broadening_unapproved_topics() -> None:
    cooling = faq(
        "Can I request air conditioning repair?",
        "Can you help with AC repair?",
        "Do you repair air conditioners?",
    )
    assert select_faq_match("Can you help with AC repair?", [cooling]) is cooling
    assert select_faq_match("Do you repair air conditioners?", [cooling]) is cooling
    assert select_faq_match("What is your financing interest rate?", [cooling]) is None


def test_conflicting_variations_require_staff_instead_of_picking_an_answer() -> None:
    first = faq("What are your office hours?", "When can I contact your team?")
    second = faq("How can I reach staff?", "When can I contact your team?")
    assert select_faq_match("When can I contact your team?", [first, second]) is None


@pytest.mark.parametrize(
    "variations",
    [
        ["Another question"] * 9,
        ["   "],
        ["???"],
        ["What are your office hours!"],
        ["When are you open?", "WHEN ARE YOU OPEN!"],
        ["x" * 301],
    ],
)
def test_variations_require_bounded_distinct_meaningful_questions(
    variations: list[str],
) -> None:
    with pytest.raises(ValidationError):
        ApprovedFaqCreateInput(
            question="What are your office hours?",
            approved_answer="Synthetic approved hours.",
            question_variations=variations,
        )


def test_variations_are_trimmed_and_new_answers_stay_inactive() -> None:
    content = ApprovedFaqCreateInput(
        question="What are your office hours?",
        approved_answer="Synthetic approved hours.",
        question_variations=["  When are you open?  "],
    )
    assert content.question_variations == ["When are you open?"]
    assert content.status == "INACTIVE"
