import { Container } from "@chakra-ui/react";
import { createFileRoute } from "@tanstack/react-router";
import { GameList } from "../../components/GameList";

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
});

/**
 * Main dashboard page for GamePulse.
 * Displays NCAA Men's Basketball games with excitement scores.
 * Auto-refreshes every 1 minute via TanStack Query polling.
 *
 * Future expansion (Epic 8):
 * - Individual game detail route: /game/:id
 */
function Dashboard() {
  return (
    <Container maxW="container.xl" py={8}>
      <GameList />
    </Container>
  );
}
