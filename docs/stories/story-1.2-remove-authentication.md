# Story 1.2: Remove Authentication Boilerplate

**Epic:** Epic 1 - Project Foundation & Infrastructure
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to remove the authentication system from the FastAPI template,
So that the application is a public read-only dashboard without login complexity.

---

## Acceptance Criteria

**Given** the FastAPI template includes JWT authentication, user models, and login endpoints
**When** I remove authentication-related code
**Then** the following are deleted or disabled:
- `backend/app/models/user.py` (User model)
- `backend/app/api/routes/login.py` (JWT token endpoints)
- `backend/app/api/routes/users.py` (user CRUD endpoints)
- `backend/app/core/security.py` (password hashing, JWT functions)
- Frontend login pages and authentication context

**And** I remove authentication dependencies from API routes (no `current_user` dependencies)

**And** I update the main FastAPI router to remove login/user endpoints

**And** the application starts without authentication errors

**And** API endpoints are publicly accessible without tokens

---

## Prerequisites

- Story 1.1 (template initialized)
- Story 1.1b (AWS infrastructure provisioned - optional, can be done in parallel)

---

## Technical Notes

**Backend Files to Remove:**
- `app/models/user.py`
- `app/api/routes/login.py`
- `app/api/routes/users.py`
- `app/core/security.py`

**Edit app/api/main.py:**
```python
# Remove these router includes:
# from app.api.routes import login, users

# Keep only:
from app.api.routes import games, health
```

**Remove Dependencies from pyproject.toml:**
```toml
# Remove:
passlib = "^1.7.4"
python-jose = "^3.3.0"
bcrypt = "^4.0.1"
```

**Frontend Files to Remove:**
- `src/pages/Login.tsx`
- `src/contexts/AuthContext.tsx`
- Any authentication-related components

**Update src/App.tsx:**
```typescript
// Remove authentication routes
// Remove AuthProvider wrapper
// Set Dashboard as default route
```

**Document Decision:**
Create ADR (Architecture Decision Record):
- File: `docs/adrs/adr-001-no-authentication.md`
- Rationale: MVP is public read-only dashboard per NFR-2.3
- Can add authentication in Growth phase if needed

**Time Saved:** ~2 hours vs maintaining unused auth code

---

## Definition of Done

- [ ] All authentication files removed from backend
- [ ] All authentication files removed from frontend
- [ ] Router configurations updated
- [ ] Dependencies removed from pyproject.toml and package.json
- [ ] Application starts without errors
- [ ] API endpoints accessible without tokens
- [ ] Frontend loads without authentication checks
- [ ] ADR documented explaining decision
- [ ] Tests updated (remove auth-related tests)
- [ ] Changes committed to git
