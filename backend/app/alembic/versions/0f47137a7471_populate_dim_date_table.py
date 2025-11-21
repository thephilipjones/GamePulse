"""Populate dim_date table

Revision ID: 0f47137a7471
Revises: c2073349c669
Create Date: 2025-11-20 20:46:54.992615

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from datetime import date, timedelta


# revision identifiers, used by Alembic.
revision = '0f47137a7471'
down_revision = 'c2073349c669'
branch_labels = None
depends_on = None


def upgrade():
    """Populate dim_date with dates from 2024-2026 for game date foreign keys."""
    # Generate dates from 2024-01-01 to 2026-12-31 (3 years coverage)
    start_date = date(2024, 1, 1)
    end_date = date(2026, 12, 31)

    dates_to_insert = []
    current_date = start_date

    while current_date <= end_date:
        date_key = int(current_date.strftime('%Y%m%d'))

        dates_to_insert.append({
            'date_key': date_key,
            'full_date': current_date,
            'year': current_date.year,
            'quarter': (current_date.month - 1) // 3 + 1,
            'month': current_date.month,
            'month_name': current_date.strftime('%B'),
            'day_of_month': current_date.day,
            'day_of_week': current_date.weekday() + 1,  # Monday=1
            'day_name': current_date.strftime('%A'),
            'is_weekend': current_date.weekday() >= 5,
            'is_march_madness': False,  # Can be updated later for specific dates
        })
        current_date += timedelta(days=1)

    # Bulk insert using raw SQL for performance (1096 dates)
    op.bulk_insert(
        sa.table('dim_date',
            sa.column('date_key', sa.Integer),
            sa.column('full_date', sa.Date),
            sa.column('year', sa.Integer),
            sa.column('quarter', sa.Integer),
            sa.column('month', sa.Integer),
            sa.column('month_name', sa.String),
            sa.column('day_of_month', sa.Integer),
            sa.column('day_of_week', sa.Integer),
            sa.column('day_name', sa.String),
            sa.column('is_weekend', sa.Boolean),
            sa.column('is_march_madness', sa.Boolean),
        ),
        dates_to_insert
    )

    print(f"✓ Populated dim_date with {len(dates_to_insert)} dates (2024-2026)")


def downgrade():
    """Remove all dates from dim_date."""
    op.execute("DELETE FROM dim_date WHERE date_key >= 20240101 AND date_key <= 20261231")
