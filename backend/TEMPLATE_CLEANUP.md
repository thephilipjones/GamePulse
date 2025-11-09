# Template Cleanup Checklist

This FastAPI full-stack template includes demo functionality that should be removed before GamePulse production deployment.

## Files to Remove Before Production

### API Routes
- [ ] `backend/app/api/routes/items.py` - Demo CRUD endpoints with public write access
- [ ] `backend/app/api/routes/utils.py` - Test email endpoint (or move to internal admin)

### Models
- [ ] `backend/app/models.py` - Remove Item model classes:
  - ItemBase
  - ItemCreate
  - ItemUpdate
  - Item (table)
  - ItemPublic
  - ItemsPublic

### Database
- [ ] `backend/app/alembic/versions/001_initialize_item_model.py` - Demo migration
- [ ] Drop `item` table from production database

### Tests
- [ ] `backend/app/tests/api/routes/test_items.py` - Item endpoint tests
- [ ] `backend/app/tests/utils/item.py` - Item test utilities
- [ ] `backend/app/crud.py` - Remove `create_item` function

### CRUD
- [ ] `backend/app/crud.py` - Remove all Item-related functions

## Why Remove?

**Security**: Items endpoints have public POST/PUT/DELETE operations without authentication.
**Architecture**: GamePulse is a read-only public dashboard - no user-generated content.
**Cleanup**: Template demo code confuses new developers about application scope.

## When to Remove?

**Recommended**: During Epic 2-3 when implementing real GamePulse domain models (Game, Team, etc.)

**Alternative**: Keep for local development testing, but ensure Traefik config ONLY exposes:
- `/api/v1/games/*` (GET only)
- `/api/v1/teams/*` (GET only)
- Other read-only GamePulse endpoints

## Replacement

Replace with GamePulse domain models:
- `backend/app/models/game.py` - Game model
- `backend/app/models/team.py` - Team model
- `backend/app/models/score.py` - Excitement score model
- `backend/app/api/routes/games.py` - Read-only game endpoints
- `backend/app/api/routes/teams.py` - Read-only team endpoints

See Epic 2-3 stories for implementation details.
