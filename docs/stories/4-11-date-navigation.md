# Story 4-11: Add Date Navigation (Prev/Next Day)

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-11
**Status:** ready-for-dev
**Date Drafted:** 2025-11-20
**Date Ready:** 2025-11-20
**Estimated Effort:** 2-4 hours
**Priority:** High (Unblocks social post value)
**Dependencies:** Story 4-10 (Social Posts Feed)

---

## User Story

**As a** basketball fan,
**I want** to navigate between yesterday's and today's games using prev/next day controls,
**So that** I can view social media posts and game stories from completed games (yesterday) where the most interesting content exists.

---

## Context

### Product Discovery Insight

**Original PRD Assumption (Proven Incorrect):**
- PRD listed "Historical Browsing: Today's games only (no date picker for past days)" as acceptable MVP simplification (PRD lines 274-276)
- Assumed today's games would have sufficient social content

**Reality from Product Usage (2025-11-20):**
- ❌ **Upcoming games (today)**: No social posts exist (games haven't happened yet)
- ✅ **Completed games (yesterday)**: Lots of social posts, sentiment, fan reactions
- **Conclusion**: The most valuable content is for **yesterday's games**, not today's

### Business Justification

Story 4-10 integrated social posts feed into game cards, but users can't access this value because:
1. Default view shows today's games (scheduled, no posts yet)
2. Yesterday's games (with rich social content) are invisible
3. Product value proposition (surfacing game stories) is blocked

**This story unblocks the core user value by enabling navigation to yesterday's games.**

### Technical Good News

✅ **Backend API already supports date queries!** (No backend changes needed)

**Source:** `backend/app/api/routes/games.py:26-63`

```python
@router.get("", response_model=GameListResponse)
async def get_games(
    session: SessionDep,
    date_param: str | None = Query(
        None,
        alias="date",
        description="Date in YYYY-MM-DD format (defaults to today in UTC)",
    ),
):
    # API already implemented and working!
```

**Implementation is 100% frontend work.**

---

## Dev Notes for Developer

### Architecture Patterns and Constraints

**Frontend-Only Implementation:**
- No backend changes required (API already supports `?date=YYYY-MM-DD`)
- Use TanStack Router for URL state management
- Default to **yesterday's date** (where interesting content is)
- Preserve existing auto-refresh behavior (60-second polling)

**Navigation Design:**
```
┌────────────────────────────────────┐
│  <   November 19, 2025   >        │
└────────────────────────────────────┘
      [All game cards below...]
```

**URL Pattern:**
- Today: `http://localhost:5173/` (defaults to yesterday)
- Specific date: `http://localhost:5173/?date=2025-11-19`
- Shareable links (date persists in URL)

**Key Design Decisions:**

1. **Default to Yesterday (Not Today)**
   - Rationale: Yesterday's games have social posts, today's don't
   - User sees value immediately on page load
   - Can navigate to today if needed (but usually won't)

2. **Prev/Next Navigator (Not Date Picker)**
   - Simple arrow navigation: `< Date >`
   - Expandable to full date picker later (Epic 5+)
   - Minimal implementation time (2-4 hours)

3. **URL State Management**
   - Use TanStack Router `useSearch()` hook
   - Date persists in URL query params
   - Browser back/forward buttons work correctly
   - Shareable links include date

### Implementation Components

**New Component:**
```typescript
// frontend/src/components/DateNavigator.tsx

import { IconButton, HStack, Text } from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';

interface DateNavigatorProps {
  currentDate: string; // YYYY-MM-DD format
  onDateChange: (newDate: string) => void;
}

export function DateNavigator({ currentDate, onDateChange }: DateNavigatorProps) {
  const handlePrevDay = () => {
    const date = new Date(currentDate);
    date.setDate(date.getDate() - 1);
    onDateChange(date.toISOString().split('T')[0]);
  };

  const handleNextDay = () => {
    const date = new Date(currentDate);
    date.setDate(date.getDate() + 1);
    onDateChange(date.toISOString().split('T')[0]);
  };

  const formatDisplayDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(date);
  };

  return (
    <HStack justify="center" mb={6} gap={4}>
      <IconButton
        icon={<ChevronLeftIcon />}
        onClick={handlePrevDay}
        aria-label="Previous day"
        size="sm"
      />
      <Text fontWeight="bold" fontSize="lg">
        {formatDisplayDate(currentDate)}
      </Text>
      <IconButton
        icon={<ChevronRightIcon />}
        onClick={handleNextDay}
        aria-label="Next day"
        size="sm"
      />
    </HStack>
  );
}
```

**Updated Hook:**
```typescript
// frontend/src/hooks/useGames.ts

// BEFORE:
export function useGames() {
  return useQuery({
    queryKey: ['games', 'today'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/games`);
      return res.json();
    },
  });
}

