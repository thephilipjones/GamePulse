# GamePulse Development Backlog

This file tracks technical debt, bugs, and enhancements identified during code reviews and development.

## Format

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
|------|-------|------|------|----------|-------|--------|-------|

## Active Items

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
|------|-------|------|------|----------|-------|--------|-------|
| 2025-11-12 | 2.3b | 2 | Bug | HIGH | TBD | Open | Fix migration `d115685a3652` - Add DEFAULT constraints for team_key, created_at, updated_at [file: backend/app/alembic/versions/d115685a3652_refactor_to_dimensional_model_with_.py:53] |
| 2025-11-12 | 2.3b | 2 | Test | HIGH | TBD | Open | Verify tests pass after migration fix - Run full test suite and verify 13/13 passing (AC1-AC5) [file: backend/app/tests/services/test_team_sync.py] |
| 2025-11-12 | 2.3b | 2 | TechDebt | MEDIUM | TBD | Open | Remove unused type: ignore comment (mypy cleanup) [file: backend/app/services/team_sync.py:136] |
| 2025-11-12 | 2.3b | 2 | Enhancement | LOW | TBD | Open | Add migration test - Verify DEFAULT constraints exist after upgrade [file: backend/app/tests/migrations/] |
| 2025-11-12 | 2.3b | 2 | Test | LOW | TBD | Open | Add test for AC4 WARNING logging - Verify WARNING emitted [file: backend/app/tests/services/test_team_sync.py] |
| 2025-11-12 | 2.3b | 2 | Test | LOW | TBD | Open | Manual testing with live NCAA API - Document results [file: docs/stories/2-3b-sync-team-metadata.md] |

## Resolved Items

(None yet)

## Notes

- Items are added during code reviews and retrospectives
- HIGH severity items block story completion
- MEDIUM severity items should be addressed before next epic
- LOW severity items are nice-to-have improvements
