"""Remove item table

Revision ID: e85b1a0dd26b
Revises: 9fc66d903edb
Create Date: 2025-11-12 15:39:01.102579

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'e85b1a0dd26b'
down_revision = '9fc66d903edb'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the item table
    op.drop_table('item')


def downgrade():
    # Recreate the item table for rollback capability
    # Note: Foreign key to user table omitted since user table no longer exists
    # (removed in story 1-2: remove-authentication)
    op.create_table(
        'item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_item_id', 'item', ['id'], unique=False)
    op.create_index('ix_item_title', 'item', ['title'], unique=False)
