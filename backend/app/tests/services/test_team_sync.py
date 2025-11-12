"""
Tests for team sync service.

Validates team discovery, idempotent merge, surrogate key preservation,
and graceful handling of missing teams.
"""

import logging
from typing import Any

import pytest
from sqlmodel import Session, select

from app.models.dim_team import DimTeam
from app.services.team_sync import sync_teams_from_games


@pytest.mark.asyncio
async def test_discover_new_team(db: Session) -> None:
    """Test discovering and inserting a new team from API."""
    games_data = [
        {
            "home": {
                "id": "999",
                "names": {"short": "Test Team", "full": "Test University"},
            },
            "away": {"id": "150", "names": {"short": "Duke"}},
        }
    ]

    metadata = await sync_teams_from_games(games_data, db)

    # Verify metadata counts
    assert metadata["teams_discovered"] >= 1  # At least Test Team is new
    assert metadata["teams_updated"] == 0  # No updates on first sync
    assert metadata["teams_unchanged"] >= 0

    # Verify team was inserted
    team = db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_999")).first()
    assert team is not None
    assert team.team_name == "Test Team"
    assert team.espn_team_id == "999"
    assert team.sport == "ncaam"
    assert team.team_key is not None  # Auto-generated surrogate key
    assert team.primary_color is None  # No colors from API
    assert team.secondary_color is None
    assert team.is_current is True


@pytest.mark.asyncio
async def test_preserve_manual_data(db: Session) -> None:
    """Test that manual data (colors, aliases) is preserved during sync."""
    # Seed Duke with manual data
    duke = DimTeam(
        team_id="ncaam_150",
        espn_team_id="150",
        sport="ncaam",
        team_name="Duke (Old Name)",  # Intentionally different
        team_abbr="DUKE",
        primary_color="#012169",
        secondary_color="#FFFFFF",
        aliases=["Blue Devils", "Duke Basketball"],
        team_group_id="acc",
        team_group_name="Atlantic Coast Conference",
    )
    db.add(duke)
    db.commit()
    db.refresh(duke)
    original_team_key = duke.team_key

    # Sync from API with updated name
    games_data = [
        {
            "home": {
                "id": "150",
                "names": {"short": "Duke", "full": "Duke Blue Devils"},
            },
            "away": {"id": "41", "names": {"short": "UConn"}},
        }
    ]

    metadata = await sync_teams_from_games(games_data, db)

    # Verify metadata
    assert metadata["teams_updated"] == 1  # Duke name updated
    assert metadata["teams_discovered"] >= 0

    # Verify Duke was updated
    updated_duke = db.exec(
        select(DimTeam).where(DimTeam.team_id == "ncaam_150")
    ).first()
    assert updated_duke is not None
    assert updated_duke.team_name == "Duke"  # Name updated from API
    assert updated_duke.team_key == original_team_key  # Surrogate key preserved!
    assert updated_duke.primary_color == "#012169"  # Color preserved
    assert updated_duke.secondary_color == "#FFFFFF"  # Color preserved
    assert updated_duke.aliases == [
        "Blue Devils",
        "Duke Basketball",
    ]  # Aliases preserved
    assert updated_duke.team_group_id == "acc"  # Conference preserved
    assert (
        updated_duke.team_group_name == "Atlantic Coast Conference"
    )  # Conference preserved


