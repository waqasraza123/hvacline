from insurance_operations.errors import ApiError


def conflict(message: str = "This record changed. Refresh and try again.") -> ApiError:
    return ApiError(status_code=409, code="RECOVERY_CONFLICT", message=message)
