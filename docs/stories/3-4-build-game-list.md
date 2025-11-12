# Story 3.4: Build Simple Game List Component

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want a React component that fetches and displays today's games in a simple list,
So that users can see live NCAA game data.

---

## Acceptance Criteria

**Given** the `/api/games/today` endpoint returns game data
**When** I create the GameList component
**Then** the component:
- Fetches data from `/api/games/today` using React Query hook
- Displays games in a simple list format (no fancy cards yet)
- Shows for each game: home team name, away team name, scores, game status
- Uses Chakra UI `<Box>` or `<Stack>` for layout
- Shows loading skeleton while data is fetching
- Shows error message if API request fails
- Shows "No games today" if games array is empty

**And** I create a custom React Query hook: `useGames()`

**And** the component displays team colors as accent (background or border)

**And** the list is responsive on mobile (stack vertically, readable font sizes)

**And** I can verify: Dashboard shows real game data from NCAA API after poller has run

---

## Prerequisites

- Story 3.1 (API endpoint)
- Story 3.3 (Dashboard page exists)

---

## Technical Notes

**Create File:** `frontend/src/hooks/useGames.ts`
```typescript
import { useQuery } from '@tanstack/react-query';

interface Game {
  game_id: string;
  home_team: {
    team_id: string;
    team_name: string;
    primary_color: string | null;
  };
  away_team: {
    team_id: string;
    team_name: string;
    primary_color: string | null;
  };
  home_score: number | null;
  away_score: number | null;
  game_status: string;
}

interface GamesResponse {
  games: Game[];
  updated_at: string;
}

export function useGames() {
  return useQuery({
    queryKey: ['games', 'today'],
    queryFn: async (): Promise<GamesResponse> => {
      const res = await fetch('/api/games/today');
      if (!res.ok) {
        throw new Error('Failed to fetch games');
      }
      return res.json();
    },
  });
}
```

**Create File:** `frontend/src/components/GameList.tsx`
```typescript
import { Box, Stack, Text, Skeleton, Alert, HStack } from '@chakra-ui/react';
import { useGames } from '../hooks/useGames';

export function GameList() {
  const { data, isLoading, isError } = useGames();

  if (isLoading) {
    return (
      <Stack spacing={4}>
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} height="60px" />
        ))}
      </Stack>
    );
  }

  if (isError) {
    return (
      <Alert status="error">
        Unable to load games. Please try again later.
      </Alert>
    );
  }

  if (!data || data.games.length === 0) {
    return <Text>No games scheduled for today.</Text>;
  }

  return (
    <Stack spacing={4}>
      {data.games.map((game) => (
        <Box
          key={game.game_id}
          border="1px"
          borderColor="gray.600"
          p={4}
          borderRadius="md"
          borderLeftWidth="4px"
          borderLeftColor={game.away_team.primary_color || 'gray.500'}
        >
          <HStack justify="space-between">
            <Text>{game.away_team.team_name}</Text>
            <Text fontWeight="bold">{game.away_score ?? '-'}</Text>
          </HStack>
          <HStack justify="space-between">
            <Text>{game.home_team.team_name}</Text>
            <Text fontWeight="bold">{game.home_score ?? '-'}</Text>
          </HStack>
          <Text fontSize="sm" color="gray.400" mt={2}>
            {game.game_status}
          </Text>
        </Box>
      ))}
    </Stack>
  );
}
```

**Import in Dashboard.tsx:**
```typescript
import { GameList } from '../components/GameList';

// Inside Dashboard component:
<Box>
  <GameList />
</Box>
```

**Loading State:** `<Skeleton height="60px" />` repeated 5 times

**Error State:** `<Alert status="error">Unable to load games</Alert>`

**Empty State:** `<Text>No games scheduled for today</Text>`

**Team Colors:** Use `borderLeftColor` for visual accent

**Mobile Responsive:**
- Stack components use Chakra's responsive props
- Font sizes remain readable on mobile
- HStack automatically handles overflow

---

## Definition of Done

- [ ] useGames hook created with TypeScript types
- [ ] GameList component created
- [ ] Loading state with skeletons implemented
- [ ] Error state with alert implemented
- [ ] Empty state message implemented
- [ ] Game data displayed: teams, scores, status
- [ ] Team colors shown as accent
- [ ] Component imported in Dashboard
- [ ] Dashboard shows real game data
- [ ] Layout responsive on mobile
- [ ] Code follows TypeScript and React best practices
- [ ] Changes committed to git
