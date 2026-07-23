"""Small helpers shared across integration tests."""

from httpx import AsyncClient


async def create_product(
    client: AsyncClient,
    *,
    sku: str = "SKU-1",
    name: str = "Widget",
    price: str = "9.99",
    description: str | None = None,
) -> dict:
    payload = {"sku": sku, "name": name, "price": price}
    if description is not None:
        payload["description"] = description
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def restock(client: AsyncClient, product_id: int, quantity: int) -> dict:
    response = await client.post(
        f"/api/v1/products/{product_id}/restock", json={"quantity": quantity}
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]
