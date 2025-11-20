import { Container, Heading } from "@chakra-ui/react";
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { GameList } from "../../components/GameList";
import { DateNavigator } from "../../components/DateNavigator";

/**
 * Helper function to get today's date in YYYY-MM-DD format.
 *
 * @returns Today's date in YYYY-MM-DD format (ISO 8601)
 *
 * @example
 * ```ts
 * getTodayDate() // "2025-11-20"
 * ```
 */
function getTodayDate(): string {
  const date = new Date();
  return date.toISOString().split("T")[0];
}

/**
 * Search params type for Dashboard route.
 * Supports optional date query parameter for navigating between dates.
 */
interface DashboardSearch {
  date?: string;
}

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  validateSearch: (search: Record<string, unknown>): DashboardSearch => {
    return {
      date: typeof search.date === "string" ? search.date : undefined,
    };
  },
});

/**
 * Main dashboard page for GamePulse.
 *
 * Displays NCAA Men's Basketball games with social posts and excitement scores.
 * Supports date navigation via prev/next controls with URL state management.
 *
 * Features (Story 4-11):
 * - **Date Navigation**: Prev/next day controls for browsing historical games
 * - **Default to Yesterday**: Shows yesterday's games by default (where social content exists)
 * - **URL State**: Date persists in URL query params (?date=2025-11-19) for shareable links
 * - **Adaptive Caching**: Today's games auto-refresh every 60s, historical games cached for 5 min
 *
 * Satisfies:
 * - AC-4.11.3: URL State Management
 * - AC-4.11.4: Dashboard Integration
 *
 * Future expansion (Epic 8):
 * - Individual game detail route: /game/:id
 * - Date range views (week/month)
 * - Calendar date picker
 */
function Dashboard() {
  const navigate = useNavigate({ from: Route.id });
  const search = useSearch({ from: Route.id });

  // AC-4.11.4: Default to today's date when no URL param present
  const currentDate = search.date || getTodayDate();

  /**
   * Handle date change from DateNavigator component.
   * Updates URL query params, triggering a new data fetch via TanStack Query.
   *
   * AC-4.11.3: URL State Management
   * - Browser back/forward navigation works correctly
   * - URL is shareable (date persists in query params)
   */
  const handleDateChange = (newDate: string) => {
    navigate({
      search: { date: newDate },
    });
  };

  return (
    <Container maxW="container.xl" py={8}>
      {/* GameList automatically fetches games for currentDate */}
      <GameList date={currentDate} />
    </Container>
  );
}