// AFTER:
export function useGames(date?: string) {
  return useQuery({
    queryKey: ['games', date || 'today'],
    queryFn: async () => {
      const url = date
        ? `${API_BASE_URL}/api/v1/games?date=${date}`
        : `${API_BASE_URL}/api/v1/games`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch games');
      return res.json();
    },
    // Keep existing staleTime, refetchInterval settings
  });
}
```

**Updated Dashboard:**
```typescript
// frontend/src/routes/_layout/index.tsx

import { useNavigate, useSearch } from '@tanstack/react-router';
import { DateNavigator } from '../../components/DateNavigator';

// Helper: Get yesterday's date in YYYY-MM-DD format
function getYesterdayDate(): string {
  const date = new Date();
  date.setDate(date.getDate() - 1);
  return date.toISOString().split('T')[0];
}

export function Dashboard() {
  const navigate = useNavigate();
  const { date } = useSearch() as { date?: string };

  // Default to yesterday if no date param in URL
  const currentDate = date || getYesterdayDate();

  const { data, isLoading, isError } = useGames(currentDate);

  const handleDateChange = (newDate: string) => {
    navigate({ search: { date: newDate } });
  };

  return (
    <Container maxW="container.xl" py={8}>
      <Heading as="h1" size="2xl" textAlign="center" mb={8}>
        GamePulse
      </Heading>

      <DateNavigator currentDate={currentDate} onDateChange={handleDateChange} />

      <GameList data={data} isLoading={isLoading} isError={isError} />
    </Container>
  );
}
```

### Learnings from Previous Stories

**From Story 3-4 (Build Game List):**
- `useGames` hook currently has no parameters (fetches "today" by default)
- TanStack Query `queryKey` determines cache bucket (`['games', 'today']`)
- Changing date should create new query key: `['games', '2025-11-19']`
- This allows separate caching per date (efficient!)

**From Story 4-10 (Social Posts Feed):**
- Social posts linked by `game_id`, not date
- Posts will automatically load for historical games
- No changes needed to SocialPostsFeed component

**From Story 3-6 (Auto-Refresh):**
- Current polling interval: 60 seconds (1 minute)
- Polling should continue working with date parameter
- TanStack Query handles this automatically via queryKey

### Timezone Handling

**Important:** Backend returns games in UTC timezone, but user expects local date navigation.

**Approach:**
- Use user's local timezone for display: `new Intl.DateTimeFormat(...)`
- Send date to API in YYYY-MM-DD format (no timezone)
- Backend interprets date as UTC (consistent behavior)

**Edge Case:**
- User at 11:00 PM EST on Nov 19 → "Yesterday" = Nov 18 (local time)
- Backend may return different games if UTC date is Nov 20
- **Acceptable for MVP** - can refine in Epic 5 if needed

### Testing Strategy

**Component Tests:**
```typescript
// frontend/src/components/DateNavigator.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { DateNavigator } from './DateNavigator';

