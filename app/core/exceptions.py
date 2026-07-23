"""Application exception hierarchy.

Services raise these domain exceptions; the centralized handlers translate them
into consistent HTTP error responses. Each exception carries the HTTP status,
a stable machine-readable ``error_code``, and a human-readable message.
"""


class AppError(Exception):
    """Base class for all handled application errors."""

    status_code: int = 500
    error_code: str = "internal_error"
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, details: list[str] | None = None):
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
    default_message = "The request conflicts with the current state of the resource."


class ProductNotFoundError(NotFoundError):
    error_code = "product_not_found"

    def __init__(self, product_id: int):
        super().__init__(message=f"Product with id {product_id} was not found.")


class DuplicateSKUError(ConflictError):
    error_code = "duplicate_sku"

    def __init__(self, sku: str):
        super().__init__(message=f"A product with SKU '{sku}' already exists.")


class InsufficientStockError(ConflictError):
    error_code = "insufficient_stock"

    def __init__(self, product_id: int, available: int, requested: int):
        super().__init__(
            message=(
                f"Insufficient stock for product {product_id}: "
                f"requested {requested}, available {available}."
            )
        )


class OptimisticLockError(ConflictError):
    error_code = "version_conflict"

    def __init__(self, product_id: int, expected: int | None = None, actual: int | None = None):
        if expected is not None and actual is not None:
            message = (
                f"Product {product_id} version conflict: expected version "
                f"{expected} but current version is {actual}."
            )
        else:
            message = f"Product {product_id} was modified by a concurrent request."
        super().__init__(message=message)


class ProductHasMovementsError(ConflictError):
    error_code = "product_has_movements"

    def __init__(self, product_id: int):
        super().__init__(
            message=(
                f"Product {product_id} cannot be deleted because it has stock "
                "movement history. Deactivate it instead."
            )
        )
