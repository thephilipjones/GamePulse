# Story 3.6: Increase Refresh Cadence to 1 Minute

Status: ready-for-dev

## Story

As a user watching a live game,
I want scores and game status to update within 1-2 minutes,
so that the dashboard feels like a real sports app instead of a delayed summary.

## Acceptance Criteria

### AC-3.34: Backend Polling Cadence

**Given** the Dagster ncaa_games_schedule is configured
**When** the schedule definition is updated
**Then** the schedule:
- Uses cron expression `"* * * * *"` (every 1 minute, was `"*/15 * * * *"`)
- Executes successfully every minute without skipped runs
- Shows no 429 (rate limit) errors in logs after 24 hours of operation
- Dagster UI displays runs every minute in the Runs tab

**Validation:**
```python
# backend/app/dagster_definitions.py
ncaa_games_schedule = ScheduleDefinition(
    name="ncaa_games_schedule",
    cron_schedule="* * * * *",  # Every 1 minute (was "*/15 * * * *")
    target=ncaa_games,
    execution_timezone="US/Eastern",
)
```

**Manual Verification:**
1. Open Dagster UI: http://localhost:3000 (dev) or https://dagster.gamepulse.top (prod)
2. Navigate to Schedules tab, verify `ncaa_games_schedule` shows status "Running"
3. Navigate to Runs tab, observe runs appearing every minute
4. Check run duration: Should remain ~2-3 seconds per execution
5. Monitor for 10 minutes: Expect 10 successful runs

---

### AC-3.35: Frontend Polling Alignment

**Given** the useGames hook is configured in Story 3.5
**When** the React Query polling interval is updated
**Then** the hook:
- Sets `refetchInterval: 60000` (60 seconds, was 900000)
- Sets `staleTime: 60000` to match refetch interval
- Retains `refetchIntervalInBackground: true` from Story 3.5
- Network tab shows new API request approximately every 60 seconds
- "Last updated" timestamp never exceeds 2 minutes between refreshes

**Validation:**
```typescript
// frontend/src/hooks/useGames.ts
export function useGames() {
  return useQuery<GameListResponse>({
    queryKey: ["games", "today"],
    queryFn: async () => {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/games/today`);
      if (!response.ok) {
        throw new Error("Failed to fetch games");
      }
      return response.json();
    },
    refetchInterval: 60000,  // 1 minute (was 900000 = 15 minutes)
    staleTime: 60000,        // 1 minute (was 900000)
    refetchIntervalInBackground: true,  // Continue polling when tab hidden
  });
}
```

**Manual Verification:**
1. Open dashboard: http://localhost:5173 (dev) or https://gamepulse.top (prod)
2. Open browser DevTools → Network tab → Filter by "games"
3. Wait 5 minutes, observe approximately 5 API requests
4. Verify "Last updated" timestamp updates within 1-2 minutes
5. Switch to different browser tab, return after 5 minutes → verify polling continued

---

### AC-3.36: Timestamp Display Precision

**Given** the Dashboard displays "Last updated X ago" timestamp (Story 3.5)
**When** the polling frequency increases to 1 minute
**Then** the timestamp display:
- Shows second-level precision for recency: "45 seconds ago" (not "less than a minute ago")
- Updates every 30 seconds via existing useEffect timer (implemented in Story 3.5)
- Provides clear feedback on data freshness
- Helps users understand 1-minute polling behavior

**Note:** Story 3.5 already implements live-updating timestamp with `formatDistanceToNow` from date-fns. This AC is validation-only - no code changes required unless precision needs adjustment.

**Validation:**
```typescript
// frontend/src/routes/_layout/index.tsx (existing from Story 3.5)
{data && (
  <Text fontSize="sm" color="gray.500" mb={4} textAlign="center">
    Last updated {formatDistanceToNow(new Date(data.generated_at), { addSuffix: true })}
  </Text>
)}
```

**Manual Verification:**
1. Open dashboard, note initial "Last updated" timestamp
2. Wait 30 seconds, verify timestamp updates to show "30 seconds ago" or "1 minute ago"
3. Verify precision matches user expectation for 1-minute polling cadence

---

### AC-3.37: Monitoring and Validation

**Given** the system is deployed with 1-minute polling
**When** monitoring the application for 24 hours
**Then** validation checks confirm:
- **Backend Performance**: Dagster runs complete in <5 seconds (typical: 2-3 seconds)
- **API Rate Limits**: No 429 errors from NCAA API (1 req/min well below 5 req/sec limit)
- **EC2 Resource Usage**: CPU usage remains <15% sustained (was <10% with 15-min polling)
- **Database Performance**: Upsert operations complete without blocking
- **Frontend Network**: 1 request/minute = 1,440 requests/day (21.6 MB/day data transfer)

**Monitoring Commands:**
```bash
# Check Dagster run status (EC2 or local)
docker compose logs -f dagster-daemon | grep -i "ncaa_games"

