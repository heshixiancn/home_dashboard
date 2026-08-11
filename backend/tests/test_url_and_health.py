import asyncio
from types import SimpleNamespace

import httpx
import pytest
import respx

from app.healthcheck import map_http_status, probe_service
from app.url_utils import build_service_url


def test_build_service_url_from_device_host():
    assert build_service_url(protocol="http", host="10.126.126.10", port=8080, path="admin") == "http://10.126.126.10:8080/admin"


def test_custom_url_takes_priority():
    assert build_service_url(protocol="http", host="host", port=1, path="/", custom_url="https://example.com/ui") == "https://example.com/ui"


@pytest.mark.parametrize("code,status", [(200, "online"), (302, "online"), (401, "auth"), (403, "auth"), (500, "degraded")])
def test_status_mapping(code, status):
    assert map_http_status(code) == status


def service(url_host="example.test", method="GET", timeout=3000):
    return SimpleNamespace(
        id=1,
        enabled=True,
        health_enabled=True,
        protocol="http",
        port=None,
        path="/",
        custom_url=f"http://{url_host}/",
        health_method=method,
        timeout_ms=timeout,
        device=SimpleNamespace(host=url_host),
    )


@pytest.mark.asyncio
@respx.mock
async def test_probe_records_latency_and_http_status():
    respx.get("http://example.test/").mock(return_value=httpx.Response(204))
    result = await probe_service(service())
    assert result.status == "online"
    assert result.http_status == 204
    assert result.latency_ms is not None
    assert result.checked_at is not None


@pytest.mark.asyncio
@respx.mock
async def test_probe_timeout_is_offline():
    async def timeout(_request):
        raise httpx.ConnectTimeout("timed out")

    respx.get("http://example.test/").mock(side_effect=timeout)
    result = await probe_service(service(timeout=500))
    assert result.status == "offline"
    assert "ConnectTimeout" in result.error_message


@pytest.mark.asyncio
@respx.mock
async def test_probe_failures_do_not_block_other_checks():
    respx.get("http://bad.test/").mock(side_effect=httpx.ConnectError("refused"))
    respx.get("http://good.test/").mock(return_value=httpx.Response(200))
    first, second = await asyncio.gather(probe_service(service("bad.test")), probe_service(service("good.test")))
    assert first.status == "offline"
    assert second.status == "online"

