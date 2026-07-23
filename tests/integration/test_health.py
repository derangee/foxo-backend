"""Integration test for the health endpoint."""


class TestHealth:
    async def test_reports_healthy_with_database_up(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ok"
        assert body["data"]["database"] == "up"
