# Dimensional Data Seed Files

This directory contains JSON seed files for GamePulse dimensional data (teams, conferences). These files provide manually curated metadata for high-visibility teams while allowing automatic discovery of new teams from the NCAA API.

## Hybrid Data Strategy

GamePulse uses a **hybrid approach** combining manual curation with automatic API sync:

### Manual Seed Data (teams.json, conferences.json)
- **Purpose**: Provide rich metadata for high-profile teams
- **Contents**: Team colors, aliases (for Reddit matching), conference affiliations
- **Maintenance**: Updated manually for major conference realignments or new teams
- **Priority**: Manual data is **preserved** during API sync (never overwritten)

### Automatic API Sync (team_sync.py service)
- **Purpose**: Automatically discover teams encountered in game data
- **Contents**: Team names, ESPN IDs from NCAA API responses
- **Maintenance**: Zero maintenance - fully automatic
- **Coverage**: All 350+ NCAA Division I teams

### When to Use Each

| Scenario | Approach | Example |
|----------|----------|---------|
| Adding a new high-profile team | **Manual seed** | Add to `teams.json` with colors/aliases |
| Processing games with unknown teams | **Automatic** | Team created automatically on first encounter |
| Updating team names (NCAA rebrand) | **Automatic** | API sync updates name, preserves colors |
| Adding colors to auto-discovered team | **Manual seed** | Add entry to `teams.json`, re-run seed migration |

## Seed Data Files

### conferences.json

Contains NCAA Division I basketball conferences with hierarchical group information:

```json
{
  "conferences": [
    {
      "team_group_id": "ncaam_acc",
      "team_group_name": "Atlantic Coast Conference",
      "sport": "ncaam",
      "group_type": "conference",
      "parent_group_id": null,
      "level": 1
    }
  ]
}
```