describe('DateNavigator', () => {
  it('should call onDateChange with previous day when prev button clicked', () => {
    const mockOnChange = vi.fn();
    render(<DateNavigator currentDate="2025-11-20" onDateChange={mockOnChange} />);

    fireEvent.click(screen.getByLabelText('Previous day'));

    expect(mockOnChange).toHaveBeenCalledWith('2025-11-19');
  });

  it('should call onDateChange with next day when next button clicked', () => {
    const mockOnChange = vi.fn();
    render(<DateNavigator currentDate="2025-11-20" onDateChange={mockOnChange} />);

    fireEvent.click(screen.getByLabelText('Next day'));

    expect(mockOnChange).toHaveBeenCalledWith('2025-11-21');
  });

  it('should format date as "Wednesday, November 20, 2025"', () => {
    render(<DateNavigator currentDate="2025-11-20" onDateChange={vi.fn()} />);

    expect(screen.getByText(/Wednesday, November 20, 2025/i)).toBeInTheDocument();
  });
});
```

**Integration Tests:**
```typescript
// frontend/src/routes/_layout/index.test.tsx

describe('Dashboard with date navigation', () => {
  it('should default to yesterday\'s date when no URL param', () => {
    // Mock useSearch to return empty object
    vi.mocked(useSearch).mockReturnValue({});

    render(<Dashboard />);

    // Should call useGames with yesterday's date
    expect(useGames).toHaveBeenCalledWith(getYesterdayDate());
  });

  it('should use date from URL query param if present', () => {
    vi.mocked(useSearch).mockReturnValue({ date: '2025-11-15' });

    render(<Dashboard />);

    expect(useGames).toHaveBeenCalledWith('2025-11-15');
  });

  it('should update URL when date changes', () => {
    const mockNavigate = vi.fn();
    vi.mocked(useNavigate).mockReturnValue(mockNavigate);

    render(<Dashboard />);

    // Click next day button
    fireEvent.click(screen.getByLabelText('Next day'));

    expect(mockNavigate).toHaveBeenCalledWith({
      search: { date: expect.stringMatching(/\d{4}-\d{2}-\d{2}/) },
    });
  });
});
```

**Manual Testing Checklist:**
- [ ] Load dashboard → Defaults to yesterday's date
- [ ] Date displayed as "Tuesday, November 19, 2025" (formatted)
- [ ] Game cards show yesterday's completed games
- [ ] Social posts visible for yesterday's games
- [ ] Click "Next day" → URL updates to today, games refresh
- [ ] Click "Prev day" → URL updates to 2 days ago, games refresh
- [ ] Manually edit URL `?date=2025-11-15` → Games load for that date
- [ ] Browser back button works (returns to previous date)
- [ ] Browser forward button works (navigates to next date)
- [ ] Auto-refresh continues every 60 seconds (TanStack Query polling)
- [ ] TanStack Query DevTools shows separate cache entries per date
- [ ] Responsive design (mobile, tablet, desktop)

### Performance Considerations

**Cache Strategy:**
- Each date gets separate TanStack Query cache entry
- Cache key: `['games', '2025-11-19']` vs `['games', '2025-11-20']`
- `staleTime: 5 * 60 * 1000` (5 minutes for historical data)
- `refetchInterval: 60 * 1000` (60 seconds for auto-refresh)

**Why 5-minute staleTime for historical dates:**
- Yesterday's games don't change (already final)
- No need to refetch every 60 seconds
- Reduce API load

**Implementation:**
```typescript
export function useGames(date?: string) {
  const isToday = !date || date === new Date().toISOString().split('T')[0];

  return useQuery({
    queryKey: ['games', date || 'today'],
    queryFn: async () => { /* ... */ },
    staleTime: isToday ? 60 * 1000 : 5 * 60 * 1000, // 1 min for today, 5 min for historical
    refetchInterval: isToday ? 60 * 1000 : undefined, // Only poll for today
  });
}
```

### Future Enhancements (Out of Scope)

**Story 4-11 focuses on simple prev/next navigation. Future improvements:**

1. **Date Picker Widget** (Epic 5)
   - Calendar UI for selecting arbitrary dates
   - Quick jump to "Last Saturday" or specific tournament dates

2. **Relative Date Display** (Epic 5)
   - Show "Yesterday" | "Today" | "Tomorrow" instead of full date
   - Better UX for recent dates

3. **Keyboard Shortcuts** (Epic 8)
   - Arrow keys (← →) to navigate days
   - "T" for today, "Y" for yesterday

4. **Date Range Views** (Epic 5)
   - "This Week" | "This Month" aggregate views
   - Multiple days displayed simultaneously

---

## Acceptance Criteria

### AC-4.11.1: DateNavigator Component
- [ ] Create `DateNavigator.tsx` component in `frontend/src/components/`
- [ ] Component accepts `currentDate` (string, YYYY-MM-DD) and `onDateChange` (callback) props
- [ ] Displays formatted date: "Wednesday, November 20, 2025" format
- [ ] Prev button (←) calls `onDateChange` with previous day's date
- [ ] Next button (→) calls `onDateChange` with next day's date
- [ ] Uses Chakra UI components (IconButton, HStack, Text)
- [ ] Accessible: aria-labels on buttons ("Previous day", "Next day")

### AC-4.11.2: Update useGames Hook
- [ ] Modify `useGames` hook to accept optional `date` parameter (string, YYYY-MM-DD)
- [ ] If `date` provided: fetch from `GET /api/v1/games?date={date}`
- [ ] If `date` omitted: fetch from `GET /api/v1/games` (defaults to today)
- [ ] Update queryKey to include date: `['games', date || 'today']`
- [ ] Different dates create separate cache entries
- [ ] Preserve existing error handling and retry logic

### AC-4.11.3: URL State Management
- [ ] Use TanStack Router `useSearch()` to read `date` query param from URL
- [ ] Use `useNavigate()` to update URL when date changes
- [ ] URL format: `http://localhost:5173/?date=2025-11-19`
- [ ] Browser back/forward buttons navigate between dates correctly
- [ ] URL shareable (copy-paste includes date)

