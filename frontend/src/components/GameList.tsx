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
 * GameList component displays NCAA basketball games for a specific date, grouped by status.
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
 * - Adaptive caching: Today's games poll every 60s, historical games cached for 5 min
 *
 * Uses TanStack Query via useGames hook for efficient data fetching
 * with automatic caching, retry logic, and intelligent polling.
 *
 * @param date - Optional date in YYYY-MM-DD format. Defaults to today.
 *
 * @example
 * ```tsx
 * // Show today's games
 * <GameList />
 *
 * // Show games for specific date
 * <GameList date="2025-11-19" />
 * ```
 */
export interface GameListProps {
  /** Optional date in YYYY-MM-DD format. Defaults to today. */
  date?: string;
}

export function GameList({ date }: GameListProps = {}) {
  const { data, isLoading, isError, isFetching } = useGames(date);

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
        No games scheduled for this date.
      </Text>
    );
  }

  // Success state: display grouped game cards
  return (
    <Box position="relative">
      {/* Background refetch indicator - absolutely positioned to avoid layout shift */}
      {isFetching && !isLoading && (
        <HStack
          position="fixed"
          top={{ base: "110px", md: "90px" }}
          left="50%"
          transform="translateX(-50%)"
          color="gray.500"
          fontSize="sm"
          bg="bg.surface"
          px={4}
          py={2}
          borderRadius="full"
          boxShadow="md"
          zIndex={5}
        >
          <Spinner size="sm" />
          <Text>Updating...</Text>
        </HStack>
      )}

      <GameListContent
        liveGames={liveGames}
        finalGames={finalGames}
        upcomingGames={upcomingGames}
      />
    </Box>
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
        No games scheduled for this date.
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
