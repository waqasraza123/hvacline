from insurance_operations.errors import ApiError


def billing_error(status: int, code: str, message: str) -> ApiError:
    return ApiError(status_code=status, code=code.upper(), message=message)