### AC-4.11.4: Dashboard Integration
- [ ] Add `DateNavigator` component to Dashboard page (above GameList)
- [ ] Default to **yesterday's date** when no URL param present
- [ ] Pass current date to `useGames(date)` hook
- [ ] Update URL when user navigates dates
- [ ] Preserve existing layout and styling

### AC-4.11.5: Cache Optimization
- [ ] Historical dates (not today): `staleTime: 5 * 60 * 1000` (5 minutes)
- [ ] Today's date: `staleTime: 60 * 1000` (1 minute, existing behavior)
- [ ] Historical dates: No auto-refresh polling (games already final)
- [ ] Today's date: `refetchInterval: 60 * 1000` (60 seconds, existing behavior)
- [ ] Verify in TanStack Query DevTools: separate cache entries per date

### AC-4.11.6: Date Formatting
- [ ] Display format: "Wednesday, November 20, 2025" (long weekday, month, day, year)
- [ ] Use `Intl.DateTimeFormat('en-US', { ... })` for locale-aware formatting
- [ ] API format: "2025-11-20" (YYYY-MM-DD, ISO 8601)
- [ ] Internal Date objects: UTC timezone (consistent with backend)

### AC-4.11.7: Component Tests
- [ ] Test: Prev button decrements date by 1 day
- [ ] Test: Next button increments date by 1 day
- [ ] Test: Date formatted correctly (long format)
- [ ] Test: `onDateChange` callback called with correct date string
- [ ] Test: Aria-labels present on navigation buttons
- [ ] All tests passing (no regressions)

### AC-4.11.8: Integration Tests
- [ ] Test: Dashboard defaults to yesterday when no URL param
- [ ] Test: Dashboard uses URL param date when present
- [ ] Test: Date change updates URL via navigate()
- [ ] Test: useGames called with correct date parameter
- [ ] Test: GameList re-renders when date changes

