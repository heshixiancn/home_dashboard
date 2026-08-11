from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .cache import cache
from .database import get_session
from .healthcheck import check_one
from .models import Device, HealthStatus, Service
from .schemas import DashboardRead, DeviceCreate, DeviceRead, DeviceUpdate, FavoriteUpdate, HealthRead, ServiceCreate, ServiceRead, ServiceUpdate
from .url_utils import build_service_url

router = APIRouter(prefix="/api")


def health_read(status_obj: HealthStatus | None) -> HealthRead:
    return HealthRead.model_validate(status_obj) if status_obj else HealthRead()


def service_read(service: Service) -> ServiceRead:
    return ServiceRead(
        id=service.id,
        device_id=service.device_id,
        name=service.name,
        protocol=service.protocol,
        port=service.port,
        path=service.path,
        custom_url=service.custom_url,
        icon=service.icon,
        description=service.description,
        favorite=service.favorite,
        enabled=service.enabled,
        health_enabled=service.health_enabled,
        health_method=service.health_method,
        timeout_ms=service.timeout_ms,
        sort_order=service.sort_order,
        created_at=service.created_at,
        updated_at=service.updated_at,
        device_name=service.device.name,
        device_host=service.device.host,
        url=build_service_url(protocol=service.protocol, host=service.device.host, port=service.port, path=service.path, custom_url=service.custom_url),
        health=health_read(service.health),
    )


async def device_counts(session: AsyncSession) -> dict[int, tuple[int, int]]:
    rows = await session.execute(
        select(Device.id, func.count(Service.id), func.sum(case((HealthStatus.status.in_(["online", "auth"]), 1), else_=0)))
        .outerjoin(Service, Service.device_id == Device.id)
        .outerjoin(HealthStatus, HealthStatus.service_id == Service.id)
        .group_by(Device.id)
    )
    return {row[0]: (int(row[1] or 0), int(row[2] or 0)) for row in rows}


def device_read(device: Device, counts: dict[int, tuple[int, int]]) -> DeviceRead:
    total, online = counts.get(device.id, (0, 0))
    data = DeviceRead.model_validate(device).model_dump()
    data.update({"service_count": total, "online_count": online})
    return DeviceRead(**data)


async def list_devices_uncached(session: AsyncSession) -> list[DeviceRead]:
    devices = (await session.scalars(select(Device).order_by(Device.sort_order, Device.name))).all()
    counts = await device_counts(session)
    return [device_read(device, counts) for device in devices]


async def list_services_uncached(session: AsyncSession) -> list[ServiceRead]:
    services = (
        await session.scalars(
            select(Service).options(selectinload(Service.device), selectinload(Service.health)).order_by(Service.favorite.desc(), Service.sort_order, Service.name)
        )
    ).all()
    return [service_read(service) for service in services]


@router.get("/dashboard", response_model=DashboardRead)
async def dashboard(session: AsyncSession = Depends(get_session)) -> DashboardRead:
    cached = cache.get("dashboard")
    if cached:
        return cached
    payload = DashboardRead(devices=await list_devices_uncached(session), services=await list_services_uncached(session))
    cache.set("dashboard", payload)
    return payload


@router.get("/devices", response_model=list[DeviceRead])
async def list_devices(session: AsyncSession = Depends(get_session)) -> list[DeviceRead]:
    cached = cache.get("devices")
    if cached:
        return cached
    payload = await list_devices_uncached(session)
    cache.set("devices", payload)
    return payload


@router.post("/devices", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(payload: DeviceCreate, session: AsyncSession = Depends(get_session)) -> DeviceRead:
    device = Device(**payload.model_dump())
    session.add(device)
    try:
        await session.commit()
        await session.refresh(device)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(400, "device could not be saved") from exc
    cache.invalidate()
    return device_read(device, {})


@router.put("/devices/{device_id}", response_model=DeviceRead)
async def update_device(device_id: int, payload: DeviceUpdate, session: AsyncSession = Depends(get_session)) -> DeviceRead:
    device = await session.get(Device, device_id)
    if not device:
        raise HTTPException(404, "device not found")
    for key, value in payload.model_dump().items():
        setattr(device, key, value)
    await session.commit()
    await session.refresh(device)
    cache.invalidate()
    return device_read(device, await device_counts(session))


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: int, cascade: bool = Query(False), session: AsyncSession = Depends(get_session)) -> Response:
    device = await session.get(Device, device_id)
    if not device:
        raise HTTPException(404, "device not found")
    service_count = await session.scalar(select(func.count(Service.id)).where(Service.device_id == device_id))
    if service_count and not cascade:
        raise HTTPException(409, "device has services; retry with cascade=true after confirmation")
    await session.delete(device)
    await session.commit()
    cache.invalidate()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/services", response_model=list[ServiceRead])
async def list_services(session: AsyncSession = Depends(get_session)) -> list[ServiceRead]:
    cached = cache.get("services")
    if cached:
        return cached
    payload = await list_services_uncached(session)
    cache.set("services", payload)
    return payload


async def ensure_device(session: AsyncSession, device_id: int) -> None:
    if not await session.get(Device, device_id):
        raise HTTPException(400, "device_id does not exist")


@router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceCreate, session: AsyncSession = Depends(get_session)) -> ServiceRead:
    await ensure_device(session, payload.device_id)
    service = Service(**payload.model_dump())
    session.add(service)
    await session.commit()
    service = await session.scalar(select(Service).where(Service.id == service.id).options(selectinload(Service.device), selectinload(Service.health)))
    cache.invalidate()
    return service_read(service)


@router.put("/services/{service_id}", response_model=ServiceRead)
async def update_service(service_id: int, payload: ServiceUpdate, session: AsyncSession = Depends(get_session)) -> ServiceRead:
    service = await session.get(Service, service_id)
    if not service:
        raise HTTPException(404, "service not found")
    await ensure_device(session, payload.device_id)
    for key, value in payload.model_dump().items():
        setattr(service, key, value)
    await session.commit()
    service = await session.scalar(select(Service).where(Service.id == service_id).options(selectinload(Service.device), selectinload(Service.health)))
    cache.invalidate()
    return service_read(service)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(service_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    service = await session.get(Service, service_id)
    if not service:
        raise HTTPException(404, "service not found")
    await session.delete(service)
    await session.commit()
    cache.invalidate()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/services/{service_id}/favorite", response_model=ServiceRead)
async def set_favorite(service_id: int, payload: FavoriteUpdate, session: AsyncSession = Depends(get_session)) -> ServiceRead:
    service = await session.get(Service, service_id)
    if not service:
        raise HTTPException(404, "service not found")
    service.favorite = payload.favorite
    await session.commit()
    service = await session.scalar(select(Service).where(Service.id == service_id).options(selectinload(Service.device), selectinload(Service.health)))
    cache.invalidate()
    return service_read(service)


@router.post("/services/{service_id}/check", response_model=HealthRead)
async def check_service(service_id: int, session: AsyncSession = Depends(get_session)) -> HealthRead:
    try:
        result = await check_one(session, service_id)
    except ValueError as exc:
        raise HTTPException(404, "service not found") from exc
    cache.invalidate()
    return health_read(result)


@router.get("/health")
async def app_health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    try:
        await session.execute(text("select 1"))
    except SQLAlchemyError:
        raise HTTPException(503, {"status": "unhealthy", "database": "down"})
    return {"status": "ok", "database": "ok"}
