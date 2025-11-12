# Story 3.5: Add Auto-Refresh Polling with React Query

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want the dashboard to automatically refresh game data every 15 minutes,
So that users see updated scores without manually reloading the page.

---

## Acceptance Criteria

**Given** the dashboard displays game data using React Query
**When** the user leaves the dashboard open
**Then** React Query automatically refetches data every 15 minutes

**And** a visual indicator shows when data is being refreshed (subtle loading state)

**And** a "Last updated X minutes ago" timestamp is displayed

**And** the refresh happens in the background (no full page reload)

**And** if the API request fails, the old data remains visible with a warning banner

**And** I can verify auto-refresh: Open dashboard, wait 15 min, see data update without manual refresh

---

## Prerequisites

- Story 3.4 (GameList component with useGames hook)

---

## Technical Notes

**Auto-Refresh Configuration:**
Already configured in Story 3.3 via React Query:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15 * 60 * 1000, // 15 minutes
      refetchInterval: 15 * 60 * 1000, // Auto-refresh every 15 min
    },
  },
});
```

**Add Background Refetch Indicator:**
Update `GameList.tsx`:
```typescript
import { Spinner, HStack } from '@chakra-ui/react';

export function GameList() {
  const { data, isLoading, isFetching, isError } = useGames();

  return (
    <>
      {isFetching && !isLoading && (
        <HStack justify="center" mb={4}>
          <Spinner size="sm" />
          <Text fontSize="sm" color="gray.500">Updating...</Text>
        </HStack>
      )}
      {/* Rest of component */}
    </>
  );
}
```

**Add Timestamp Display:**
Update `Dashboard.tsx`:
```typescript
import { formatDistanceToNow } from 'date-fns';

export function Dashboard() {
  const { data } = useGames();

  return (
    <Container maxW="container.xl" py={8}>
      <Heading as="h1" size="2xl" textAlign="center" mb={8}>
        GamePulse
      </Heading>

      {data && (
        <Text fontSize="sm" color="gray.500" mb={4} textAlign="center">
          Last updated {formatDistanceToNow(new Date(data.updated_at))} ago
        </Text>
      )}

      <GameList />
    </Container>
  );
}
```

**Install date-fns:**
```bash
cd frontend
npm install date-fns
```

**Error Handling with Stale Data:**
React Query automatically keeps last successful data in cache if refetch fails.

**Add Stale Data Warning:**
Update `GameList.tsx`:
```typescript
{isError && (
  <Alert status="warning" mb={4}>
    Unable to fetch latest data. Showing cached results.
  </Alert>
)}
```

**Verify Auto-Refresh:**
1. Open dashboard in browser
2. Open Network tab in DevTools
3. Wait 15 minutes
4. See new API request without manual refresh
5. Data updates automatically

**Alternative Test (Faster):**
Temporarily change refetchInterval to 30 seconds for testing:
```typescript
refetchInterval: 30 * 1000, // 30 seconds for testing
```

**Performance Considerations:**
- Use browser Network tab throttling to simulate slow connection
- Verify loading states don't cause layout shift
- Confirm stale-while-revalidate behavior

---

## Definition of Done

- [ ] Auto-refresh configured (15-minute interval)
- [ ] Background refetch indicator added (Spinner)
- [ ] "Last updated X min ago" timestamp displayed
- [ ] date-fns installed and imported
- [ ] Stale data warning alert added
- [ ] React Query keeps cached data on error
- [ ] No full page reload on refresh
- [ ] Auto-refresh verified with 15-min wait
- [ ] Network throttling test passed
- [ ] Code follows React Query best practices
- [ ] Changes committed to git

**🎯 MILESTONE COMPLETE:** Working demo by end of Week 1 achieved!