### AC-4.11.9: Manual Verification
- [ ] Load dashboard → Shows yesterday's date and games
- [ ] Social posts visible for yesterday's completed games
- [ ] Click prev/next → Games refresh, URL updates
- [ ] Edit URL `?date=2025-03-15` → Loads games for that date
- [ ] Browser back/forward buttons work
- [ ] Auto-refresh continues for today's date (60s polling)
- [ ] No auto-refresh for historical dates (performance optimization)
- [ ] Mobile responsive (navigator fits on small screens)

### AC-4.11.10: Documentation Updates
- [ ] Update PRD.md: Move "Historical Browsing" from "Acceptable Simplifications" to "Core MVP Features"
- [ ] Update PRD.md: Add note documenting product discovery insight (yesterday > today)
- [ ] Add JSDoc comments to DateNavigator component
- [ ] Add JSDoc comments to updated useGames hook
- [ ] Update CLAUDE.md if navigation usage patterns need documentation

---

## Dependencies

**Required (Must be complete):**
- ✅ Story 3-4: Build Game List (useGames hook exists)
- ✅ Story 4-10: Social Posts Feed (value to unlock)
- ✅ Backend API: Supports `?date=YYYY-MM-DD` (already implemented!)

**Nice to Have (Can proceed without):**
- None - all dependencies satisfied

---

## Files Modified

**Frontend:**
- `frontend/src/components/DateNavigator.tsx` - **NEW**: Prev/Next day navigation component
- `frontend/src/hooks/useGames.ts` - **MODIFIED**: Add date parameter
- `frontend/src/routes/_layout/index.tsx` - **MODIFIED**: Integrate DateNavigator, URL state
- `frontend/src/components/DateNavigator.test.tsx` - **NEW**: Component tests

**Documentation:**
- `docs/PRD.md` - **MODIFIED**: Update historical browsing from simplification to core feature
- `docs/sprint-change-proposal-2025-11-20.md` - **EXISTING**: Full change analysis (reference)

**Tests:**
- `frontend/src/routes/_layout/index.test.tsx` - **MODIFIED**: Add date navigation tests

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| TanStack Router query params conflict | Low | Low | Well-documented API, test thoroughly |
| Cache invalidation issues (date changes) | Low | Low | TanStack Query handles queryKey changes automatically |
| Timezone confusion (user local vs UTC) | Medium | Low | Display dates prominently, document behavior |
| Breaking existing auto-refresh | Low | Medium | Test polling continues for today's date |
| Default to yesterday confuses users | Low | Low | Date clearly displayed, easy to navigate to today |

**Overall Risk:** **LOW** (Frontend-only, well-scoped, backend already supports)

---

## Success Metrics

- ✅ Users can navigate to yesterday's games and see social posts
- ✅ URL state persists (shareable links work)
- ✅ Browser back/forward navigation works
- ✅ Auto-refresh continues for today's date
- ✅ No performance regression (separate caching per date)
- ✅ No visual regressions (existing components unchanged)

---

## References

- **Sprint Change Proposal**: [docs/sprint-change-proposal-2025-11-20.md](../sprint-change-proposal-2025-11-20.md)
- **PRD Section**: [docs/PRD.md](../PRD.md) (lines 274-276 - to be updated)
- **Backend API**: [backend/app/api/routes/games.py:26-63](../../backend/app/api/routes/games.py) (date parameter already implemented)
- **Story 3-4**: [3-4-build-game-list.md](./3-4-build-game-list.md) (useGames hook foundation)
- **Story 4-10**: [4-10-social-posts-feed.md](./4-10-social-posts-feed.md) (social posts integration)

---

## Dev Agent Record

### Context Reference
- [4-11-date-navigation.context.xml](4-11-date-navigation.context.xml) - Generated 2025-11-20

---

## Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2025-11-20 | 1.0 | Story drafted and marked ready-for-dev |
