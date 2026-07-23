"""Stock-movement endpoints.

Three explicit operations (restock, sale, adjust) nested under a product. Each
is thin: validate the payload, delegate to the service, return the created
movement (including the resulting stock level). Movements are immutable, so no
update or delete routes exist.
"""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_stock_movement_service
from app.schemas.common import APIResponse
from app.schemas.stock_movement import (
    AdjustmentRequest,
    MovementRead,
    QuantityMovementRequest,
)
from app.services.stock_movement import StockMovementService

router = APIRouter(prefix="/products/{product_id}", tags=["Stock Movements"])


@router.post(
    "/restock",
    response_model=APIResponse[MovementRead],
    status_code=status.HTTP_201_CREATED,
    summary="Restock a product (increase stock)",
)
async def restock(
    product_id: int,
    payload: QuantityMovementRequest,
    service: StockMovementService = Depends(get_stock_movement_service),
) -> APIResponse[MovementRead]:
    movement = await service.restock(product_id, payload.quantity, payload.reason)
    return APIResponse(message="Stock restocked", data=MovementRead.model_validate(movement))


@router.post(
    "/sale",
    response_model=APIResponse[MovementRead],
    status_code=status.HTTP_201_CREATED,
    summary="Record a sale (decrease stock)",
)
async def sale(
    product_id: int,
    payload: QuantityMovementRequest,
    service: StockMovementService = Depends(get_stock_movement_service),
) -> APIResponse[MovementRead]:
    movement = await service.sell(product_id, payload.quantity, payload.reason)
    return APIResponse(message="Sale recorded", data=MovementRead.model_validate(movement))


@router.post(
    "/adjust",
    response_model=APIResponse[MovementRead],
    status_code=status.HTTP_201_CREATED,
    summary="Adjust stock (signed correction, reason required)",
)
async def adjust(
    product_id: int,
    payload: AdjustmentRequest,
    service: StockMovementService = Depends(get_stock_movement_service),
) -> APIResponse[MovementRead]:
    movement = await service.adjust(product_id, payload.quantity_change, payload.reason)
    return APIResponse(message="Stock adjusted", data=MovementRead.model_validate(movement))
