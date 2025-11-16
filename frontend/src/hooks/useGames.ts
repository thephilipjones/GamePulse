import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import type { GameListResponse } from "../client/types.gen";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Custom React Query hook for fetching today's NCAA basketball games.
 *
 * Uses TanStack Query for efficient data fetching with automatic caching,
 * retry logic, and stale-while-revalidate behavior. Automatically polls
 * for fresh data every 1 minute while the page is visible.
 *
 * Automatically calculates "today" based on the user's local timezone
 * to ensure users see games for their local calendar date, not UTC.
 *
 * @returns React Query result with { data, isLoading, isError, isFetching, error }
 *
 * @example
 * ```tsx
 * const { data, isLoading, isError, isFetching } = useGames();
 *
 * if (isLoading) return <Skeleton />;
 * if (isError) return <Alert>Error loading games</Alert>;
 * if (isFetching && !isLoading) return <Spinner>Updating...</Spinner>;
 * return <div>{data.games.map(game => ...)}</div>;
 * ```
 */
export function useGames() {
  // Calculate user's local date (YYYY-MM-DD format)
  // This ensures users see games for their local "today", not server's UTC today
  const localDate = format(new Date(), 'yyyy-MM-dd');

  return useQuery<GameListResponse>({
    queryKey: ["games", localDate],
    queryFn: async (): Promise<GameListResponse> => {
      const res = await fetch(`${API_BASE_URL}/api/v1/games?date=${localDate}`);
      if (!res.ok) {
        throw new Error("Failed to fetch games");
      }
      return res.json();
    },
    refetchInterval: 60000, // Poll every 1 minute (60,000ms)
    refetchIntervalInBackground: true, // Keep polling even when tab is hidden
    staleTime: 60000, // Consider data fresh for 1 minute
  });
}