# Monitor EC2 CPU usage
top -bn1 | grep -E "Cpu|dagster"

# Check for rate limit errors
docker compose logs dagster-daemon | grep -i "429\|rate limit"

# Verify database performance
docker compose exec db psql -U postgres -d app -c "
  SELECT
    COUNT(*) as total_games,
    MAX(updated_at) as last_update
  FROM fact_game
  WHERE game_date_key = $(date +%Y%m%d)
"
```

**CloudWatch Metrics (Optional - Epic 9):**
- Backend API latency (P50, P95, P99)
- Dagster asset materialization success rate
- EC2 instance CPU and memory utilization

---

### AC-3.38: Error Handling Continuity

**Given** Story 3.5 implemented comprehensive error handling
**When** the polling frequency increases to 1 minute
**Then** error handling behavior:
- React Query retry logic continues working (3 attempts with exponential backoff)
- If API fails, cached data remains visible with warning banner
- Error state shows: "Unable to fetch latest data. Showing cached results."
- No regression in error handling behavior from Story 3.5
- Background refetch indicator still works (`isFetching` vs `isLoading` states)

**Validation:**
- All error handling from Story 3.5 remains functional
- No code changes required (configuration-only update)

**Manual Testing:**
1. Open dashboard with backend running
2. Stop backend: `docker compose stop backend`
3. Wait 60+ seconds for refetch interval to trigger
4. Verify: Cached games remain visible with warning banner
5. Restart backend: `docker compose start backend`
6. Verify: Warning clears on next successful refetch (within 1-2 minutes)

---

## Tasks / Subtasks

- [ ] **Task 1: Update Dagster Schedule to 1-Minute Polling** (AC: 3.34)
  - [ ] Open `backend/app/dagster_definitions.py`
  - [ ] Locate `ncaa_games_schedule` definition
  - [ ] Change `cron_schedule` from `"*/15 * * * *"` to `"* * * * *"`
  - [ ] Add comment explaining change: `# Every 1 minute - real-time feel for live sports`
  - [ ] Verify syntax: Dagster supports standard cron expressions
  - [ ] Save file

- [ ] **Task 2: Update Frontend Polling Interval** (AC: 3.35)
  - [ ] Open `frontend/src/hooks/useGames.ts`
  - [ ] Update `refetchInterval: 900000` to `refetchInterval: 60000`
  - [ ] Update `staleTime: 900000` to `staleTime: 60000`
  - [ ] Verify `refetchIntervalInBackground: true` is present (from Story 3.5)
  - [ ] Add/update JSDoc comment explaining 1-minute polling interval
  - [ ] Save file
  - [ ] Run TypeScript compiler: `npx tsc --noEmit`
  - [ ] Verify no type errors introduced

