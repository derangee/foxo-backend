"""Integration tests for the stock-movement API and history endpoint."""

from tests.helpers import create_product, restock


class TestMovements:
    async def test_restock_returns_201(self, client):
        product = await create_product(client, sku="SKU-1")
        response = await client.post(
            f"/api/v1/products/{product['id']}/restock", json={"quantity": 100}
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["movement_type"] == "RESTOCK"
        assert data["resulting_quantity"] == 100

    async def test_sale_reduces_stock(self, client):
        product = await create_product(client, sku="SKU-1")
        await restock(client, product["id"], 100)
        response = await client.post(
            f"/api/v1/products/{product['id']}/sale", json={"quantity": 30}
        )
        assert response.json()["data"]["resulting_quantity"] == 70

    async def test_oversell_returns_409_and_no_state_change(self, client):
        product = await create_product(client, sku="SKU-1")
        await restock(client, product["id"], 10)
        response = await client.post(
            f"/api/v1/products/{product['id']}/sale", json={"quantity": 50}
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "insufficient_stock"
        current = await client.get(f"/api/v1/products/{product['id']}")
        assert current.json()["data"]["quantity"] == 10

    async def test_adjustment_requires_reason(self, client):
        product = await create_product(client, sku="SKU-1")
        response = await client.post(
            f"/api/v1/products/{product['id']}/adjust", json={"quantity_change": 5}
        )
        assert response.status_code == 422

    async def test_restock_on_missing_product_returns_404(self, client):
        response = await client.post("/api/v1/products/9999/restock", json={"quantity": 5})
        assert response.status_code == 404


class TestHistory:
    async def test_history_orders_and_paginates(self, client):
        product = await create_product(client, sku="SKU-1")
        await restock(client, product["id"], 50)
        await client.post(f"/api/v1/products/{product['id']}/sale", json={"quantity": 10})

        response = await client.get(f"/api/v1/products/{product['id']}/movements")
        data = response.json()["data"]
        assert data["total"] == 2
        assert data["items"][0]["quantity_change"] == -10  # newest first

    async def test_history_type_filter(self, client):
        product = await create_product(client, sku="SKU-1")
        await restock(client, product["id"], 50)
        await client.post(f"/api/v1/products/{product['id']}/sale", json={"quantity": 10})

        response = await client.get(
            f"/api/v1/products/{product['id']}/movements",
            params={"movement_type": "SALE"},
        )
        data = response.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["movement_type"] == "SALE"

    async def test_history_missing_product_returns_404(self, client):
        response = await client.get("/api/v1/products/9999/movements")
        assert response.status_code == 404
