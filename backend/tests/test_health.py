"""
Health Endpoint Tests

Tests for the health check endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "AI QA Platform"
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness probe endpoint."""
        response = await client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_check_healthy(self, client: AsyncClient):
        """Readiness succeeds when the database answers SELECT 1."""
        response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"]["status"] == "healthy"
        assert "latency_ms" in data["checks"]["database"]

    @pytest.mark.asyncio
    async def test_readiness_check_unhealthy_db(self, client: AsyncClient):
        """Readiness returns 503 when the database check fails."""
        with patch(
            "app.api.v1.endpoints.health.check_database",
            new_callable=AsyncMock,
            return_value={"status": "unhealthy", "error": "connection refused"},
        ):
            response = await client.get("/api/v1/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_response_headers(self, client: AsyncClient):
        """Test that health endpoint returns proper headers."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        # Check for custom headers added by middleware
        assert "x-request-id" in response.headers
        assert "x-response-time" in response.headers



class TestOpenAPI:
    """Tests for OpenAPI documentation."""

    @pytest.mark.asyncio
    async def test_openapi_schema(self, client: AsyncClient):
        """Test OpenAPI schema is accessible."""
        response = await client.get("/openapi.json")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "AI QA Platform"

    @pytest.mark.asyncio
    async def test_swagger_ui(self, client: AsyncClient):
        """Test Swagger UI is accessible."""
        response = await client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_redoc(self, client: AsyncClient):
        """Test ReDoc is accessible."""
        response = await client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
