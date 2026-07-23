"""Product CRUD endpoints.

Endpoints stay thin: they translate HTTP <-> DTOs and delegate all logic to the
service. Responses use the shared :class:`APIResponse` envelope; errors are
produced centrally by the registered exception handlers.
"""

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_product_service
from app.schemas.common import APIResponse, Page
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    response_model=APIResponse[ProductRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
async def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
) -> APIResponse[ProductRead]:
    product = await service.create(payload)
    return APIResponse(message="Product created", data=ProductRead.model_validate(product))


@router.get(
    "/{product_id}",
    response_model=APIResponse[ProductRead],
    summary="Get a product by id",
)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
) -> APIResponse[ProductRead]:
    product = await service.get(product_id)
    return APIResponse(data=ProductRead.model_validate(product))


@router.get(
    "",
    response_model=APIResponse[Page[ProductRead]],
    summary="List products",
)
async def list_products(
    page: int = Query(1, ge=1, description="1-based page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(False, description="Return only active products"),
    service: ProductService = Depends(get_product_service),
) -> APIResponse[Page[ProductRead]]:
    items, total = await service.list(page=page, size=size, active_only=active_only)
    page_data = Page.create(
        items=[ProductRead.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return APIResponse(data=page_data)


@router.patch(
    "/{product_id}",
    response_model=APIResponse[ProductRead],
    summary="Update a product",
)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> APIResponse[ProductRead]:
    product = await service.update(product_id, payload)
    return APIResponse(message="Product updated", data=ProductRead.model_validate(product))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
) -> None:
    await service.delete(product_id)
