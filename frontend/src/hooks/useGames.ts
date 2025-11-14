import { useQuery } from "@tanstack/react-query";
import type { GameListResponse } from "../client/types.gen";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Custom React Query hook for fetching today's NCAA basketball games.
 *
 * Uses TanStack Query for efficient data fetching with automatic caching,
 * retry logic, and stale-while-revalidate behavior. Automatically polls
 * for fresh data every 15 minutes while the page is visible.
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
  return useQuery<GameListResponse>({
    queryKey: ["games", "today"],
    queryFn: async (): Promise<GameListResponse> => {
      const res = await fetch(`${API_BASE_URL}/api/v1/games/today`);
      if (!res.ok) {
        throw new Error("Failed to fetch games");
      }
      return res.json();
    },
    refetchInterval: 900000, // Poll every 15 minutes (900,000ms)
    refetchIntervalInBackground: true, // Keep polling even when tab is hidden
    staleTime: 900000, // Consider data fresh for 15 minutes
  });
}
