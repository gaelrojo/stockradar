"""Esquema inicial: usuarios, tiendas, conexiones POS, catálogo, ventas, alertas y sync_runs.

Revision ID: 0001
Revises:
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("admin", "manager", "viewer", name="user_role", create_type=False)
coverage_status = postgresql.ENUM(
    "ok", "warning", "critical", name="coverage_status", create_type=False
)
sync_status = postgresql.ENUM(
    "running", "success", "failed", name="sync_status", create_type=False
)
ENUMS = (user_role, coverage_status, sync_status)


def _created_at() -> sa.Column[sa.DateTime]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stores"),
    )
    op.create_table(
        "pos_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("connector_type", sa.String(50), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("encrypted_credentials", sa.LargeBinary(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_pos_connections_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pos_connections"),
    )
    op.create_index("ix_pos_connections_store_id", "pos_connections", ["store_id"])

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("coverage_days_critical", sa.Numeric(6, 2), nullable=False),
        sa.Column("coverage_days_warning", sa.Numeric(6, 2), nullable=False),
        sa.Column("channels_json", sa.JSON(), nullable=False),
        sa.CheckConstraint("coverage_days_critical > 0", name="ck_alert_rules_critical_positive"),
        sa.CheckConstraint(
            "coverage_days_warning >= coverage_days_critical", name="ck_alert_rules_warning_gte"
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name="fk_alert_rules_store_id_stores", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_alert_rules"),
        sa.UniqueConstraint("store_id", name="uq_alert_rules_store_id"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("category", sa.String(150), nullable=True),
        sa.Column("supplier", sa.String(200), nullable=True),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["pos_connections.id"],
            name="fk_products_connection_id_pos_connections",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint(
            "connection_id", "external_id", name="uq_products_connection_id_external_id"
        ),
    )
    op.create_index("ix_products_connection_id", "products", ["connection_id"])
    op.create_index("ix_products_sku", "products", ["sku"])

    op.create_table(
        "stock_levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("min_threshold", sa.Numeric(14, 3), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_stock_levels_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_levels"),
    )
    op.create_index("ix_stock_levels_product_id", "stock_levels", ["product_id"])
    op.create_index("ix_stock_levels_captured_at", "stock_levels", ["captured_at"])

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["pos_connections.id"],
            name="fk_sales_connection_id_pos_connections",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
        sa.UniqueConstraint(
            "connection_id", "external_id", name="uq_sales_connection_id_external_id"
        ),
    )
    op.create_index("ix_sales_connection_id", "sales", ["connection_id"])
    op.create_index("ix_sales_sold_at", "sales", ["sold_at"])

    op.create_table(
        "sale_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_sale_lines_product_id_products",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], name="fk_sale_lines_sale_id_sales", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_lines"),
    )
    op.create_index("ix_sale_lines_sale_id", "sale_lines", ["sale_id"])
    op.create_index("ix_sale_lines_product_id", "sale_lines", ["product_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("level", coverage_status, nullable=False),
        sa.Column("coverage_days", sa.Numeric(10, 2), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        _created_at(),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name="fk_alerts_product_id_products", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_alerts"),
    )
    op.create_index("ix_alerts_product_id", "alerts", ["product_id"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sync_status, nullable=False),
        sa.Column("records", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["pos_connections.id"],
            name="fk_sync_runs_connection_id_pos_connections",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sync_runs"),
    )
    op.create_index("ix_sync_runs_connection_id", "sync_runs", ["connection_id"])


def downgrade() -> None:
    for table in (
        "sync_runs",
        "alerts",
        "sale_lines",
        "sales",
        "stock_levels",
        "products",
        "alert_rules",
        "pos_connections",
        "stores",
        "users",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum in ENUMS:
        enum.drop(bind, checkfirst=True)
