"""Integration tests for the product API (HTTP layer, status codes, envelopes)."""

from tests.helpers import create_product, restock


class TestCreate:
    async def test_create_returns_201_and_envelope(self, client):
        response = await client.post(
            "/api/v1/products",
            json={"sku": "SKU-1", "name": "Widget", "price": "9.99"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["quantity"] == 0
        assert body["data"]["version"] == 1

    async def test_duplicate_sku_returns_409(self, client):
        await create_product(client, sku="SKU-1")
        response = await client.post(
            "/api/v1/products",
            json={"sku": "SKU-1", "name": "Other", "price": "1.00"},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "duplicate_sku"

    async def test_invalid_payload_returns_422(self, client):
        response = await client.post(
            "/api/v1/products",
            json={"sku": "bad sku!", "name": "", "price": "-1"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


class TestRead:
    async def test_get_returns_product(self, client):
        product = await create_product(client, sku="SKU-1")
        response = await client.get(f"/api/v1/products/{product['id']}")
        assert response.status_code == 200
        assert response.json()["data"]["sku"] == "SKU-1"

    async def test_get_missing_returns_404(self, client):
        response = await client.get("/api/v1/products/9999")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "product_not_found"

    async def test_list_is_paginated(self, client):
        await create_product(client, sku="SKU-1")
        await create_product(client, sku="SKU-2")
        response = await client.get("/api/v1/products", params={"page": 1, "size": 1})
        data = response.json()["data"]
        assert data["total"] == 2
        assert data["pages"] == 2
        assert len(data["items"]) == 1


class TestUpdate:
    async def test_partial_update(self, client):
        product = await create_product(client, sku="SKU-1")
        response = await client.patch(f"/api/v1/products/{product['id']}", json={"price": "12.50"})
        assert response.status_code == 200
        assert response.json()["data"]["price"] == "12.50"

    async def test_stale_version_returns_409(self, client):
        product = await create_product(client, sku="SKU-1")
        await client.patch(
            f"/api/v1/products/{product['id']}",
            json={"name": "A", "expected_version": 1},
        )
        response = await client.patch(
            f"/api/v1/products/{product['id']}",
            json={"name": "B", "expected_version": 1},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "version_conflict"


class TestDelete:
    async def test_delete_without_movements_returns_204(self, client):
        product = await create_product(client, sku="SKU-1")
        response = await client.delete(f"/api/v1/products/{product['id']}")
        assert response.status_code == 204

    async def test_delete_with_movements_returns_409(self, client):
        product = await create_product(client, sku="SKU-1")
        await restock(client, product["id"], 5)
        response = await client.delete(f"/api/v1/products/{product['id']}")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "product_has_movements"


class TestActivation:
    async def test_deactivate_and_activate(self, client):
        product = await create_product(client, sku="SKU-1")
        deactivated = await client.post(f"/api/v1/products/{product['id']}/deactivate")
        assert deactivated.json()["data"]["is_active"] is False
        activated = await client.post(f"/api/v1/products/{product['id']}/activate")
        assert activated.json()["data"]["is_active"] is True


class TestLowStock:
    async def test_returns_products_at_or_below_threshold(self, client):
        low = await create_product(client, sku="LOW")
        await restock(client, low["id"], 3)
        high = await create_product(client, sku="HIGH")
        await restock(client, high["id"], 100)

        response = await client.get("/api/v1/products/low-stock", params={"threshold": 10})
        data = response.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == low["id"]
