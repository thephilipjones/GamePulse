import { Box, Container, Heading, Text } from "@chakra-ui/react";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
});

/**
 * Main dashboard page for GamePulse.
 * Displays NCAA Men's Basketball games with excitement scores.
 */
function Dashboard() {
  return (
    <Container maxW="container.xl" py={8}>
      <Heading as="h1" size="2xl" textAlign="center" mb={8}>
        GamePulse
      </Heading>
      <Box>
        <Text fontSize="lg" color="gray.500" textAlign="center">
          Loading games...
        </Text>
      </Box>
    </Container>
  );
}
