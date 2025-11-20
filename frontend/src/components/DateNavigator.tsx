import { HStack, IconButton, Text } from "@chakra-ui/react";
import { LuChevronLeft, LuChevronRight } from "react-icons/lu";

/**
 * DateNavigator component for navigating between dates with prev/next controls.
 *
 * Provides simple arrow-based navigation to move between days, with the current
 * date displayed in a human-readable format (e.g., "Wednesday, November 20, 2025").
 *
 * Designed for Story 4-11 to enable users to view games from different dates,
 * particularly yesterday's completed games where social post content is most valuable.
 *
 * @param currentDate - The currently selected date in YYYY-MM-DD format (ISO 8601)
 * @param onDateChange - Callback function called when user navigates to a different date
 *
 * @example
 * ```tsx
 * const [selectedDate, setSelectedDate] = useState('2025-11-19');
 *
 * <DateNavigator
 *   currentDate={selectedDate}
 *   onDateChange={(newDate) => setSelectedDate(newDate)}
 * />
 * ```
 */
export interface DateNavigatorProps {
  /** Current date in YYYY-MM-DD format */
  currentDate: string;
  /** Callback when date changes via prev/next navigation */
  onDateChange: (newDate: string) => void;
}

/**
 * DateNavigator component for prev/next day navigation.
 *
 * Satisfies AC-4.11.1: DateNavigator Component
 * - Accepts currentDate (YYYY-MM-DD) and onDateChange callback props
 * - Displays formatted date: "Wednesday, November 20, 2025"
 * - Prev/next buttons with accessible aria-labels
 * - Uses Chakra UI components (IconButton, HStack, Text)
 */
export function DateNavigator({
  currentDate,
  onDateChange,
}: DateNavigatorProps) {
  /**
   * Navigate to the previous day (yesterday relative to current date).
   * Creates a new Date object, decrements by 1 day, and converts back to YYYY-MM-DD format.
   */
  const handlePrevDay = () => {
    const date = new Date(currentDate + "T00:00:00"); // Explicit UTC midnight
    date.setDate(date.getDate() - 1);
    onDateChange(date.toISOString().split("T")[0]);
  };

  /**
   * Navigate to the next day (tomorrow relative to current date).
   * Creates a new Date object, increments by 1 day, and converts back to YYYY-MM-DD format.
   */
  const handleNextDay = () => {
    const date = new Date(currentDate + "T00:00:00"); // Explicit UTC midnight
    date.setDate(date.getDate() + 1);
    onDateChange(date.toISOString().split("T")[0]);
  };

  /**
   * Format date for display using locale-aware formatting.
   *
   * Desktop: "Wednesday, November 20, 2025"
   * Mobile: "Thu 11/20/25"
   *
   * Satisfies AC-4.11.6: Date Formatting
   * - Uses Intl.DateTimeFormat for locale-aware formatting
   * - Responsive: Long format on desktop, compact on mobile
   */
  const formatDisplayDateLong = (dateStr: string): string => {
    const date = new Date(dateStr + "T00:00:00"); // Parse as UTC midnight
    return new Intl.DateTimeFormat("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(date);
  };

  const formatDisplayDateShort = (dateStr: string): string => {
    const date = new Date(dateStr + "T00:00:00"); // Parse as UTC midnight
    return new Intl.DateTimeFormat("en-US", {
      weekday: "short",
      year: "2-digit",
      month: "numeric",
      day: "numeric",
    }).format(date);
  };

  return (
    <HStack justify="center" gap={{ base: 1, md: 4 }}>
      <IconButton
        aria-label="Previous day"
        onClick={handlePrevDay}
        size={{ base: "xs", md: "sm" }}
        variant="outline"
      >
        <LuChevronLeft />
      </IconButton>
      {/* Desktop: Long format */}
      <Text
        fontWeight="bold"
        fontSize="lg"
        minW="280px"
        textAlign="center"
        whiteSpace="nowrap"
        display={{ base: "none", md: "block" }}
      >
        {formatDisplayDateLong(currentDate)}
      </Text>
      {/* Mobile: Short format */}
      <Text
        fontWeight="bold"
        fontSize="sm"
        textAlign="center"
        whiteSpace="nowrap"
        display={{ base: "block", md: "none" }}
      >
        {formatDisplayDateShort(currentDate)}
      </Text>
      <IconButton
        aria-label="Next day"
        onClick={handleNextDay}
        size={{ base: "xs", md: "sm" }}
        variant="outline"
      >
        <LuChevronRight />
      </IconButton>
    </HStack>
  );
}
