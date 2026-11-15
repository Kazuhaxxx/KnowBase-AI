"""Add collections table and link documents with collection_id.

Revision ID: 20261116_0002
Revises: 20261112_0001
Create Date: 2026-11-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20261116_0002"
down_revision = "20261112_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=False, server_default="folder"),
        sa.Column(
            "access_classification",
            sa.String(length=32),
            nullable=False,
            server_default="employee",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collections_name", "collections", ["name"])
    op.create_index("ix_collections_slug", "collections", ["slug"], unique=True)
    op.create_index(
        "ix_collections_access_classification",
        "collections",
        ["access_classification"],
    )

    op.add_column(
        "documents",
        sa.Column("collection_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_collection_id_collections",
        "documents",
        "collections",
        ["collection_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_documents_collection_id",
        "documents",
        ["collection_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_collection_id", table_name="documents")
    op.drop_constraint(
        "fk_documents_collection_id_collections",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "collection_id")
    op.drop_index("ix_collections_access_classification", table_name="collections")
    op.drop_index("ix_collections_slug", table_name="collections")
    op.drop_index("ix_collections_name", table_name="collections")
    op.drop_table("collections")

