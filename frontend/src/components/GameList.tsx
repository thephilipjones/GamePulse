import {
  Alert,
  Box,
  Grid,
  HStack,
  Heading,
  Skeleton,
  Spinner,
  Stack,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useMemo } from "react";
import type { GamePublic } from "../client/types.gen";
import { useGames } from "../hooks/useGames";
import { GameCard } from "./GameCard";

/**
 * GameList component displays today's NCAA basketball games grouped by status.
 *
 * Handles five states:
 * 1. Loading: Shows skeleton placeholders in grid layout
 * 2. Error: Displays user-friendly error message on fetch failure
 * 3. Empty: Shows informative message when no games are scheduled
 * 4. Background Refetch: Shows subtle "Updating..." indicator during polling
 * 5. Success: Renders game cards grouped by status (Live → Final → Upcoming)
 *
 * Features:
 * - Status-based grouping with section headers
 * - Responsive grid: Mobile (1 col), Tablet (2 col), Desktop (3 col)
 * - Empty sections automatically hidden
 * - Preserves existing polling behavior (60s interval)
 *
 * Uses TanStack Query via useGames hook for efficient data fetching
 * with automatic caching, retry logic, and polling.
 *
 * @example
 * ```tsx
 * <Container>
 *   <GameList />
 * </Container>
 * ```
 */
export function GameList() {
  const { data, isLoading, isError, isFetching } = useGames();

  // Group games by status (memoized to prevent unnecessary recalculations)
  const { liveGames, finalGames, upcomingGames } = useMemo(() => {
    if (!data?.games) {
      return { liveGames: [], finalGames: [], upcomingGames: [] };
    }

    return {
      liveGames: data.games.filter(
        (g) => g.game_status === "in_progress" || g.game_status === "live",
      ),
      finalGames: data.games.filter((g) => g.game_status === "final"),
      upcomingGames: data.games.filter(
        (g) => g.game_status === "scheduled" || g.game_status === "pre",
      ),
    };
  }, [data?.games]);

  // Loading state: Skeleton placeholders in grid layout
  if (isLoading) {
    return (
      <Grid
        templateColumns={{
          base: "repeat(2, 1fr)",
          xl: "repeat(3, 1fr)",
        }}
        gap={4}
      >
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} height="200px" borderRadius="lg" />
        ))}
      </Grid>
    );
  }

  // Error state: Show warning with cached data if available
  if (isError && !data) {
    return (
      <Alert.Root status="error">
        <Alert.Indicator />
        <Alert.Title>
          Unable to load games. Please check that the backend is running.
        </Alert.Title>
      </Alert.Root>
    );
  }

  if (isError && data) {
    // Show warning banner, then render cached games normally
    return (
      <Stack gap={4}>
        <Alert.Root status="warning">
          <Alert.Indicator />
          <Alert.Title>
            Unable to fetch latest data. Showing cached results.
          </Alert.Title>
        </Alert.Root>
        <GameListContent
          liveGames={liveGames}
          finalGames={finalGames}
          upcomingGames={upcomingGames}
        />
      </Stack>
    );
  }

  // Empty state: no games scheduled
  if (!data || data.games.length === 0) {
    return (
      <Text fontSize="lg" color="gray.500" textAlign="center">
        No games scheduled for today.
      </Text>
    );
  }

  // Success state: display grouped game cards
  return (
    <VStack gap={4} align="stretch">
      {/* Background refetch indicator */}
      {isFetching && !isLoading && (
        <HStack justify="center" color="gray.500" fontSize="sm">
          <Spinner size="sm" />
          <Text>Updating...</Text>
        </HStack>
      )}

      <GameListContent
        liveGames={liveGames}
        finalGames={finalGames}
        upcomingGames={upcomingGames}
      />
    </VStack>
  );
}

/**
 * Renders game cards grouped by status with section headers.
 * Empty sections are automatically hidden.
 */
interface GameListContentProps {
  liveGames: GamePublic[];
  finalGames: GamePublic[];
  upcomingGames: GamePublic[];
}

function GameListContent({
  liveGames,
  finalGames,
  upcomingGames,
}: GameListContentProps) {
  // If all sections are empty, show empty state
  const hasGames =
    liveGames.length > 0 || finalGames.length > 0 || upcomingGames.length > 0;

  if (!hasGames) {
    return (
      <Text fontSize="lg" color="gray.500" textAlign="center">
        No games scheduled for today.
      </Text>
    );
  }

  return (
    <VStack gap={8} align="stretch">
      {/* Live Games Section */}
      {liveGames.length > 0 && (
        <Box>
          <Heading as="h2" size="lg" mb={4} color="game.live">
            Live Games
          </Heading>
          <Grid
            templateColumns={{
              base: "repeat(2, 1fr)",
              xl: "repeat(3, 1fr)",
            }}
            gap={4}
          >
            {liveGames.map((game) => (
              <GameCard key={game.game_key} game={game} />
            ))}
          </Grid>
        </Box>
      )}

      {/* Final Games Section */}
      {finalGames.length > 0 && (
        <Box>
          <Heading as="h2" size="lg" mb={4} color="game.final">
            Final Games
          </Heading>
          <Grid
            templateColumns={{
              base: "repeat(2, 1fr)",
              xl: "repeat(3, 1fr)",
            }}
            gap={4}
          >
            {finalGames.map((game) => (
              <GameCard key={game.game_key} game={game} />
            ))}
          </Grid>
        </Box>
      )}

      {/* Upcoming Games Section */}
      {upcomingGames.length > 0 && (
        <Box>
          <Heading as="h2" size="lg" mb={4} color="game.scheduled">
            Upcoming Games
          </Heading>
          <Grid
            templateColumns={{
              base: "repeat(2, 1fr)",
              xl: "repeat(3, 1fr)",
            }}
            gap={4}
          >
            {upcomingGames.map((game) => (
              <GameCard key={game.game_key} game={game} />
            ))}
          </Grid>
        </Box>
      )}
    </VStack>
  );
}
