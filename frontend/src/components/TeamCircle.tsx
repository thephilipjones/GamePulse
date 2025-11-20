import { Box, Text, VStack } from "@chakra-ui/react";

interface TeamCircleProps {
  teamName: string;
  primaryColor?: string | null;
  secondaryColor?: string | null;
  abbreviation: string;
}

/**
 * TeamCircle component displays team as a subtle circle with abbreviation.
 *
 * Features:
 * - Subtle circular placeholder (future logo container)
 * - 2-letter team abbreviation
 * - Muted background to not compete with gradient
 * - Team name displayed below circle
 * - Designed as placeholder for future team logos
 */
export function TeamCircle({ teamName, abbreviation }: TeamCircleProps) {
  return (
    <VStack gap={1}>
      {/* Subtle Circle with Abbreviation (future logo placeholder) */}
      <Box
        w={{ base: 10, md: 16 }}
        h={{ base: 10, md: 16 }}
        bg="rgba(128, 128, 128, 0.15)"
        borderRadius="full"
        display="flex"
        alignItems="center"
        justifyContent="center"
        flexShrink={0}
        aria-label={`${teamName} team`}
      >
        <Text
          fontSize={{ base: "xs", md: "lg" }}
          fontWeight="bold"
          color="text.primary"
          textTransform="uppercase"
          userSelect="none"
        >
          {abbreviation}
        </Text>
      </Box>

      {/* Team Name Below Circle */}
      <Text
        fontSize={{ base: "2xs", md: "xs" }}
        fontWeight="medium"
        color="text.primary"
        textAlign="center"
      >
        {teamName}
      </Text>
    </VStack>
  );
}
