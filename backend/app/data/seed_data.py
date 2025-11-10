"""
Sample data seeding script for GamePulse multi-sport schema.

Seeds:
- 5 NCAAM teams (Duke, UNC, Kansas, Kentucky, Villanova)
- 2 team groups (ACC, Big 12 conferences)
- 1 rivalry (Duke-UNC with rivalry_factor=1.5)
- 1 sample game

This script is idempotent - running multiple times won't create duplicates.
Uses INSERT ... ON CONFLICT for PostgreSQL upsert behavior.
"""
from datetime import datetime
from sqlalchemy import text
from sqlmodel import Session, select

from app.core.db import engine
from app.models import Team, TeamGroup, TeamRivalry, Game


def seed_team_groups(session: Session) -> None:
    """Seed NCAAM conference data (ACC, Big 12)."""

    groups = [
        TeamGroup(
            team_group_id="ncaam_acc",
            team_group_name="ACC",
            sport="ncaam",
            group_type="conference",
            parent_group_id=None,
            level=1,
        ),
        TeamGroup(
            team_group_id="ncaam_big12",
            team_group_name="Big 12",
            sport="ncaam",
            group_type="conference",
            parent_group_id=None,
            level=1,
        ),
    ]

    for group in groups:
        # Check if exists
        existing = session.exec(
            select(TeamGroup).where(TeamGroup.team_group_id == group.team_group_id)
        ).first()

        if not existing:
            session.add(group)
            print(f"✅ Created team group: {group.team_group_name}")
        else:
            print(f"⏭️  Team group already exists: {group.team_group_name}")

    session.commit()


def seed_teams(session: Session) -> None:
    """Seed 5 NCAAM teams (Duke, UNC, Kansas, Kentucky, Villanova)."""

    teams = [
        Team(
            team_id="ncaam_duke",
            sport="ncaam",
            team_name="Duke Blue Devils",
            team_abbr="DUKE",
            team_group_id="ncaam_acc",
            primary_color="#003087",
            secondary_color="#FFFFFF",
            aliases=["Duke", "Blue Devils", "DU"],
        ),
        Team(
            team_id="ncaam_unc",
            sport="ncaam",
            team_name="North Carolina Tar Heels",
            team_abbr="UNC",
            team_group_id="ncaam_acc",
            primary_color="#7BAFD4",
            secondary_color="#FFFFFF",
            aliases=["UNC", "North Carolina", "Tar Heels", "Carolina"],
        ),
        Team(
            team_id="ncaam_kansas",
            sport="ncaam",
            team_name="Kansas Jayhawks",
            team_abbr="KU",
            team_group_id="ncaam_big12",
            primary_color="#0051BA",
            secondary_color="#E8000D",
            aliases=["Kansas", "Jayhawks", "KU"],
        ),
        Team(
            team_id="ncaam_kentucky",
            sport="ncaam",
            team_name="Kentucky Wildcats",
            team_abbr="UK",
            team_group_id=None,  # Not in ACC or Big 12 (SEC)
            primary_color="#0033A0",
            secondary_color="#FFFFFF",
            aliases=["Kentucky", "Wildcats", "UK"],
        ),
        Team(
            team_id="ncaam_villanova",
            sport="ncaam",
            team_name="Villanova Wildcats",
            team_abbr="NOVA",
            team_group_id=None,  # Not in ACC or Big 12 (Big East)
            primary_color="#00205B",
            secondary_color="#95C8E1",
            aliases=["Villanova", "Wildcats", "Nova"],
        ),
    ]

    for team in teams:
        # Check if exists
        existing = session.exec(
            select(Team).where(Team.team_id == team.team_id)
        ).first()

        if not existing:
            session.add(team)
            print(f"✅ Created team: {team.team_name}")
        else:
            print(f"⏭️  Team already exists: {team.team_name}")

    session.commit()


def seed_rivalries(session: Session) -> None:
    """Seed Duke-UNC historic rivalry."""

    # Check if rivalry exists (in either direction)
    existing = session.exec(
        select(TeamRivalry).where(
            ((TeamRivalry.team_a_id == "ncaam_duke") & (TeamRivalry.team_b_id == "ncaam_unc"))
            | ((TeamRivalry.team_a_id == "ncaam_unc") & (TeamRivalry.team_b_id == "ncaam_duke"))
        )
    ).first()

    if not existing:
        rivalry = TeamRivalry(
            team_a_id="ncaam_duke",  # Alphabetically first per CHECK constraint
            team_b_id="ncaam_unc",
            rivalry_factor=1.5,
            rivalry_type="historic",
            notes="Tobacco Road rivalry - one of college basketball's greatest matchups",
        )
        session.add(rivalry)
        session.commit()
        print("✅ Created rivalry: Duke-UNC (Tobacco Road)")
    else:
        print("⏭️  Rivalry already exists: Duke-UNC")


def seed_sample_game(session: Session) -> None:
    """Seed a sample Duke-UNC game."""

    game_id = "ncaam_sample_duke_unc_2024"

    # Check if exists
    existing = session.exec(
        select(Game).where(Game.game_id == game_id)
    ).first()

    if not existing:
        game = Game(
            game_id=game_id,
            sport="ncaam",
            game_date=datetime(2024, 2, 3, 18, 0),  # Feb 3, 2024 at 6pm
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
            home_score=73,
            away_score=68,
            game_status="final",
            game_clock=None,
            game_start_time=datetime(2024, 2, 3, 18, 15),
            game_end_time=datetime(2024, 2, 3, 20, 30),
            venue="Cameron Indoor Stadium",
            game_type="regular_season",
            rivalry_factor=1.5,
            broadcast_network="ESPN",
            attendance=9314,
        )
        session.add(game)
        session.commit()
        print("✅ Created sample game: Duke vs UNC (Feb 3, 2024)")
    else:
        print("⏭️  Sample game already exists: Duke vs UNC")


def main() -> None:
    """Run all seed functions in correct dependency order."""

    print("\n🌱 Starting GamePulse sample data seeding...\n")

    with Session(engine) as session:
        # Order matters: groups → teams → rivalries/games
        seed_team_groups(session)
        print()

        seed_teams(session)
        print()

        seed_rivalries(session)
        print()

        seed_sample_game(session)

    print("\n✅ Sample data seeding complete!\n")


if __name__ == "__main__":
    main()
