"""Add game_period to fact_game

Revision ID: 0c51279163bd
Revises: f3c4d5e6f7g8
Create Date: 2025-11-17 22:11:53.844321

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0c51279163bd'
down_revision = 'f3c4d5e6f7g8'
branch_labels = None
depends_on = None


def upgrade():
    # Add game_period column to fact_game for storing period info (1st Half, 2nd Half, etc.)
    op.add_column('fact_game', sa.Column('game_period', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('fact_game', 'game_period')
