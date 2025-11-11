"""cleanup_legacy_test_data

Revision ID: 61ebb6c6c0da
Revises: 7a8f23177a57
Create Date: 2025-11-11 20:07:00.560239

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '61ebb6c6c0da'
down_revision = '7a8f23177a57'
branch_labels = None
depends_on = None


def upgrade():
    """Remove legacy test data from Nov 10, 2025."""
    conn = op.get_bind()

    # Step 1: Fix team reference - update ncaam_kansas to use correct conference ID
    # (ncaam_b12 instead of ncaam_big12)
    conn.execute(sa.text("""
        UPDATE teams
        SET team_group_id = 'ncaam_b12'
        WHERE team_id = 'ncaam_kansas'
        AND team_group_id = 'ncaam_big12'
    """))

    # Step 2: Delete any team rivalries that reference legacy test teams
    # (these are test data from Nov 10 and should be removed)
    conn.execute(sa.text("""
        DELETE FROM team_rivalries
        WHERE team_a_id IN ('ncaam_duke', 'ncaam_unc', 'ncaam_kansas', 'ncaam_kentucky', 'ncaam_villanova')
           OR team_b_id IN ('ncaam_duke', 'ncaam_unc', 'ncaam_kansas', 'ncaam_kentucky', 'ncaam_villanova')
    """))

    # Step 3: Delete any games that reference legacy test teams
    # (these are test data from Nov 10 and should be removed)
    conn.execute(sa.text("""
        DELETE FROM games
        WHERE home_team_id IN ('ncaam_duke', 'ncaam_unc', 'ncaam_kansas', 'ncaam_kentucky', 'ncaam_villanova')
           OR away_team_id IN ('ncaam_duke', 'ncaam_unc', 'ncaam_kansas', 'ncaam_kentucky', 'ncaam_villanova')
    """))

    # Step 4: Delete old test teams with slug-based IDs
    conn.execute(sa.text("""
        DELETE FROM teams
        WHERE team_id IN ('ncaam_duke', 'ncaam_unc', 'ncaam_kansas', 'ncaam_kentucky', 'ncaam_villanova')
    """))

    # Step 5: Delete duplicate conference entry (ncaam_big12)
    # Note: The correct entry is ncaam_b12
    conn.execute(sa.text("""
        DELETE FROM team_groups
        WHERE team_group_id = 'ncaam_big12'
    """))


def downgrade():
    """
    No downgrade needed - legacy test data should not be restored.

    This migration removes incorrect test data that was accidentally seeded.
    Downgrading would re-insert bad data, which is not desired.
    """
    pass
