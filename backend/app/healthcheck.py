import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from .models import HealthStatus, Service
from .url_utils import build_service_url

logger = logging.getLogger(__name__)


def map_http_status(code: int) -> str:
    if 200 <= code < 400:
        return "online"
    if code in {401, 403}:
        return "auth"
    return "degraded"


def compact_error(exc: Exception) -> str:
    name = exc.__class__.__name__
    lines = str(exc).splitlines()
    text = lines[0][:180] if lines else ""
    return f"{name}: {text}" if text else name


async def probe_service(service: Service) -> HealthStatus:
    if not service.enabled or not service.health_enabled:
        return HealthStatus(service_id=service.id, status="unknown", checked_at=None)
    url = build_service_url(
        protocol=service.protocol,
        host=service.device.host,
        port=service.port,
        path=service.path,
        custom_url=service.custom_url,
    )
    start = time.perf_counter()
    try:
        timeout = httpx.Timeout(service.timeout_ms / 1000)
        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
            response = await client.request(service.health_method, url)
        latency = int((time.perf_counter() - start) * 1000)
        return HealthStatus(
            service_id=service.id,
            status=map_http_status(response.status_code),
            http_status=response.status_code,
            latency_ms=max(latency, 0),
            error_message=None,
            checked_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        latency = int((time.perf_counter() - start) * 1000)
        return HealthStatus(
            service_id=service.id,
            status="offline",
            http_status=None,
            latency_ms=max(latency, 0),
            error_message=compact_error(exc),
            checked_at=datetime.now(timezone.utc),
        )


async def persist_health(session: AsyncSession, status: HealthStatus) -> HealthStatus:
    existing = await session.get(HealthStatus, status.service_id)
    if existing:
        existing.status = status.status
        existing.http_status = status.http_status
        existing.latency_ms = status.latency_ms
        existing.error_message = status.error_message
        existing.checked_at = status.checked_at
        await session.flush()
        return existing
    session.add(status)
    await session.flush()
    return status


async def check_one(session: AsyncSession, service_id: int) -> HealthStatus:
    service = await session.scalar(
        select(Service).where(Service.id == service_id).options(selectinload(Service.device))
    )
    if not service:
        raise ValueError("service not found")
    status = await probe_service(service)
    await persist_health(session, status)
    await session.commit()
    return status


async def check_all(session_factory: async_sessionmaker[AsyncSession], concurrency: int) -> None:
    async with session_factory() as session:
        services = (
            await session.scalars(
                select(Service)
                .where(Service.enabled.is_(True), Service.health_enabled.is_(True))
                .options(selectinload(Service.device))
            )
        ).all()
    semaphore = asyncio.Semaphore(concurrency)

    async def run(service: Service) -> None:
        async with semaphore:
            status = await probe_service(service)
            try:
                async with session_factory() as session:
                    await persist_health(session, status)
                    await session.commit()
            except Exception:
                logger.exception("failed to persist health status for service_id=%s", service.id)

    await asyncio.gather(*(run(service) for service in services), return_exceptions=True)
