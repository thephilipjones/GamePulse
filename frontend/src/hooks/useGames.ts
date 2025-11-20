import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import type { GameListResponse } from "../client/types.gen";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Custom React Query hook for fetching NCAA basketball games for a specific date.
 *
 * Uses TanStack Query for efficient data fetching with automatic caching,
 * retry logic, and stale-while-revalidate behavior.
 *
 * Implements intelligent caching strategy (AC-4.11.5):
 * - **Today's games**: Polls every 60 seconds (scores/status change frequently)
 * - **Historical games**: No polling, 5-minute staleTime (games already final)
 *
 * @param date - Optional date in YYYY-MM-DD format. Defaults to today in user's local timezone.
 * @returns React Query result with { data, isLoading, isError, isFetching, error }
 *
 * @example
 * ```tsx
 * // Fetch today's games (auto-refresh every 60 seconds)
 * const { data } = useGames();
 *
 * // Fetch specific date (no auto-refresh, 5-minute cache)
 * const { data } = useGames('2025-11-19');
 *
 * // Typical usage in component
 * const { data, isLoading, isError, isFetching } = useGames(selectedDate);
 * if (isLoading) return <Skeleton />;
 * if (isError) return <Alert>Error loading games</Alert>;
 * return <div>{data.games.map(game => <GameCard game={game} />)}</div>;
 * ```
 *
 * Satisfies AC-4.11.2: Update useGames Hook
 * - Accepts optional date parameter (YYYY-MM-DD)
 * - Fetches from GET /api/v1/games?date={date} when date provided
 * - Defaults to today's date when omitted
 * - QueryKey includes date for separate caching per date
 */
export function useGames(date?: string) {
  // Calculate user's local date (YYYY-MM-DD format) if no date provided
  // This ensures users see games for their local "today", not server's UTC today
  const localDate = date || format(new Date(), "yyyy-MM-dd");

  // Determine if we're fetching today's games or historical games
  // Today's games need frequent polling, historical games are static
  const isToday = localDate === format(new Date(), "yyyy-MM-dd");

  return useQuery<GameListResponse>({
    // AC-4.11.2: QueryKey includes date for separate cache entries per date
    queryKey: ["games", localDate],
    queryFn: async (): Promise<GameListResponse> => {
      const res = await fetch(`${API_BASE_URL}/api/v1/games?date=${localDate}`);
      if (!res.ok) {
        throw new Error("Failed to fetch games");
      }
      return res.json();
    },
    // AC-4.11.5: Cache Optimization
    // Today: 1-minute staleTime (existing behavior, games change frequently)
    // Historical: 5-minute staleTime (games already final, less frequent refetch)
    staleTime: isToday ? 60000 : 5 * 60 * 1000,

    // AC-4.11.5: Polling Optimization
    // Today: Poll every 60 seconds (scores/status update frequently)
    // Historical: No polling (games already completed, no changes expected)
    refetchInterval: isToday ? 60000 : false,
    refetchIntervalInBackground: isToday, // Only poll in background for today

    // Keep previous data visible during navigation to prevent flash
    placeholderData: keepPreviousData,
  });
}
