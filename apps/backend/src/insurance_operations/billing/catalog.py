import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Literal

type PlanKey = Literal["none", "essential", "comfort", "complete"]
type PaidPlanKey = Literal["essential", "comfort", "complete"]


@dataclass(frozen=True)
class Plan:
    key: PaidPlanKey
    name: str
    amount: int
    included_hours: int
    hourly_amount: int
    description: str

    def __post_init__(self) -> None:
        if (
            self.key not in {"essential", "comfort", "complete"}
            or not self.name.strip()
            or not self.description.strip()
        ):
            raise ValueError(
                "Maintenance packages require valid keys, names and descriptions"
            )
        if any(
            type(value) is not int or value <= 0
            for value in (self.amount, self.included_hours, self.hourly_amount)
        ):
            raise ValueError(
                "Package prices and included hours must be positive integers"
            )

    @property
    def included_minutes(self) -> int:
        return self.included_hours * 60


def load_plans() -> dict[PaidPlanKey, Plan]:
    values = json.loads(files(__package__).joinpath("plans.json").read_text())
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError("The maintenance catalog requires three packages")
    result = {plan.key: plan for plan in (Plan(**value) for value in values)}
    if set(result) != {"essential", "comfort", "complete"}:
        raise ValueError("The maintenance catalog requires unique package keys")
    return result


PLANS = load_plans()

CORE_FEATURES = (
    "Included technician maintenance hours each month",
    "Extra hours available at your package rate",
    "Review service charges before paying through Stripe",
    "Book available times and view your service history",
)
