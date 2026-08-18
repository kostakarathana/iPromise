from httpx import ASGITransport, AsyncClient

from ipromise_demo.app import create_app
from ipromise_demo.config import Settings
from ipromise_demo.store import SyntheticStore


async def test_cloud_run_safe_health_alias() -> None:
    app = create_app(
        settings=Settings(demo_token="test-synthetic-token"),
        store=SyntheticStore(),
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://synthetic.test",
        ) as client:
            response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "ipromise-synthetic-reference"
