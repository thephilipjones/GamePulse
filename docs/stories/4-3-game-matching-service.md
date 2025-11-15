# Story 4-3: Game Matching Service

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-3
**Status:** TODO
**Estimated Effort:** 8-10 hours
**Priority:** High (Week 2 - blocks 4-4)
**Dependencies:** Epic 2 (dim_team with aliases populated)

---

## User Story

**As a** data engineer,
**I want** a fuzzy team name matching service that detects NCAA teams in social post text,
**So that** I can filter out irrelevant posts during transformation and link posts to specific games.

---

## Context

Social posts mention teams using various formats:
- Official names: "Duke Blue Devils", "North Carolina Tar Heels"
- Short names: "Duke", "UNC", "Carolina"
- Hashtags: "#GoDuke", "#GoHeels"
- Nicknames: "The Blue Devils", "The Heels"

This story implements a **fuzzy string matching service** using RapidFuzz library to:
1. Match post text against `dim_team.aliases` column (TEXT[] of known variations)
2. Calculate confidence scores (0-1) based on match quality
3. Filter out irrelevant posts (confidence < 0.6 threshold)
4. Optionally resolve matched teams to specific `game_key` via date + team lookup

This service is used by Story 4-4 (transform layer) to decide which raw posts to promote to `stg_social_posts`.

---

## Acceptance Criteria

### 1. GameMatcher Class - Team Detection

✅ **GIVEN** a GameMatcher instance with loaded teams cache
**WHEN** I call `match_post_to_teams("Duke vs UNC tonight!")`
**THEN** it returns:
```python
{
    "matched_teams": ["duke", "unc"],
    "match_confidence": 0.95,
    "is_game_related": True,
    "match_details": {
        "duke": {"alias_matched": "duke", "score": 95},
        "unc": {"alias_matched": "unc", "score": 95}
    }
}
```

**AND** confidence >= 0.6 sets `is_game_related = True`

### 2. Team Aliases Loading

✅ **GIVEN** `dim_team` table has teams with aliases
**WHEN** GameMatcher initializes
**THEN** it loads all NCAA basketball teams (`sport='ncaam'`, `is_current=True`) into memory cache
**AND** cache includes team names + all aliases from TEXT[] column
**AND** logs `game_matcher_teams_loaded` with teams_count

### 3. Fuzzy Matching Algorithm

✅ **GIVEN** a social post with text "Go Blue Devils! #MarchMadness"
**WHEN** fuzzy matching runs
**THEN** it uses `rapidfuzz.fuzz.partial_ratio` scorer (allows substring matches)
**AND** matches against lowercase aliases
**AND** returns top 5 matches with scores >= 60 (out of 100)
**AND** deduplicates multiple aliases for same team

### 4. Confidence Scoring

✅ **GIVEN** multiple team matches with scores [95, 90, 50]
**WHEN** overall confidence is calculated
**THEN** it averages the top 2 scores: `(95 + 90) / 2 / 100 = 0.925`
**AND** normalizes to 0-1 scale
**AND** filters matches below 60/100 threshold

### 5. Game Key Resolution (Optional)

✅ **GIVEN** matched teams `["duke", "unc"]` and post date `2025-11-15`
**WHEN** I call `resolve_game_key(team_ids, post_date)`
**THEN** it queries `fact_game` for:
- **2 teams:** Head-to-head game on that date
- **1 team:** Any game (home or away) for that team
- **0 or 3+ teams:** Returns None (ambiguous)

**AND** returns `game_key` if unique match found, else None

### 6. Irrelevant Post Filtering

✅ **GIVEN** a post "Just had pizza for dinner. Great day!"
**WHEN** matched
**THEN** `matched_teams = []`, `match_confidence = 0.0`, `is_game_related = False`

**AND** transform layer (Story 4-4) skips this post (not inserted into `stg_social_posts`)

---

## Technical Tasks

### Task 1: GameMatcher Service Implementation

**File:** `backend/app/services/game_matcher.py` (new file)

**Implementation:** See Epic 4 spec, section "Game Matching Algorithm"

