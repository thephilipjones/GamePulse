import { Badge, HStack } from "@chakra-ui/react";
import { format, parseISO } from "date-fns";

interface GameStatusBadgeProps {
  status: "scheduled" | "pre" | "in_progress" | "live" | "final";
  startTime?: string | null;
  gameClock?: string | null;
  gamePeriod?: string | null;
}

/**
 * Displays game status badge with contextual information.
 *
 * - LIVE: Red badge with game clock (e.g., "LIVE • 14:32 2nd Half")
 * - FINAL: Gray badge
 * - Scheduled: Blue badge with formatted start time
 *
 * Supports light/dark modes via semantic color tokens.
 */
export function GameStatusBadge({
  status,
  startTime,
  gameClock,
  gamePeriod,
}: GameStatusBadgeProps) {
  // LIVE games
  if (status === "in_progress" || status === "live") {
    // Build clock/period display text
    const clockPeriodParts = [];
    if (gameClock) clockPeriodParts.push(gameClock);
    if (gamePeriod && gamePeriod !== "FINAL") clockPeriodParts.push(gamePeriod);
    const clockPeriodText = clockPeriodParts.join(" • ");

    const ariaLabel = clockPeriodText
      ? `Game is live, ${clockPeriodText}`
      : "Game is live";

    return (
      <HStack gap={2}>
        <Badge
          colorPalette="red"
          bg="game.live"
          color="white"
          px={2}
          py={1}
          borderRadius="md"
          fontWeight="bold"
          fontSize="xs"
          aria-label={ariaLabel}
        >
          LIVE
        </Badge>
        {clockPeriodText && (
          <Badge
            colorPalette="red"
            variant="subtle"
            px={2}
            py={1}
            borderRadius="md"
            fontSize="xs"
          >
            {clockPeriodText}
          </Badge>
        )}
      </HStack>
    );
  }

  // FINAL games
  if (status === "final") {
    return (
      <Badge
        colorPalette="gray"
        bg="game.final"
        color="white"
        px={2}
        py={1}
        borderRadius="md"
        fontSize="xs"
        aria-label="Game is final"
      >
        FINAL
      </Badge>
    );
  }

  // Scheduled/Pre games
  if ((status === "scheduled" || status === "pre") && startTime) {
    try {
      // Parse ISO timestamp and format for display
      const date = parseISO(startTime);
      const formattedTime = format(date, "h:mm a");
      const formattedDate = format(date, "MMM d");

      return (
        <Badge
          colorPalette="blue"
          bg="game.scheduled"
          color="white"
          px={2}
          py={1}
          borderRadius="md"
          fontSize="xs"
          aria-label={`Game starts ${formattedDate} at ${formattedTime}`}
        >
          {formattedDate} • {formattedTime}
        </Badge>
      );
    } catch (error) {
      // Fallback if time parsing fails
      if (process.env.NODE_ENV === "development") {
        console.warn("Failed to parse game start time:", startTime, error);
      }
      return (
        <Badge
          colorPalette="blue"
          bg="game.scheduled"
          color="white"
          px={2}
          py={1}
          borderRadius="md"
          fontSize="xs"
          aria-label="Scheduled game"
        >
          Scheduled
        </Badge>
      );
    }
  }

  // Default fallback
  return null;
}
