import { Box, Container, Heading } from "@chakra-ui/react";
import { createFileRoute } from "@tanstack/react-router";
import { GameList } from "../../components/GameList";

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
});

/**
 * Main dashboard page for GamePulse.
 * Displays NCAA Men's Basketball games with excitement scores.
 *
 * Future expansion (Epic 8):
 * - Individual game detail route: /game/:id
 */
function Dashboard() {
  return (
    <Container maxW="container.xl" py={8}>
      <Heading as="h1" size="2xl" textAlign="center" mb={8}>
        GamePulse
      </Heading>
      <Box>
        <GameList />
      </Box>
    </Container>
  );
}