**Key Features:**
- `GameMatcher` class with `__init__(session: Session)`
- `_load_teams_cache()` - Load dim_team into memory
- `match_post_to_teams(post_text: str)` - Fuzzy match
- `resolve_game_key(team_ids, post_date)` - FK resolution

**Dependencies:**
```toml
# backend/pyproject.toml
[project]
dependencies = [
    "rapidfuzz>=3.0.0",  # Fast fuzzy string matching
    # ... existing dependencies
]
```

**Installation:**
```bash
cd backend
uv add rapidfuzz
uv sync
```

---

### Task 2: Team Aliases Population

**Prerequisite:** `dim_team.aliases` column must contain team name variations.

**Migration (if not exists):**

**File:** `backend/app/alembic/versions/{timestamp}_add_team_aliases.py`

```python
def upgrade() -> None:
    # Add aliases column to dim_team
    op.execute("""
        ALTER TABLE dim_team
        ADD COLUMN IF NOT EXISTS aliases TEXT[];
    """)

    # Populate with common variations
    op.execute("""
        UPDATE dim_team
        SET aliases = ARRAY[
            team_name,                          -- Official name
            SPLIT_PART(team_name, ' ', 1),      -- First word (e.g., "Duke")
            LOWER(team_name),                   -- Lowercase
            UPPER(SPLIT_PART(team_name, ' ', 1)) -- Uppercase abbreviation
        ]
        WHERE sport = 'ncaam' AND aliases IS NULL;
    """)

def downgrade() -> None:
    op.execute("ALTER TABLE dim_team DROP COLUMN IF EXISTS aliases;")
```

**Manual Alias Updates (Production):**

For better matching, manually add team-specific aliases to seed data:

**File:** `backend/app/data/teams.json`

```json
{
  "team_id": "duke",
  "team_name": "Duke Blue Devils",
  "aliases": ["duke", "Duke", "Blue Devils", "The Blue Devils", "GoDuke", "#GoDuke"],
  ...
}
```

Reload seed data via migration `7a8f23177a57_seed_dimensional_data.py` (idempotent upsert).

---

### Task 3: Unit Tests - Game Matcher

**File:** `backend/app/tests/services/test_game_matcher.py`

**Test Fixtures:**
```python
SAMPLE_POSTS = [
    {
        "text": "Duke vs UNC tonight! Cameron Indoor is going to be electric!",
        "expected_teams": ["duke", "unc"],
        "expected_confidence": 0.90,
        "expected_is_game_related": True,
    },
    {
        "text": "Go Blue Devils! Ready for tip-off at 7pm #MarchMadness",
        "expected_teams": ["duke"],
        "expected_confidence": 0.85,
        "expected_is_game_related": True,
    },
    {
        "text": "Just had pizza for dinner. Great day!",
        "expected_teams": [],
        "expected_confidence": 0.0,
        "expected_is_game_related": False,
    },
    {
        "text": "Duke Energy stock is up 5% today!",  # False positive risk
        "expected_teams": [],  # Should NOT match "Duke" basketball
        "expected_confidence": 0.0,
        "expected_is_game_related": False,
    },
]
```

**Test Cases:**
1. `test_match_two_teams_high_confidence()` - Verify Duke vs UNC detected
2. `test_match_single_team()` - Verify single team detection
3. `test_irrelevant_post_filtered()` - Verify pizza post returns empty
4. `test_false_positive_duke_energy()` - Verify non-sports "Duke" filtered
5. `test_resolve_game_key_head_to_head()` - Verify 2 teams → game_key
6. `test_resolve_game_key_single_team()` - Verify 1 team → game_key
7. `test_resolve_game_key_ambiguous()` - Verify 3+ teams → None

**Priority:** High (Week 2) - Critical for verifying match quality

---

### Task 4: Integration with dim_team

**Verification Query:**
```sql
-- Check team aliases are populated
SELECT team_id, team_name, aliases
FROM dim_team
WHERE sport = 'ncaam'
LIMIT 10;

-- Expected output:
-- team_id | team_name          | aliases
-- --------|--------------------|-----------------------------------------
-- duke    | Duke Blue Devils   | {duke,Duke,Blue Devils,GoDuke,#GoDuke}
-- unc     | UNC Tar Heels      | {unc,UNC,Tar Heels,Carolina,GoHeels}
```

