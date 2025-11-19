import { Badge } from "@chakra-ui/react";

interface SentimentBadgeProps {
  sentiment: "positive" | "neutral" | "negative";
}

/**
 * Color-coded sentiment badge component (Story 4-10).
 *
 * Displays sentiment classification with appropriate colors:
 * - Positive: Green (excitement, enthusiasm)
 * - Neutral: Gray (facts, statistics)
 * - Negative: Red (frustration, disappointment)
 *
 * Includes aria-labels for accessibility (AC-4.10.8).
 */
export function SentimentBadge({ sentiment }: SentimentBadgeProps) {
  const config = {
    positive: {
      colorPalette: "green",
      label: "Positive",
      ariaLabel: "Positive sentiment",
    },
    neutral: {
      colorPalette: "gray",
      label: "Neutral",
      ariaLabel: "Neutral sentiment",
    },
    negative: {
      colorPalette: "red",
      label: "Negative",
      ariaLabel: "Negative sentiment",
    },
  };

  const { colorPalette, label, ariaLabel } = config[sentiment];

  return (
    <Badge
      colorPalette={colorPalette}
      variant="subtle"
      px={2}
      py={0.5}
      borderRadius="md"
      fontSize="xs"
      aria-label={ariaLabel}
    >
      {label}
    </Badge>
  );
}
