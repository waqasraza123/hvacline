import re

import phonenumbers

from insurance_operations.errors import ApiError

E164 = re.compile(r"\+[1-9][0-9]{7,14}\Z")
US_REGIONS = frozenset({"US", "AS", "GU", "MP", "PR", "VI"})


def normalize_phone_number(value: str) -> str:
    value = value.strip()
    if E164.fullmatch(value):
        return value
    if re.fullmatch(r"\+?[0-9 ().-]+", value) is None:
        raise ValueError(
            "Use a phone number without extensions or dialing instructions"
        )
    try:
        number = phonenumbers.parse(value, "US")
    except phonenumbers.NumberParseException:
        raise ValueError(
            "Use a complete phone number including its area code"
        ) from None
    normalized = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    if number.extension or E164.fullmatch(normalized) is None:
        raise ValueError("Use a complete phone number without an extension")
    return normalized


def validate_us_destination(value: str) -> None:
    try:
        number = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        raise invalid_us_number() from None
    if not phonenumbers.is_valid_number(number):
        raise invalid_us_number()
    supported_type = phonenumbers.number_type(number) in {
        phonenumbers.PhoneNumberType.FIXED_LINE,
        phonenumbers.PhoneNumberType.MOBILE,
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
        phonenumbers.PhoneNumberType.VOIP,
    }
    if (
        number.country_code != 1
        or phonenumbers.region_code_for_number(number) not in US_REGIONS
        or not supported_type
    ):
        raise ApiError(
            status_code=422,
            code="DEMO_DESTINATION_UNSUPPORTED",
            message="Only US mobile, landline and VoIP destinations are supported.",
            details={"field": "phone_number"},
        )


def invalid_us_number() -> ApiError:
    return ApiError(
        status_code=422,
        code="DEMO_PHONE_NUMBER_INVALID",
        message="Use a valid US phone number in an assigned numbering range.",
        details={"field": "phone_number"},
    )