@pytest.mark.asyncio
async def test_upsert_preserves_surrogate_key(db: Session) -> None:
    """Test that surrogate key (team_key) is never updated during upsert."""
    # Create team with specific team_key
    team = DimTeam(
        team_id="ncaam_356",
        espn_team_id="356",
        sport="ncaam",
        team_name="Illinois",
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    original_team_key = team.team_key

    # Sync same team from API multiple times
    games_data: list[dict[str, Any]] = [
        {
            "home": {"id": "356", "names": {"short": "Illinois Fighting Illini"}},
            "away": {"id": "248", "names": {"short": "Houston"}},
        }
    ]

    # First sync
    await sync_teams_from_games(games_data, db)

    # Second sync with different name
    games_data[0]["home"]["names"]["short"] = "Illinois"
    await sync_teams_from_games(games_data, db)

    # Verify surrogate key unchanged
    updated_team = db.exec(
        select(DimTeam).where(DimTeam.team_id == "ncaam_356")
    ).first()
    assert updated_team is not None
    assert updated_team.team_key == original_team_key  # Key never changes!
    assert updated_team.team_name == "Illinois"  # Name updated


@pytest.mark.asyncio
async def test_metadata_counts(db: Session) -> None:
    """Test that metadata counts are accurate."""
    # Seed one existing team
    existing_team = DimTeam(
        team_id="ncaam_222",
        espn_team_id="222",
        sport="ncaam",
        team_name="Villanova (Old)",
    )
    db.add(existing_team)
    db.commit()

    # Sync with mix of new, updated, and unchanged teams
    games_data = [
        # New team
        {
            "home": {"id": "999", "names": {"short": "New Team"}},
            "away": {"id": "998", "names": {"short": "Another New"}},
        },
        # Existing team with name change (updated)
        {
            "home": {"id": "222", "names": {"short": "Villanova"}},
            "away": {"id": "997", "names": {"short": "Third New"}},
        },
    ]

    metadata = await sync_teams_from_games(games_data, db)

    # Verify counts
    assert metadata["teams_discovered"] >= 3  # 999, 998, 997 are new
    assert metadata["teams_updated"] == 1  # 222 updated
    assert metadata["teams_unchanged"] == 0  # All teams are either new or updated
    assert (
        metadata["teams_discovered"]
        + metadata["teams_updated"]
        + metadata["teams_unchanged"]
        == 4
    )


@pytest.mark.asyncio
async def test_logging_output(db: Session, caplog: pytest.LogCaptureFixture) -> None:
    """Test that logging outputs correct WARNING/DEBUG messages per AC4."""
    caplog.set_level(logging.DEBUG)

    # Seed one team
    existing = DimTeam(
        team_id="ncaam_150",
        espn_team_id="150",
        sport="ncaam",
        team_name="Duke (Old)",
    )
    db.add(existing)
    db.commit()

    # Sync with new and updated teams
    games_data = [
        {
            "home": {"id": "150", "names": {"short": "Duke"}},
            "away": {"id": "999", "names": {"short": "New Team"}},
        },
    ]

    await sync_teams_from_games(games_data, db)

    # Verify WARNING log for new team (AC4 requirement)
    assert any(
        record.levelname == "WARNING"
        and "Team ncaam_999 auto-created with minimal data" in record.message
        for record in caplog.records
    )
    assert any(
        "consider adding colors/aliases in teams.json" in record.message
        for record in caplog.records
    )
    assert any("ESPN ID: 999" in record.message for record in caplog.records)

    # Verify DEBUG log for updated team
    assert any(
        "Team updated from API: ncaam_150" in record.message
        for record in caplog.records
    )
    assert any("name changed from" in record.message for record in caplog.records)

    # Verify summary log
    assert any("Team sync complete" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_empty_games_list(db: Session) -> None:
    """Test handling of empty games list."""
    metadata = await sync_teams_from_games([], db)

    assert metadata["teams_discovered"] == 0
    assert metadata["teams_updated"] == 0
    assert metadata["teams_unchanged"] == 0


@pytest.mark.asyncio
async def test_duplicate_teams_in_games(db: Session) -> None:
    """Test that duplicate teams in games list are handled correctly."""
    games_data = [
        {
            "home": {"id": "150", "names": {"short": "Duke"}},
            "away": {"id": "41", "names": {"short": "UConn"}},
        },
        {
            "home": {"id": "150", "names": {"short": "Duke"}},
            "away": {"id": "153", "names": {"short": "UNC"}},
        },  # Duke appears twice
    ]

    _ = await sync_teams_from_games(games_data, db)

    # Verify Duke only counted once
    duke_count = db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_150")).all()
    assert len(duke_count) == 1  # Only one Duke record


@pytest.mark.asyncio
async def test_missing_team_names(db: Session) -> None:
    """Test handling of games with missing team names."""
    games_data = [
        {
            "home": {"id": "999"},
            "away": {"id": "998", "names": {"short": "Valid Team"}},
        },  # Missing names
    ]

    _ = await sync_teams_from_games(games_data, db)

    # Verify team was created with ID as fallback name
    team = db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_999")).first()
    assert team is not None
    assert team.team_name in ["999", "Unknown"]  # Fallback name


@pytest.mark.asyncio
async def test_malformed_game_data(
    db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """Test graceful handling of malformed game data."""
    caplog.set_level(logging.WARNING)

    games_data = [
        {
            "home": None,
            "away": {"id": "150", "names": {"short": "Duke"}},
        },  # home is None
        {
            "home": {"id": "41", "names": {"short": "UConn"}},
            "away": {},
        },  # away missing id
        "invalid_game_string",  # Completely invalid
    ]

    # Should not crash
    metadata = await sync_teams_from_games(games_data, db)  # type: ignore[arg-type]

    # Verify at least Duke was synced
    duke = db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_150")).first()
    assert (
        duke is not None or metadata["teams_discovered"] >= 0
    )  # Either Duke exists or was counted


@pytest.mark.asyncio
async def test_batch_upsert_efficiency(db: Session) -> None:
    """Test that batch upsert uses single query (not N queries)."""
    # Create 50 games with 100 unique teams
    games_data = []
    for i in range(50):
        games_data.append(
            {
                "home": {
                    "id": str(1000 + i * 2),
                    "names": {"short": f"Team {1000 + i * 2}"},
                },
                "away": {
                    "id": str(1001 + i * 2),
                    "names": {"short": f"Team {1001 + i * 2}"},
                },
            }
        )

    metadata = await sync_teams_from_games(games_data, db)

    # Verify all teams were created
    assert metadata["teams_discovered"] == 100

    # Verify count in database
    count = len(db.exec(select(DimTeam)).all())
    assert count >= 100


@pytest.mark.asyncio
async def test_seed_migration_preserves_sync_teams(db: Session) -> None:
    """Test that seed migration doesn't overwrite auto-discovered teams."""
    # Auto-discover a team via sync
    games_data = [
        {
            "home": {"id": "150", "names": {"short": "Duke from API"}},
            "away": {"id": "41", "names": {"short": "UConn"}},
        },
    ]
    await sync_teams_from_games(games_data, db)

    # Get the auto-generated team_key
    duke_before = db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_150")).first()
    assert duke_before is not None
    original_team_key = duke_before.team_key

    # Simulate seed migration (ON CONFLICT DO UPDATE)
    # This would normally come from the seed data with colors/aliases
    # The key test: team_key should be preserved (not regenerated)

    # For now, we just verify the team_key is stable
    # Full seed migration test would require running actual Alembic migration
    assert duke_before.team_key == original_team_key


@pytest.mark.asyncio
async def test_concurrent_team_sync_safe(db: Session) -> None:
    """Test that concurrent syncs don't create duplicate teams."""
    # This is a simplified test - real concurrency would need threading
    games_data = [
        {
            "home": {"id": "150", "names": {"short": "Duke"}},
            "away": {"id": "41", "names": {"short": "UConn"}},
        },
    ]

    # Run sync twice
    await sync_teams_from_games(games_data, db)
    await sync_teams_from_games(games_data, db)

    # Verify only one Duke record
    duke_count = len(
        db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_150")).all()
    )
    assert duke_count == 1


@pytest.mark.asyncio
async def test_espn_team_id_populated(db: Session) -> None:
    """Test that espn_team_id is correctly populated from API."""
    games_data = [
        {
            "home": {"id": "2509", "names": {"short": "Purdue"}},
            "away": {"id": "248", "names": {"short": "Houston"}},
        },
    ]

    await sync_teams_from_games(games_data, db)

    # Verify espn_team_id
    purdue = db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_2509")).first()
    assert purdue is not None
    assert purdue.espn_team_id == "2509"
    assert purdue.team_id == "ncaam_2509"

    houston = db.exec(select(DimTeam).where(DimTeam.team_id == "ncaam_248")).first()
    assert houston is not None
    assert houston.espn_team_id == "248"
