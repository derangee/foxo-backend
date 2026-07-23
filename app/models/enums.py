"""Domain enumerations shared across models, schemas, and services."""

from enum import StrEnum


class MovementType(StrEnum):
    """The kind of stock movement recorded against a product.

    - ``RESTOCK``    increases stock (incoming inventory).
    - ``SALE``       decreases stock (outgoing inventory).
    - ``ADJUSTMENT`` corrects stock up or down (requires a reason).
    """

    RESTOCK = "RESTOCK"
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"
