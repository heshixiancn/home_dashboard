from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Device(TimestampMixin, Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="设备ID")
    name: Mapped[str] = mapped_column(String(80), nullable=False, comment="设备名称")
    host: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, comment="EasyTier IP或主机名")
    device_type: Mapped[str] = mapped_column(String(40), nullable=False, default="NAS", comment="设备类型")
    icon: Mapped[str] = mapped_column(String(80), nullable=False, default="server", comment="图标标识或图片URL")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="设备说明")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序值，越小越靠前")

    services: Mapped[list["Service"]] = relationship(back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_devices_sort_name", "sort_order", "name"), {"comment": "家庭设备表"})


class Service(TimestampMixin, Base):
    __tablename__ = "service_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="服务ID")
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属设备ID")
    name: Mapped[str] = mapped_column(String(80), nullable=False, comment="服务名称")
    protocol: Mapped[str] = mapped_column(String(8), nullable=False, default="http", comment="访问协议，仅允许http或https")
    port: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="服务端口，完整URL存在时可为空")
    path: Mapped[str] = mapped_column(String(255), nullable=False, default="/", comment="访问路径，自动补齐前导斜杠")
    custom_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="可选完整URL，非空时优先使用")
    icon: Mapped[str] = mapped_column(String(80), nullable=False, default="globe", comment="图标标识或图片URL")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="服务说明")
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否收藏")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用服务入口")
    health_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用健康检查")
    health_method: Mapped[str] = mapped_column(String(8), nullable=False, default="GET", comment="健康检查方法，GET或HEAD")
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=3000, comment="健康检查超时时间，单位毫秒")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序值，越小越靠前")

    device: Mapped[Device] = relationship(back_populates="services")
    health: Mapped["HealthStatus | None"] = relationship(back_populates="service", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        CheckConstraint("protocol in ('http', 'https')", name="ck_service_protocol"),
        CheckConstraint("health_method in ('GET', 'HEAD')", name="ck_service_health_method"),
        CheckConstraint("timeout_ms between 100 and 30000", name="ck_service_timeout"),
        Index("ix_services_sort_name", "favorite", "sort_order", "name"),
        {"comment": "服务入口表"},
    )


class HealthStatus(Base):
    __tablename__ = "health_statuses"

    service_id: Mapped[int] = mapped_column(ForeignKey("service_entries.id", ondelete="CASCADE"), primary_key=True, comment="服务ID")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown", comment="最新检测状态：online/auth/degraded/offline/unknown")
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="HTTP响应状态码")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="响应耗时，单位毫秒")
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="简短错误摘要")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="最近检测时间")

    service: Mapped[Service] = relationship(back_populates="health")

    __table_args__ = (
        CheckConstraint("status in ('online', 'auth', 'degraded', 'offline', 'unknown')", name="ck_health_status"),
        Index("ix_health_status", "status"),
        {"comment": "服务最新健康状态表"},
    )
