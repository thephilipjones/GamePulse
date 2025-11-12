"""seed_dimensional_data

Revision ID: 7a8f23177a57
Revises: 29a82f0b5d5b
Create Date: 2025-11-11 14:52:52.722885

"""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '7a8f23177a57'
down_revision = '29a82f0b5d5b'  # Original order preserved
branch_labels = None
depends_on = None


def upgrade():
    """Seed dimensional data for NCAA Men's Basketball teams.

    This migration is schema-aware and works with both:
    - Old schema: teams + team_groups tables (before dimensional refactor)
    - New schema: dim_team table (after dimensional refactor)
    """
    # Get path to data directory
    data_dir = Path(__file__).parent.parent.parent / "data"

    # Read JSON files
    with open(data_dir / "conferences.json") as f:
        data = json.load(f)
        conferences = data["conferences"]

    with open(data_dir / "teams.json") as f:
        data = json.load(f)
        teams = data["teams"]

    # Get connection
    conn = op.get_bind()

    # Check which schema exists (old: teams/team_groups, new: dim_team)
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()
    using_new_schema = "dim_team" in table_names

    if using_new_schema:
        # NEW SCHEMA: Insert into dim_team with flattened team_group fields
        conference_lookup = {
            conf["team_group_id"]: conf["team_group_name"] for conf in conferences
        }

        for team in teams:
            team_group_id = team["team_group_id"]
            team_group_name = conference_lookup.get(team_group_id)

            # Extract ESPN team ID from team_id (e.g., "ncaam_150" → "150")
            espn_team_id = team["team_id"].split("_")[1] if "_" in team["team_id"] else None

            conn.execute(
                sa.text("""
                    INSERT INTO dim_team (
                        team_id, sport, team_name, team_abbr, espn_team_id, team_group_id, team_group_name,
                        primary_color, secondary_color, aliases,
                        is_current, valid_from, valid_to, created_at, updated_at
                    )
                    VALUES (
                        :team_id, :sport, :team_name, :team_abbr, :espn_team_id, :team_group_id, :team_group_name,
                        :primary_color, :secondary_color, :aliases,
                        TRUE, NOW(), NULL, NOW(), NOW()
                    )
                    ON CONFLICT (team_id)
                    DO UPDATE SET
                        sport = EXCLUDED.sport,
                        team_name = EXCLUDED.team_name,
                        team_abbr = EXCLUDED.team_abbr,
                        espn_team_id = EXCLUDED.espn_team_id,
                        team_group_id = EXCLUDED.team_group_id,
                        team_group_name = EXCLUDED.team_group_name,
                        primary_color = EXCLUDED.primary_color,
                        secondary_color = EXCLUDED.secondary_color,
                        aliases = EXCLUDED.aliases,
                        updated_at = NOW()
                """),
                {
                    "team_id": team["team_id"],
                    "sport": team["sport"],
                    "team_name": team["team_name"],
                    "team_abbr": team["team_abbr"],
                    "espn_team_id": espn_team_id,
                    "team_group_id": team_group_id,
                    "team_group_name": team_group_name,
                    "primary_color": team["primary_color"],
                    "secondary_color": team["secondary_color"],
                    "aliases": team["aliases"],
                }
            )
    else:
        # OLD SCHEMA: Insert into teams + team_groups (original logic)
        # Insert conferences first (parent table)
        for conference in conferences:
            conn.execute(
                sa.text("""
                    INSERT INTO team_groups (
                        team_group_id, team_group_name, sport, group_type, parent_group_id, level, created_at
                    )
                    VALUES (
                        :team_group_id, :team_group_name, :sport, :group_type, :parent_group_id, :level, NOW()
                    )
                    ON CONFLICT (team_group_id)
                    DO UPDATE SET
                        team_group_name = EXCLUDED.team_group_name,
                        sport = EXCLUDED.sport,
                        group_type = EXCLUDED.group_type,
                        parent_group_id = EXCLUDED.parent_group_id,
                        level = EXCLUDED.level
                """),
                {
                    "team_group_id": conference["team_group_id"],
                    "team_group_name": conference["team_group_name"],
                    "sport": conference["sport"],
                    "group_type": conference["group_type"],
                    "parent_group_id": conference.get("parent_group_id"),
                    "level": conference["level"],
                }
            )

        # Insert teams second (child table with FK)
        for team in teams:
            conn.execute(
                sa.text("""
                    INSERT INTO teams (
                        team_id, sport, team_name, team_abbr, team_group_id,
                        primary_color, secondary_color, aliases, created_at, updated_at
                    )
                    VALUES (
                        :team_id, :sport, :team_name, :team_abbr, :team_group_id,
                        :primary_color, :secondary_color, :aliases, NOW(), NOW()
                    )
                    ON CONFLICT (team_id)
                    DO UPDATE SET
                        sport = EXCLUDED.sport,
                        team_name = EXCLUDED.team_name,
                        team_abbr = EXCLUDED.team_abbr,
                        team_group_id = EXCLUDED.team_group_id,
                        primary_color = EXCLUDED.primary_color,
                        secondary_color = EXCLUDED.secondary_color,
                        aliases = EXCLUDED.aliases,
                        updated_at = NOW()
                """),
                {
                    "team_id": team["team_id"],
                    "sport": team["sport"],
                    "team_name": team["team_name"],
                    "team_abbr": team["team_abbr"],
                    "team_group_id": team["team_group_id"],
                    "primary_color": team["primary_color"],
                    "secondary_color": team["secondary_color"],
                    "aliases": team["aliases"],
                }
            )


def downgrade():
    """Remove seeded dimensional data for NCAA Men's Basketball.

    Schema-aware: works with both old (teams/team_groups) and new (dim_team) schemas.
    """
    conn = op.get_bind()

    # Check which schema exists
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()
    using_new_schema = "dim_team" in table_names

    if using_new_schema:
        # NEW SCHEMA: Delete from dim_team
        conn.execute(sa.text("DELETE FROM dim_team WHERE sport = 'ncaam'"))
    else:
        # OLD SCHEMA: Delete from teams and team_groups
        conn.execute(sa.text("DELETE FROM teams WHERE sport = 'ncaam'"))
        conn.execute(sa.text("DELETE FROM team_groups WHERE sport = 'ncaam'"))
