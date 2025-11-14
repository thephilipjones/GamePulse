import { Box, Container, Heading, Text } from "@chakra-ui/react";
import { createFileRoute } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import { useEffect, useState } from "react";
import { GameList } from "../../components/GameList";
import { useGames } from "../../hooks/useGames";

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
});

/**
 * Main dashboard page for GamePulse.
 * Displays NCAA Men's Basketball games with excitement scores.
 * Auto-refreshes every 15 minutes with live-updating "last updated" timestamp.
 *
 * Future expansion (Epic 8):
 * - Individual game detail route: /game/:id
 */
function Dashboard() {
  const { data } = useGames();
  const [, setNow] = useState(Date.now());

  // Update timestamp display every 30 seconds for live relative time
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <Container maxW="container.xl" py={8}>
      <Heading as="h1" size="2xl" textAlign="center" mb={8}>
        GamePulse
      </Heading>
      {data?.generated_at && (
        <Text fontSize="sm" color="gray.500" textAlign="center" mb={4}>
          Last updated{" "}
          {formatDistanceToNow(new Date(data.generated_at), {
            addSuffix: true,
          })}
        </Text>
      )}
      <Box>
        <GameList />
      </Box>
    </Container>
  );
}