- [ ] **Task 3: Local Testing and Validation** (AC: 3.34, 3.35, 3.37)
  - [ ] **Backend Testing**:
    - [ ] Restart Dagster services: `docker compose restart dagster-daemon dagster-webserver`
    - [ ] Open Dagster UI: http://localhost:3000
    - [ ] Navigate to Schedules tab, verify `ncaa_games_schedule` is "Running"
    - [ ] Wait 3 minutes, navigate to Runs tab, verify 3 new runs appeared
    - [ ] Check run logs: `docker compose logs -f dagster-daemon | grep ncaa_games`
    - [ ] Verify no errors, runs complete in 2-5 seconds
  - [ ] **Frontend Testing**:
    - [ ] Rebuild frontend container: `docker compose build frontend`
    - [ ] Restart frontend: `docker compose restart frontend`
    - [ ] Open dashboard: http://localhost:5173
    - [ ] Open DevTools → Network tab, filter by "games"
    - [ ] Wait 5 minutes, count API requests (expect ~5 requests)
    - [ ] Verify "Last updated" timestamp updates within 1-2 minutes
  - [ ] **Error Handling Test** (AC: 3.38):
    - [ ] Stop backend: `docker compose stop backend`
    - [ ] Wait 60+ seconds for refetch to trigger
    - [ ] Verify: Cached games visible with warning banner
    - [ ] Restart backend: `docker compose start backend`
    - [ ] Verify: Warning clears on next refetch

- [ ] **Task 4: Code Quality and Linting** (AC: All)
  - [ ] **Backend**:
    - [ ] Run Ruff linter: `cd backend && uv run ruff check .`
    - [ ] Fix any linting issues: `uv run ruff check . --fix`
    - [ ] Run Mypy type checker: `uv run mypy .`
    - [ ] Fix any type errors
  - [ ] **Frontend**:
    - [ ] Run Biome linter: `cd frontend && npm run lint`
    - [ ] Fix any auto-fixable issues (Biome handles automatically)
    - [ ] Verify TypeScript compilation: `npx tsc --noEmit`
  - [ ] Run pre-commit hooks: `cd backend && uv run pre-commit run --all-files`

- [ ] **Task 5: Deployment and Production Validation** (AC: 3.37)
  - [ ] Commit changes to git:
    ```bash
    git add backend/app/dagster_definitions.py frontend/src/hooks/useGames.ts
    git commit -m "feat: increase polling cadence to 1-minute for real-time feel

Story 3.6: Update Dagster schedule and React Query polling to 1-minute intervals
- Backend: Dagster cron schedule now runs every minute
- Frontend: React Query refetchInterval reduced from 15 minutes to 60 seconds
- Improves UX for live sports by reducing data staleness from 15 min to 1-2 min
- API rate limit impact: 1 req/min well below 5 req/sec NCAA API limit

🤖 Generated with Claude Code (https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
    ```
  - [ ] Push to main: `git push origin main`
  - [ ] Wait for GitHub Actions deployment to complete
  - [ ] Verify deployment success in Actions tab
  - [ ] Open production dashboard: https://gamepulse.top
  - [ ] Monitor production for 24 hours:
    - [ ] Check Dagster UI: https://dagster.gamepulse.top
    - [ ] Verify runs every minute with no failures
    - [ ] SSH to EC2: `terraform output -raw ssh_command`
    - [ ] Check CPU usage: `top -bn1 | head -15` (expect <15%)
    - [ ] Check for rate limit errors: `docker compose logs dagster-daemon | grep -i "429"`

- [ ] **Task 6: Gradual Rollout Testing (Optional - Recommended)** (AC: 3.37)
  - [ ] **Option A: Direct 1-Minute Deployment** (current plan)
    - [ ] Deploy straight to 1-minute polling
    - [ ] Monitor closely for first 24 hours
    - [ ] Rollback plan: Revert cron to `"*/5 * * * *"` if issues arise
  - [ ] **Option B: Staged Rollout** (lower risk, more conservative)
    - [ ] Step 1: Deploy 5-minute polling (`"*/5 * * * *"`)
    - [ ] Monitor for 24-48 hours, verify no API throttling
    - [ ] Step 2: Deploy 1-minute polling if Step 1 successful
    - [ ] Provides intermediate fallback option

