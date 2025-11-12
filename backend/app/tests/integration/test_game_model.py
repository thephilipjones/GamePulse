"""
Integration tests for Game model database operations.

Tests database insertion, querying, foreign key constraints, indexes,
and updates with actual PostgreSQL database.
"""

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, text

from app.core.db import engine
from app.models.game import Game
from app.models.team import Team, TeamGroup


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Provide a database session with transaction rollback for test isolation.

    Each test gets a fresh transaction that is rolled back after the test,
    ensuring no test data persists in the database.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def sample_teams(db_session: Session) -> dict[str, Any]:
    """
    Create sample teams for testing Game foreign key relationships.

    Uses Duke and UNC from seeded dimensional data if available,
    or creates test teams and conference if needed.
    """
    # Check if Duke and UNC exist from Story 2.1 seed data
    duke = db_session.exec(select(Team).where(Team.team_id == "ncaam_duke")).first()
    unc = db_session.exec(select(Team).where(Team.team_id == "ncaam_unc")).first()

    if duke and unc:
        return {"duke": duke, "unc": unc}

    # Create ACC conference if not exists
    acc = db_session.exec(
        select(TeamGroup).where(TeamGroup.team_group_id == "acc")
    ).first()
    if not acc:
        acc = TeamGroup(
            team_group_id="acc",
            sport="ncaam",
            team_group_name="Atlantic Coast Conference",
            group_type="conference",
        )
        db_session.add(acc)
        db_session.commit()

    # If seed data not available, create test teams
    test_duke = Team(
        team_id="ncaam_duke",
        sport="ncaam",
        team_name="Duke Blue Devils",
        team_group_id="acc",
        primary_color="#003087",
        secondary_color="#FFFFFF",
    )
    test_unc = Team(
        team_id="ncaam_unc",
        sport="ncaam",
        team_name="North Carolina Tar Heels",
        team_group_id="acc",
        primary_color="#7BAFD4",
        secondary_color="#FFFFFF",
    )

    db_session.add(test_duke)
    db_session.add(test_unc)
    db_session.commit()
    db_session.refresh(test_duke)
    db_session.refresh(test_unc)

    return {"duke": test_duke, "unc": test_unc}


