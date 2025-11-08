# Story 2.1: Create Team and Conference Dimensional Data

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to create static dimensional data for top 20 NCAA teams and conferences,
So that games can be matched to teams and rivalry detection works.

---

## Acceptance Criteria

**Given** I need team and conference data for matching and UI display
**When** I create a JSON configuration file with dimensional data
**Then** the file includes:
- Top 20 NCAA Men's Basketball teams with: team_id, team_name, team_abbr, conference_id, primary_color, aliases
- Major conferences with: conference_id, conference_name, rivalry_factor (1.0-1.5)

**And** I create a data loading script: `backend/app/services/load_dimensional_data.py`

**And** the script reads JSON and inserts/updates rows in `teams` and `conferences` tables

**And** I run the script: `docker-compose exec backend python -m app.services.load_dimensional_data`

**And** I verify the data: 20 teams and ~10 conferences exist in database

**And** I add this script to the deployment initialization steps (run on first deploy)

---

## Prerequisites

- Story 1.3 (database schema with teams and conferences tables)

---

## Technical Notes

**Create File:** `backend/app/data/teams_conferences.json`

**Top 20 Teams:**
- Duke, UNC, Kansas, Kentucky, Gonzaga, UCLA, Villanova, Michigan State, Arizona, Purdue, Houston, Tennessee, Alabama, Arkansas, Baylor, Texas, Connecticut, Illinois, Indiana, Wisconsin

**Conferences:**
- ACC, Big Ten, Big 12, SEC, Pac-12, Big East, WCC

**Team Colors (Official Hex Codes):**
- Duke: #003087
- UNC: #7BAFD4
- Kansas: #0051BA
- Kentucky: #0033A0
- etc.

**Aliases Array Examples:**
- `["Duke", "Blue Devils", "DU"]`
- `["UNC", "North Carolina", "Tar Heels"]`

**Rivalry Factor:**
- 1.2 for strong conference rivalries (ACC, Big Ten)
- 1.0 for others

**Loading Script Pattern:**
```python
# backend/app/services/load_dimensional_data.py
import json
from sqlmodel import Session, select
from app.core.db import engine
from app.models.team import Team, Conference

def load_data():
    with open('app/data/teams_conferences.json') as f:
        data = json.load(f)

    with Session(engine) as session:
        # Upsert conferences
        for conf_data in data['conferences']:
            # INSERT ... ON CONFLICT UPDATE logic
            pass

        # Upsert teams
        for team_data in data['teams']:
            # INSERT ... ON CONFLICT UPDATE logic
            pass

        session.commit()

if __name__ == "__main__":
    load_data()
```

**Run Script:**
```bash
docker-compose exec backend python -m app.services.load_dimensional_data
```

**Add to Deployment:**
- Add to docker-compose.prod.yml startup command
- Or add to GitHub Actions deploy step

**Update Frequency:** Run once during Epic 1 deployment, then occasionally for roster updates

---

## Definition of Done

- [ ] JSON file created with 20 teams and conferences
- [ ] All team colors are official hex codes
- [ ] Aliases arrays populated for each team
- [ ] Loading script created with upsert logic
- [ ] Script executed successfully
- [ ] Database verified: 20 teams and ~10 conferences exist
- [ ] Script added to deployment initialization
- [ ] Documentation added explaining data structure
- [ ] Changes committed to git
