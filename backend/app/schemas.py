from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .url_utils import normalize_path, validate_host, validate_http_url, validate_port, validate_protocol


class HealthRead(BaseModel):
    status: str = "unknown"
    http_status: int | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    checked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    host: str = Field(min_length=1, max_length=255)
    device_type: str = Field(default="NAS", max_length=40)
    icon: str = Field(default="server", max_length=80)
    description: str = ""
    sort_order: int = 0

    @field_validator("host")
    @classmethod
    def host_valid(cls, value: str) -> str:
        return validate_host(value)


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(DeviceBase):
    pass


class DeviceRead(DeviceBase):
    id: int
    service_count: int = 0
    online_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceBase(BaseModel):
    device_id: int
    name: str = Field(min_length=1, max_length=80)
    protocol: str = "http"
    port: int | None = None
    path: str = "/"
    custom_url: str | None = None
    icon: str = Field(default="globe", max_length=80)
    description: str = ""
    favorite: bool = False
    enabled: bool = True
    health_enabled: bool = True
    health_method: str = "GET"
    timeout_ms: int = Field(default=3000, ge=100, le=30000)
    sort_order: int = 0

    @field_validator("protocol")
    @classmethod
    def protocol_valid(cls, value: str) -> str:
        return validate_protocol(value)

    @field_validator("health_method")
    @classmethod
    def method_valid(cls, value: str) -> str:
        upper = value.upper().strip()
        if upper not in {"GET", "HEAD"}:
            raise ValueError("health_method must be GET or HEAD")
        return upper

    @field_validator("port")
    @classmethod
    def port_valid(cls, value: int | None) -> int | None:
        return validate_port(value)

    @field_validator("path")
    @classmethod
    def path_valid(cls, value: str) -> str:
        return normalize_path(value)

    @field_validator("custom_url")
    @classmethod
    def custom_url_valid(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_http_url(value)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(ServiceBase):
    pass


class ServiceRead(ServiceBase):
    id: int
    url: str
    device_name: str
    device_host: str
    health: HealthRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavoriteUpdate(BaseModel):
    favorite: bool


class DashboardRead(BaseModel):
    devices: list[DeviceRead]
    services: list[ServiceRead]