If aliases are NULL, run seed migration or manual UPDATE.

---

## Testing Requirements

### Unit Tests (High Priority)

**File:** `backend/app/tests/services/test_game_matcher.py`

- ✅ Test all sample posts in fixtures
- ✅ Test confidence scoring (average of top 2)
- ✅ Test game_key resolution (head-to-head, single team, ambiguous)
- ✅ Test false positive filtering (Duke Energy example)

### Integration Tests (Medium Priority)

**File:** `backend/app/tests/integration/test_game_matcher_with_db.py`

- ✅ Load real dim_team data from test database
- ✅ Test matching against actual team aliases
- ✅ Test resolve_game_key with real fact_game data

### Manual Testing Checklist

- [ ] Populate dim_team.aliases with sample teams
- [ ] Initialize GameMatcher, verify teams_cache loaded
- [ ] Test `match_post_to_teams()` with various post formats
- [ ] Verify confidence scores are reasonable (0.6-1.0 for game posts)
- [ ] Test edge cases: empty text, very long text, emojis, special chars
- [ ] Measure performance: 1000 matches in <1 second

---

## Dependencies

### Upstream (Must Complete First)
- Epic 2: dim_team table with team_id, team_name ✅ Complete
- dim_team.aliases column populated (migration + seed data)

### Downstream (Blocks These Stories)
- Story 4-4: Unified Transform Layer (uses GameMatcher to filter posts)
- Story 4-5: Sentiment Analysis (uses resolve_game_key to link to games)

---

## Out of Scope

- ❌ Player name matching (e.g., "Zion Williamson") - teams only
- ❌ Conference matching (e.g., "ACC", "Big Ten") - teams only
- ❌ ML-based entity recognition (e.g., spaCy NER) - rule-based fuzzy matching sufficient
- ❌ Real-time match quality feedback loop - static aliases

---

## Definition of Done

- [x] GameMatcher service implemented with fuzzy matching
- [x] Teams cache loads from dim_team on initialization
- [x] match_post_to_teams() returns confidence score and is_game_related flag
- [x] resolve_game_key() handles 2-team, 1-team, and ambiguous cases
- [x] Unit tests achieve >80% coverage on match logic
- [x] False positive rate <5% on test fixtures (Duke Energy example passes)
- [x] Performance: 1000 matches in <1 second
- [x] Code reviewed and merged to main branch

---

## Notes

### Why RapidFuzz over FuzzyWuzzy?

- **Performance:** RapidFuzz is 4-10x faster (C++ implementation)
- **Maintained:** Active development, Python 3.12 compatible
- **API Compatible:** Drop-in replacement for FuzzyWuzzy

### Confidence Threshold Tuning

Initial threshold: **0.6** (60/100 match score)

If false positive rate is high:
- Increase to 0.7 (more strict, fewer irrelevant posts)
- Add context-aware filtering (require sports keywords: "game", "score", "win")

If false negative rate is high:
- Decrease to 0.5 (more lenient, capture more posts)
- Expand team aliases with more variations

Monitor in Story 4-6 (observability metrics).

### Game Key Resolution Edge Cases

**Scenario:** Post mentions "Duke" on a day Duke plays 2 games (doubleheader)?
- `resolve_game_key()` returns **first match** (arbitrary)
- **Mitigation:** Epic 5 excitement scoring aggregates all posts for a game_key, so minor linking errors average out

**Scenario:** Post created day before game?
- Match logic infers `matched_game_date` from post context (e.g., "tomorrow")
- **Current implementation:** Uses `post.created_at.date()` (simple heuristic)
- **Future enhancement:** NLP date extraction ("tomorrow", "Saturday", "11/15")

---

**Story Created:** 2025-11-15
**Story Owner:** Developer
**Estimated Completion:** End of Week 2 (Epic 4 sprint)