- [ ] **Task 7: Documentation and Retrospective** (AC: All)
  - [ ] Update story status in sprint-status.yaml: backlog → drafted → ready-for-dev → in-progress → review → done
  - [ ] Document any issues encountered in Dev Agent Record → Debug Log References
  - [ ] Update Dev Agent Record → Completion Notes List with actual results:
    - API rate limit status (any 429 errors?)
    - CPU usage before/after (percentage comparison)
    - User feedback on "real-time feel" (if available)
  - [ ] Add file list: Modified files only (no new files expected)
  - [ ] Consider adding note to Epic 3 retrospective about performance impact

---

## Dev Notes

### Architecture Patterns from Epic 3 Tech Spec

**Polling Architecture (from Tech Spec [APIs and Interfaces](../tech-spec-epic-3.md#apis-and-interfaces)):**

Story 3.5 established the auto-refresh mechanism with 15-minute polling as a conservative starting point matching the Dagster ingestion cadence. This story optimizes the system for live sports UX by reducing both backend data collection and frontend display refresh to 1-minute intervals.

**Design Rationale:**
- **15-minute polling** (Story 3.5): Matched NFR-1.4 requirement (<15 min data staleness acceptable)
- **1-minute polling** (Story 3.6): Improves UX for live sports where score changes every 30-60 seconds
- **Alignment requirement**: Frontend polling should match or exceed backend ingestion frequency

**Backend Ingestion (Dagster):**
```python
# backend/app/dagster_definitions.py
ncaa_games_schedule = ScheduleDefinition(
    name="ncaa_games_schedule",
    cron_schedule="* * * * *",  # Every 1 minute
    target=ncaa_games,
    execution_timezone="US/Eastern",
)
```

**Frontend Polling (React Query):**
```typescript
// frontend/src/hooks/useGames.ts
export function useGames() {
  return useQuery<GameListResponse>({
    queryKey: ["games", "today"],
    queryFn: async () => { /* fetch logic */ },
    refetchInterval: 60000,  // 1 minute = 60,000 ms
    staleTime: 60000,        // Match refetch interval
    refetchIntervalInBackground: true,  // Story 3.5 fix
  });
}
```

**Why Both Must Change:**
- If only backend changes: Frontend still polls every 15 min → data appears stale for 14 minutes
- If only frontend changes: Frontend polls every 1 min but backend updates every 15 min → wasted requests, no new data
- **Aligned approach**: Both at 1-minute → optimal user experience with minimal waste

### API Rate Limit Analysis

**NCAA API (henrygd/ncaa-api wrapper) Constraints:**

From [Story 2.2](../stories/story-2.2-build-ncaa-client.md) and Epic 3 spec:
- **Documented burst limit**: 5 requests/second (enforced with 200ms client-side delay)
- **Undocumented rate limits**: No QPM (queries per minute) or QPD (queries per day) limits found
- **Self-hosted wrapper**: No centralized rate limiting, per-client throttling only

**Current Usage (15-minute polling - Story 3.5):**
- Frequency: 1 request every 15 minutes = 96 requests/day
- Sustained rate: 0.0011 requests/second
- Daily data transfer: ~1.4 MB (96 × 15 KB avg response size)

**Proposed Usage (1-minute polling - Story 3.6):**
- Frequency: 1 request every 1 minute = 1,440 requests/day
- Sustained rate: 0.0167 requests/second (still 300x below 5 req/sec burst limit)
- Daily data transfer: ~21.6 MB (1,440 × 15 KB avg response size)
- **Increase**: 15x more frequent requests

**Risk Assessment**: **LOW**
- 1-minute polling is 300x slower than the documented 5 req/sec burst limit
- No evidence of QPM or QPD limits in NCAA API documentation
- henrygd/ncaa-api wrapper is self-hosted (no shared quota with other users)
- Mitigation: Existing retry logic (Story 2.5) handles 429 errors gracefully

**Monitoring Strategy:**
1. Watch Dagster logs for 429 (rate limit) HTTP status codes
2. If 429 errors appear: Rollback to 5-minute polling (`"*/5 * * * *"`)
3. EC2 CloudWatch logs capture all API requests for audit

### Performance Impact Analysis

**Backend (Dagster):**

**Current Performance (15-minute polling):**
- Run frequency: 96 executions/day
- Avg execution time: 2-3 seconds per run
- Daily execution time: ~4.8 minutes total

**Proposed Performance (1-minute polling):**
- Run frequency: 1,440 executions/day
- Avg execution time: 2-3 seconds per run (unchanged)
- Daily execution time: ~72 minutes total (5% of day)
- **CPU impact**: Minimal - Dagster in-process executor with async I/O
- **Database impact**: ~60 upserts/hour (negligible for PostgreSQL)

**Why Low Impact:**
- Dagster asset execution is async I/O bound (HTTP fetch + DB upsert)
- No heavy computation (simple data transformation)
- SQLModel upserts use efficient ON CONFLICT DO UPDATE
- t2.micro single vCPU handles async workloads well

**Frontend:**

**Network Overhead:**
- Polling frequency: 1 request/minute = 0.0167 req/sec
- Response size: ~15 KB JSON (20-50 games typical)
- Daily bandwidth: 21.6 MB (well within AWS free tier: 15 GB/month outbound)

**Battery Efficiency:**
- Story 3.5 implemented `refetchIntervalInBackground: true`
- Polling continues even when tab is hidden (user preference for data freshness)
- 1-minute interval: Low wake frequency (acceptable for sports apps)
- Alternative: Could add visibility API to pause when tab hidden (future optimization)

**EC2 Instance (t2.micro):**

**Resource Constraints:**
- CPU: 1 vCPU shared (burstable with CPU credits)
- RAM: 1 GB (swap configured in Story 1.1b)
- Disk: 30 GB GP3 SSD

**Expected CPU Usage:**
- Current (15-min): ~5% sustained CPU (from CloudWatch)
- Proposed (1-min): ~10-15% sustained CPU (estimated)
- **Risk**: LOW - t2.micro CPU credits accumulate when idle, burst during activity

**Monitoring Commands:**
```bash
# Check current CPU usage (SSH to EC2)
top -bn1 | head -15

# Monitor CPU over 5 minutes
top -d 60 -n 5 -b | grep "Cpu(s)"

# Check swap usage (should be low)
free -h
```

### Rollback Plan

If performance or rate limiting issues occur:

**Immediate Rollback (5-minute compromise):**
```python
# backend/app/dagster_definitions.py
ncaa_games_schedule = ScheduleDefinition(
    name="ncaa_games_schedule",
    cron_schedule="*/5 * * * *",  # Every 5 minutes (compromise)
    # ...
)
```

```typescript
// frontend/src/hooks/useGames.ts
export function useGames() {
  return useQuery<GameListResponse>({
    queryKey: ["games", "today"],
    queryFn: async () => { /* ... */ },
    refetchInterval: 300000,  // 5 minutes
    staleTime: 300000,
    // ...
  });
}
```

**Revert to 15-Minute (Original):**
- Revert commits and redeploy
- No schema changes required (configuration only)

**No Data Loss:**
- Rollback only affects refresh frequency
- Historical data in `fact_game` table unaffected
- User experience degrades gracefully (slower updates)

### Gradual Rollout Strategy (Optional)

Epic 3 Story 6 specification recommends gradual rollout for risk mitigation:

**Phase 1: 5-Minute Polling (24-48 hours)**
- Deploy: `cron_schedule="*/5 * * * *"` + `refetchInterval: 300000`
- Monitor: Dagster logs, EC2 CPU, API errors
- Success criteria: No 429 errors, CPU <10%, no failed runs

**Phase 2: 1-Minute Polling (if Phase 1 successful)**
- Deploy: `cron_schedule="* * * * *"` + `refetchInterval: 60000`
- Monitor: Same metrics for 24-48 hours
- Fallback: Revert to 5-minute if issues arise

**Recommended Approach:** Direct 1-minute deployment with close monitoring
- **Why**: 1-minute is well within API limits, minimal CPU impact expected
- **Mitigation**: 24-hour monitoring period with rollback plan ready

### Project Structure Alignment

**Story 3.6 File Changes (Configuration Only):**

```
backend/
├── app/
│   └── dagster_definitions.py    # MODIFIED - Update cron_schedule

frontend/
└── src/
    └── hooks/
        └── useGames.ts            # MODIFIED - Update refetchInterval and staleTime
```

**No New Files Created** - Story 3.6 is pure configuration optimization.

**No Schema Changes** - Database tables unchanged (fact_game, dim_team, dim_date).

### Learnings from Previous Story (3-5-add-auto-refresh)

**From Story 3-5-add-auto-refresh (Status: done)**

Key services and patterns to REUSE:

- ✅ **useGames Hook Ready**: Already supports variable `refetchInterval` (Story 3.5)
  - **Action for this story**: Simply change `refetchInterval: 900000` to `60000`
  - `refetchIntervalInBackground: true` already configured (fix from 3-5)
  - Hook handles all states: `isLoading`, `isFetching`, `isError`, `data`

- ✅ **Live Timestamp Display**: 30-second useEffect timer already implemented (Story 3.5)
  - **Action for this story**: No changes required - precision already adequate
  - Uses date-fns `formatDistanceToNow` with `{ addSuffix: true }`
  - Output examples: "45 seconds ago", "2 minutes ago"

- ✅ **Error Handling with Cached Data**: Graceful degradation already working (Story 3.5)
  - **Action for this story**: No changes required - configuration-only update
  - React Query retry logic: 3 attempts with exponential backoff
  - Warning banner shows cached data during failures

- ✅ **Background Refetch Indicator**: `isFetching` vs `isLoading` states (Story 3.5)
  - **Action for this story**: Verify indicator still appears during 1-minute polling
  - Small spinner + "Updating..." text shown during background refetch

**New Files Created in Story 3-5** (relevant context):
- None - Story 3-5 only modified existing components

**Modified Files in Story 3-5** (will modify again in 3-6):
- `frontend/src/hooks/useGames.ts` - Will update polling intervals
- `frontend/src/routes/_layout/index.tsx` - Timestamp display (already optimal)

**Architectural Decisions from Story 3-5**:
- React Query polling architecture proven reliable
- `refetchIntervalInBackground: true` essential for tab-hidden scenarios
- date-fns lightweight and performant for timestamp formatting
- CORS configuration working between frontend and backend

**Review Findings from Story 3-5** (advisory items):
- Unused `now` state variable in index.tsx:22 (low severity, not blocking)
- JSDoc comment needs precision update (optional improvement)
- No E2E tests for polling behavior (gap, but acceptable for MVP)

**Warnings for Story 3-6**:
- Docker rebuild required after changing frontend hook (same as 3-5)
- Monitor CPU usage closely for first 24 hours (increased polling frequency)
- Pre-existing TypeScript test errors unrelated to this story

### Testing Strategy

**Manual Testing Checklist:**

1. **Backend Polling Verification**:
   - Open Dagster UI: http://localhost:3000 or https://dagster.gamepulse.top
   - Navigate to Schedules, verify `ncaa_games_schedule` status "Running"
   - Navigate to Runs, observe runs appearing every minute
   - Check logs: `docker compose logs -f dagster-daemon | grep ncaa_games`
   - Verify: Run duration <5 seconds, no errors

2. **Frontend Polling Verification**:
   - Open dashboard: http://localhost:5173 or https://gamepulse.top
   - Open DevTools → Network tab → Filter by "games"
   - Wait 5 minutes, count API requests (expect ~5 requests)
   - Verify: Requests spaced ~60 seconds apart
   - Verify: "Last updated" timestamp updates within 1-2 minutes

3. **Error Handling Test** (Story 3.5 regression check):
   - Open dashboard with backend running
   - Stop backend: `docker compose stop backend`
   - Wait 60+ seconds for refetch interval
   - Expected: Cached games visible with warning banner
   - Restart backend: `docker compose start backend`
   - Expected: Warning clears on next successful refetch

4. **CPU Usage Monitoring** (EC2 only):
   - SSH to EC2: Use terraform output or SSM Session Manager
   - Before deployment: `top -bn1 | head -15` (baseline CPU)
   - After deployment: Monitor `top` for 10 minutes
   - Expected: CPU <15% sustained (increase from ~5% baseline)
   - If CPU >20%: Investigate Dagster or backend logs

5. **Rate Limit Monitoring** (24-hour validation):
   - Day 1: Check logs hourly: `docker compose logs dagster-daemon | grep -i "429\|rate"`
   - Day 2: Verify no 429 errors accumulated overnight
   - If 429 errors: Rollback to 5-minute polling immediately

**Performance Benchmarks:**

| Metric | Before (15-min) | After (1-min) | Threshold | Risk |
|--------|-----------------|---------------|-----------|------|
| API requests/hour | 4 | 60 | No limit known | LOW |
| Dagster run duration | 2-3 sec | 2-3 sec | <5 sec | LOW |
| EC2 CPU usage | ~5% | ~10-15% | <20% | LOW |
| Network bandwidth/day | 1.4 MB | 21.6 MB | 15 GB/month | LOW |
| Frontend battery impact | Minimal | Minimal | N/A | LOW |

### References

**Tech Spec Sections:**

- [APIs and Interfaces](../tech-spec-epic-3.md#apis-and-interfaces) - React Query polling configuration
- [Workflows and Sequencing](../tech-spec-epic-3.md#workflows-and-sequencing) - Automatic polling refresh workflow
- [Reliability/Availability](../tech-spec-epic-3.md#reliabilityavailability) - Graceful degradation with cached data

**PRD Requirements:**

- [FR-7.3](../PRD.md#fr-7-frontend-dashboard) - Frontend auto-refresh requirement
- [NFR-1.4](../PRD.md#nfr-1-performance) - Data staleness <15 minutes acceptable (Story 3.6 improves to <2 min)
- [NFR-4.2](../PRD.md#nfr-4-reliability) - Graceful degradation during outages

**Architecture Document:**

- [Frontend State](../architecture.md#decision-summary) - React Query for server state management
- [API Response Format](../architecture.md#api-response-format) - `generated_at` timestamp in responses

**Previous Stories:**

- [Story 2.2](../stories/story-2.2-build-ncaa-client.md) - NCAA API client with rate limiting (5 req/sec burst limit)
- [Story 2.4](../stories/story-2.4-implement-polling-worker.md) - Dagster ncaa_games asset (currently 15-min schedule)
- [Story 3.5](../stories/3-5-add-auto-refresh.md) - Auto-refresh polling with React Query (current 15-min implementation)

**Epic Specification:**

- [Epic 3 Story 6 Specification](../epics.md#story-36-increase-refresh-cadence-to-1-minute-real-time-feel) - Full specification including risk assessment and rollback plan

**External Documentation:**

- [TanStack Query Docs - Polling / Intervals](https://tanstack.com/query/latest/docs/framework/react/guides/window-focus-refetching)
- [Dagster Docs - Schedules](https://docs.dagster.io/concepts/partitions-schedules-sensors/schedules)
- [Cron Expression Reference](https://crontab.guru/#*_*_*_*_*) - Verify cron syntax

---

## Dev Agent Record

### Context Reference

- [Story 3.6 Context](3-6-increase-refresh-cadence.context.xml) - Generated 2025-11-14

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