**Fields:**
- `team_group_id`: Unique identifier (natural key)
- `team_group_name`: Full conference name
- `sport`: Sport code (`ncaam` for NCAA Men's Basketball)
- `group_type`: Always `"conference"` for top-level groups
- `parent_group_id`: NULL for conferences (future: divisions, regions)
- `level`: 1 for conferences (future: sub-groups)

### teams.json

Contains manually curated team data with rich metadata:

```json
{
  "teams": [
    {
      "team_id": "ncaam_150",
      "sport": "ncaam",
      "team_name": "Duke",
      "team_abbr": "DUKE",
      "team_group_id": "ncaam_acc",
      "primary_color": "#003087",
      "secondary_color": "#FFFFFF",
      "aliases": ["Duke", "Blue Devils", "Duke Blue Devils"]
    }
  ]
}
```

**Fields:**
- `team_id`: Natural key format `{sport}_{espn_id}` (e.g., `ncaam_150`)
- `sport`: Sport code (`ncaam`)
- `team_name`: Official short name
- `team_abbr`: 3-5 character abbreviation
- `team_group_id`: Reference to conference in `conferences.json`
- `primary_color`: Hex color (e.g., `#003087`)
- `secondary_color`: Hex color (e.g., `#FFFFFF`)
- `aliases`: Array of strings for Reddit fuzzy matching

## Merge Logic: What's Updated vs. Preserved

When team data is synced from the NCAA API, the following merge logic applies:

### ✅ UPDATED (from API)
- `team_name` - Updated to match current NCAA branding
- `espn_team_id` - Populated if previously NULL
- `updated_at` - Timestamp refreshed

### 🔒 PRESERVED (manual data never overwritten)
- `team_key` - **Surrogate primary key (immutable)**
- `primary_color` - Manual curation preserved
- `secondary_color` - Manual curation preserved
- `aliases` - Reddit matching data preserved
- `team_group_id` - Conference affiliation preserved
- `team_group_name` - Conference name preserved
- `team_abbr` - Abbreviation preserved
- `is_current`, `valid_from`, `valid_to` - SCD Type 2 fields preserved

### Schema Fields Reference

| Field | Source | Updated by API Sync? | Indexed? | Notes |
|-------|--------|---------------------|----------|-------|
| `team_key` | Auto-generated | ❌ Never | PK | Surrogate key (immutable) |
| `team_id` | Seed + API | ❌ Never | ✅ Unique | Natural key |
| `espn_team_id` | Seed + API | ✅ If NULL | ✅ | ESPN team ID |
| `sport` | Seed + API | ❌ | ✅ | Sport code |
| `team_name` | Seed + API | ✅ Always | ❌ | Official name |
| `team_abbr` | Seed only | ❌ | ❌ | Abbreviation |
| `team_group_id` | Seed only | ❌ | ❌ | Conference ID |
| `team_group_name` | Seed only | ❌ | ❌ | Conference name |
| `primary_color` | Seed only | ❌ | ❌ | Hex color |
| `secondary_color` | Seed only | ❌ | ❌ | Hex color |
| `aliases` | Seed only | ❌ | ❌ | Array of strings |
| `is_current` | Auto-generated | ❌ | ❌ | SCD Type 2 |
| `valid_from` | Auto-generated | ❌ | ❌ | SCD Type 2 |
| `valid_to` | Auto-generated | ❌ | ❌ | SCD Type 2 |
| `created_at` | Auto-generated | ❌ | ❌ | Audit timestamp |
| `updated_at` | Auto-generated | ✅ Always | ❌ | Audit timestamp |

## Manual Override Process

To add colors, aliases, or conference information to an auto-discovered team:

### Step 1: Add Entry to teams.json

```json
{
  "team_id": "ncaam_999",
  "sport": "ncaam",
  "team_name": "Example University",
  "team_abbr": "EXU",
  "team_group_id": "ncaam_example_conf",
  "primary_color": "#FF0000",
  "secondary_color": "#0000FF",
  "aliases": ["Example", "Example U", "Example Eagles"]
}
```

### Step 2: Re-run Seed Migration (Development)

```bash
# Seed migration is idempotent - safe to run multiple times
docker compose exec backend alembic upgrade head
```

**Result**: Existing `team_key` preserved, colors/aliases added to auto-discovered team.

### Step 3: Production Deployment

Seed data changes deploy automatically via GitHub Actions:
1. Commit `teams.json` changes to `main` branch
2. Push triggers deployment workflow
3. Alembic migration runs on production instance
4. Team metadata enriched without data loss

## Migration Reference

### Seed Migration (7a8f23177a57_seed_dimensional_data.py)

**Purpose**: Load initial team and conference data from JSON files

**Behavior**:
- **Idempotent**: Safe to run multiple times (uses `ON CONFLICT DO UPDATE`)
- **Schema-aware**: Works with both old (teams/team_groups) and new (dim_team) schemas
- **Preserves `team_key`**: Auto-discovered teams keep their surrogate keys
- **Updates allowed fields**: Updates only fields from seed data (name, colors, aliases)

**When to Run**:
- Initial project setup
- After adding new teams to `teams.json`
- After updating team colors/aliases
- After conference realignment (update `conferences.json`)

### ESPN ID Migration (de4a5062ce6e_add_espn_team_id_to_dim_team.py)

**Purpose**: Add `espn_team_id` column and backfill from `team_id`

**Behavior**:
- Adds `espn_team_id VARCHAR NULL` column
- Creates index on `espn_team_id` for lookup performance
- Backfills by extracting from `team_id` (e.g., "ncaam_150" → "150")
- Reversible via downgrade

**When to Run**:
- Automatically runs during deployment (Alembic upgrade head)
- Part of Story 2-3b implementation

## API Sync Service

The `team_sync.py` service automatically discovers teams from game data:

### Usage

```python
from app.services.team_sync import sync_teams_from_games

# Fetch games from NCAA API
games_data = ncaa_client.fetch_todays_games()

# Sync teams (happens before game insert to avoid FK failures)
metadata = await sync_teams_from_games(games_data, session)
session.commit()

# Log results
logger.info(f"Teams synced: {metadata['teams_discovered']} discovered, "
            f"{metadata['teams_updated']} updated")
```

### Return Metadata

```python
{
  "teams_discovered": 5,  # New teams inserted
  "teams_updated": 2,     # Existing teams with name changes
  "teams_unchanged": 13   # Teams in API but no changes needed
}
```

### Integration with Dagster

For Story 2-4 (Dagster Polling Worker), integrate team sync **before** game processing:

```python
@asset
def ncaa_games(context: AssetExecutionContext) -> None:
    # 1. Fetch games from API
    games_data = ncaa_client.fetch_todays_games()

    # 2. SYNC TEAMS FIRST (Story 2-3b)
    team_metadata = await sync_teams_from_games(games_data, session)
    context.log.info(f"Team sync: {team_metadata}")

    # 3. Process games (teams guaranteed to exist)
    for game_data in games_data:
        game = parse_game_data(game_data)
        session.merge(game)  # Upsert game

    session.commit()
```

## Troubleshooting

### Team discovered but missing colors

**Symptom**: Team exists in database but `primary_color` is NULL

**Solution**: Add team to `teams.json` and re-run seed migration:
```bash
docker compose exec backend alembic upgrade head
```

### Duplicate team records

**Symptom**: Multiple rows with same `team_id`

**Cause**: Database constraint violation or manual INSERT

**Solution**: Fix by deleting duplicates, keeping row with lowest `team_key`:
```sql
DELETE FROM dim_team
WHERE team_key NOT IN (
    SELECT MIN(team_key)
    FROM dim_team
    GROUP BY team_id
);
```

### Migration backfill failed

**Symptom**: `espn_team_id` column exists but values are NULL

**Solution**: Re-run backfill SQL manually:
```sql
UPDATE dim_team
SET espn_team_id = SPLIT_PART(team_id, '_', 2)
WHERE team_id LIKE '%_%' AND espn_team_id IS NULL;
```

### Seed migration conflict with auto-discovered teams

**Symptom**: Concerned that seed migration will overwrite API-discovered teams

**Solution**: No action needed - merge logic preserves `team_key` (surrogate PK). Seed migration uses `ON CONFLICT (team_id) DO UPDATE` which updates only specified fields, leaving `team_key` intact.

## Future Enhancements

See [docs/stories/future-enhancements.md](../../../docs/stories/future-enhancements.md) for planned improvements:

- **Team colors automation**: Web scraping, third-party APIs, or color extraction from logos
- **Aliases generation**: LLM-based generation, web scraping, or hybrid approach
- **Conference automation**: Alternative APIs, web scraping, or schedule pattern inference

---

**Last Updated**: 2025-11-12
**Related Stories**: 2-3b (Team Sync), 2-4 (Dagster Polling)
**Migration Version**: de4a5062ce6e (ESPN ID), 7a8f23177a57 (Seed Data)