class TestGameDatabaseOperations:
    """Integration tests for Game model database operations."""

    def test_insert_game_to_database(
        self, db_session: Session, sample_teams: dict[str, Any]
    ) -> None:
        """Test inserting a game with valid foreign keys and querying it back."""
        game_date = datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
        game = Game(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=game_date,
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
            home_score=75,
            away_score=72,
            game_status="final",
            venue="Cameron Indoor Stadium",
            game_type="regular_season",
        )

        # Insert game
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        # Query back by game_id
        retrieved_game = db_session.exec(
            select(Game).where(Game.game_id == "ncaam_401234567")
        ).first()

        # Verify all fields persisted correctly
        assert retrieved_game is not None
        assert retrieved_game.game_id == "ncaam_401234567"
        assert retrieved_game.sport == "ncaam"
        # Database stores timestamps without timezone, so compare as naive datetimes
        assert retrieved_game.game_date.replace(tzinfo=timezone.utc) == game_date
        assert retrieved_game.home_team_id == sample_teams["duke"].team_id
        assert retrieved_game.away_team_id == sample_teams["unc"].team_id
        assert retrieved_game.home_score == 75
        assert retrieved_game.away_score == 72
        assert retrieved_game.game_status == "final"
        assert retrieved_game.venue == "Cameron Indoor Stadium"
        assert retrieved_game.game_type == "regular_season"
        assert retrieved_game.created_at is not None
        assert retrieved_game.updated_at is not None

    def test_foreign_key_constraint_enforcement(self, db_session: Session) -> None:
        """Test that database enforces foreign key constraints on team_id."""
        game = Game(
            game_id="ncaam_401999999",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id="ncaam_fake_team",  # Invalid team_id
            away_team_id="ncaam_another_fake_team",  # Invalid team_id
        )

        db_session.add(game)

        # Should raise IntegrityError due to foreign key violation
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Verify error message mentions foreign key constraint
        assert "foreign key constraint" in str(exc_info.value).lower()

        # Rollback the failed transaction
        db_session.rollback()

    def test_query_games_by_date(
        self, db_session: Session, sample_teams: dict[str, Any]
    ) -> None:
        """Test querying games by date with index usage."""
        # Insert games with different dates
        game1 = Game(
            game_id="ncaam_401000001",
            sport="ncaam",
            game_date=datetime(2024, 3, 10, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
        )
        game2 = Game(
            game_id="ncaam_401000002",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
        )
        game3 = Game(
            game_id="ncaam_401000003",
            sport="ncaam",
            game_date=datetime(2024, 3, 20, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
        )

        db_session.add(game1)
        db_session.add(game2)
        db_session.add(game3)
        db_session.commit()

        # Query games on specific date
        target_date = datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
        games = db_session.exec(select(Game).where(Game.game_date == target_date)).all()

        # Verify correct filtering
        assert len(games) == 1
        assert games[0].game_id == "ncaam_401000002"

        # Query games within date range
        start_date = datetime(2024, 3, 12, 0, 0, 0, tzinfo=timezone.utc)
        end_date = datetime(2024, 3, 22, 0, 0, 0, tzinfo=timezone.utc)
        games_in_range = db_session.exec(
            select(Game).where(Game.game_date >= start_date, Game.game_date <= end_date)
        ).all()

        assert len(games_in_range) == 2
        game_ids = {game.game_id for game in games_in_range}
        assert game_ids == {"ncaam_401000002", "ncaam_401000003"}

    def test_query_games_by_status(
        self, db_session: Session, sample_teams: dict[str, Any]
    ) -> None:
        """Test querying games by status with index usage."""
        # Insert games with different statuses
        scheduled_game = Game(
            game_id="ncaam_402000001",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
            game_status="scheduled",
        )
        live_game = Game(
            game_id="ncaam_402000002",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 20, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
            game_status="live",
        )
        final_game = Game(
            game_id="ncaam_402000003",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 21, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
            game_status="final",
        )

        db_session.add(scheduled_game)
        db_session.add(live_game)
        db_session.add(final_game)
        db_session.commit()

        # Query by status
        live_games = db_session.exec(
            select(Game).where(Game.game_status == "live")
        ).all()
        assert len(live_games) == 1
        assert live_games[0].game_id == "ncaam_402000002"

        final_games = db_session.exec(
            select(Game).where(Game.game_status == "final")
        ).all()
        assert len(final_games) == 1
        assert final_games[0].game_id == "ncaam_402000003"

    def test_query_games_by_sport(
        self, db_session: Session, sample_teams: dict[str, Any]
    ) -> None:
        """Test querying games by sport with index usage."""
        # Insert NCAAM game
        ncaam_game = Game(
            game_id="ncaam_403000001",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
        )

        db_session.add(ncaam_game)
        db_session.commit()

        # Query by sport
        ncaam_games = db_session.exec(select(Game).where(Game.sport == "ncaam")).all()

        # Should find at least the one we just inserted
        assert len(ncaam_games) >= 1
        game_ids = {game.game_id for game in ncaam_games}
        assert "ncaam_403000001" in game_ids

    def test_update_game_scores(
        self, db_session: Session, sample_teams: dict[str, Any]
    ) -> None:
        """Test updating game scores and verifying updated_at timestamp changes."""
        # Insert game with initial scores
        game = Game(
            game_id="ncaam_404000001",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
            home_score=0,
            away_score=0,
            game_status="live",
        )

        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        original_updated_at = game.updated_at

        # Update scores
        game.home_score = 42
        game.away_score = 38
        game.updated_at = datetime.now(timezone.utc)
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        # Verify scores updated
        assert game.home_score == 42
        assert game.away_score == 38

        # Verify updated_at changed
        assert game.updated_at > original_updated_at

    def test_database_indexes_exist(self, db_session: Session) -> None:
        """Test that all required indexes exist in pg_indexes."""
        # Query PostgreSQL system catalog for games table indexes
        index_query = text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'games'
            ORDER BY indexname
            """
        )

        result = db_session.execute(index_query)
        index_names = [row[0] for row in result]

        # Verify required indexes exist
        required_indexes = [
            "games_pkey",  # Primary key index
            "ix_games_game_date",  # Date index
            "ix_games_game_status",  # Status index
            "ix_games_sport",  # Sport index
            "ix_games_game_type",  # Game type index
            "idx_games_teams",  # Composite teams index
        ]

        for required_index in required_indexes:
            assert required_index in index_names, f"Missing: {required_index}"

    def test_game_type_filtering(
        self, db_session: Session, sample_teams: dict[str, Any]
    ) -> None:
        """Test querying games by game_type (regular_season vs postseason)."""
        # Insert games with different types
        regular_game = Game(
            game_id="ncaam_405000001",
            sport="ncaam",
            game_date=datetime(2024, 2, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
            game_type="regular_season",
        )
        postseason_game = Game(
            game_id="ncaam_405000002",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id=sample_teams["duke"].team_id,
            away_team_id=sample_teams["unc"].team_id,
            game_type="postseason",
        )

        db_session.add(regular_game)
        db_session.add(postseason_game)
        db_session.commit()

        # Query by game_type
        postseason_games = db_session.exec(
            select(Game).where(Game.game_type == "postseason")
        ).all()

        assert len(postseason_games) >= 1
        game_ids = {game.game_id for game in postseason_games}
        assert "ncaam_405000002" in game_ids
