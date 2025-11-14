import { Alert, Box, HStack, Skeleton, Stack, Text } from "@chakra-ui/react";
import { useGames } from "../hooks/useGames";

/**
 * GameList component displays today's NCAA basketball games.
 *
 * Handles four states:
 * 1. Loading: Shows skeleton placeholders while fetching data
 * 2. Error: Displays user-friendly error message on fetch failure
 * 3. Empty: Shows informative message when no games are scheduled
 * 4. Success: Renders game cards with team names, scores, and colors
 *
 * Uses TanStack Query via useGames hook for efficient data fetching
 * with automatic caching and retry logic.
 *
 * @example
 * ```tsx
 * <Container>
 *   <GameList />
 * </Container>
 * ```
 */
export function GameList() {
  const { data, isLoading, isError } = useGames();

  // Loading state: 5 skeleton placeholders
  if (isLoading) {
    return (
      <Stack gap={4}>
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} height="60px" />
        ))}
      </Stack>
    );
  }

  // Error state: user-friendly message
  if (isError) {
    return (
      <Alert.Root status="error">
        <Alert.Indicator />
        <Alert.Title>Unable to load games. Please try again later.</Alert.Title>
      </Alert.Root>
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

  // Success state: display game cards
  return (
    <Stack gap={4}>
      {data.games.map((game) => (
        <Box
          key={game.game_key}
          border="1px"
          borderColor="gray.600"
          p={4}
          borderRadius="md"
          borderLeftWidth="4px"
          borderLeftColor={game.away_team.primary_color || "gray.500"}
        >
          <HStack justify="space-between">
            <Text>{game.away_team.team_name}</Text>
            <Text fontWeight="bold">{game.away_score ?? "-"}</Text>
          </HStack>
          <HStack justify="space-between">
            <Text>{game.home_team.team_name}</Text>
            <Text fontWeight="bold">{game.home_score ?? "-"}</Text>
          </HStack>
          <Text fontSize="sm" color="gray.400" mt={2}>
            {game.game_status || "Scheduled"}
          </Text>
        </Box>
      ))}
    </Stack>
  );
}
