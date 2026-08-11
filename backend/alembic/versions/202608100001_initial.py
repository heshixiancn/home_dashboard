"""initial schema

Revision ID: 202608100001
Revises:
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202608100001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="设备ID"),
        sa.Column("name", sa.String(length=80), nullable=False, comment="设备名称"),
        sa.Column("host", sa.String(length=255), nullable=False, comment="EasyTier IP或主机名"),
        sa.Column("device_type", sa.String(length=40), nullable=False, comment="设备类型"),
        sa.Column("icon", sa.String(length=80), nullable=False, comment="图标标识或图片URL"),
        sa.Column("description", sa.Text(), nullable=False, comment="设备说明"),
        sa.Column("sort_order", sa.Integer(), nullable=False, comment="排序值，越小越靠前"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="家庭设备表",
    )
    op.create_index("ix_devices_sort_name", "devices", ["sort_order", "name"])
    op.create_table(
        "service_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="服务ID"),
        sa.Column("device_id", sa.Integer(), nullable=False, comment="所属设备ID"),
        sa.Column("name", sa.String(length=80), nullable=False, comment="服务名称"),
        sa.Column("protocol", sa.String(length=8), nullable=False, comment="访问协议，仅允许http或https"),
        sa.Column("port", sa.Integer(), nullable=True, comment="服务端口，完整URL存在时可为空"),
        sa.Column("path", sa.String(length=255), nullable=False, comment="访问路径，自动补齐前导斜杠"),
        sa.Column("custom_url", sa.String(length=1024), nullable=True, comment="可选完整URL，非空时优先使用"),
        sa.Column("icon", sa.String(length=80), nullable=False, comment="图标标识或图片URL"),
        sa.Column("description", sa.Text(), nullable=False, comment="服务说明"),
        sa.Column("favorite", sa.Boolean(), nullable=False, comment="是否收藏"),
        sa.Column("enabled", sa.Boolean(), nullable=False, comment="是否启用服务入口"),
        sa.Column("health_enabled", sa.Boolean(), nullable=False, comment="是否启用健康检查"),
        sa.Column("health_method", sa.String(length=8), nullable=False, comment="健康检查方法，GET或HEAD"),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, comment="健康检查超时时间，单位毫秒"),
        sa.Column("sort_order", sa.Integer(), nullable=False, comment="排序值，越小越靠前"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.CheckConstraint("health_method in ('GET', 'HEAD')", name="ck_service_health_method"),
        sa.CheckConstraint("protocol in ('http', 'https')", name="ck_service_protocol"),
        sa.CheckConstraint("timeout_ms between 100 and 30000", name="ck_service_timeout"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="服务入口表",
    )
    op.create_index("ix_service_entries_device_id", "service_entries", ["device_id"])
    op.create_index("ix_services_sort_name", "service_entries", ["favorite", "sort_order", "name"])
    op.create_table(
        "health_statuses",
        sa.Column("service_id", sa.Integer(), nullable=False, comment="服务ID"),
        sa.Column("status", sa.String(length=16), nullable=False, comment="最新检测状态：online/auth/degraded/offline/unknown"),
        sa.Column("http_status", sa.Integer(), nullable=True, comment="HTTP响应状态码"),
        sa.Column("latency_ms", sa.Integer(), nullable=True, comment="响应耗时，单位毫秒"),
        sa.Column("error_message", sa.String(length=255), nullable=True, comment="简短错误摘要"),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True, comment="最近检测时间"),
        sa.CheckConstraint("status in ('online', 'auth', 'degraded', 'offline', 'unknown')", name="ck_health_status"),
        sa.ForeignKeyConstraint(["service_id"], ["service_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("service_id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="服务最新健康状态表",
    )
    op.create_index("ix_health_status", "health_statuses", ["status"])


def downgrade() -> None:
    op.drop_index("ix_health_status", table_name="health_statuses")
    op.drop_table("health_statuses")
    op.drop_index("ix_services_sort_name", table_name="service_entries")
    op.drop_index("ix_service_entries_device_id", table_name="service_entries")
    op.drop_table("service_entries")
    op.drop_index("ix_devices_sort_name", table_name="devices")
    op.drop_table("devices")
