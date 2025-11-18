import { Box, Text, VStack } from "@chakra-ui/react";

interface TeamCircleProps {
  teamName: string;
  primaryColor?: string | null;
  secondaryColor?: string | null;
  abbreviation: string;
}

/**
 * TeamCircle component displays team as a colored circle with abbreviation.
 *
 * Features:
 * - Large circular avatar (96px diameter)
 * - 2-letter team abbreviation in white
 * - Team color as background (with fallback)
 * - Uses secondary color when primary is white
 * - Team name displayed below circle
 * - Designed to match mockup specifications
 */
export function TeamCircle({
  teamName,
  primaryColor,
  secondaryColor,
  abbreviation,
}: TeamCircleProps) {
  // Use secondary color if primary is white (invisible on light backgrounds)
  const isWhite = primaryColor?.toUpperCase() === "#FFFFFF";
  const bgColor =
    isWhite && secondaryColor ? secondaryColor : primaryColor || "#6b7280";

  return (
    <VStack gap={1}>
      {/* Colored Circle with Abbreviation */}
      <Box
        w={{ base: 10, md: 16 }}
        h={{ base: 10, md: 16 }}
        bg={bgColor}
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
          color="white"
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
        lineClamp={1}
        maxW={{ base: 10, md: 16 }}
      >
        {teamName}
      </Text>
    </VStack>
  );
}
