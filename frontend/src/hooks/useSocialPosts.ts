import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Social post response from API (Story 4-10).
 * Matches backend SocialPostPublic schema.
 */
export interface SocialPostPublic {
  social_post_key: number;
  platform: "reddit" | "bluesky";
  post_text: string;
  created_at: string;
  engagement_score: number;
  sentiment_compound: number;
  sentiment_label: "positive" | "neutral" | "negative";
  source_url: string;
}

/**
 * Response schema for social posts list endpoint.
 * Matches backend SocialPostListResponse schema.
 */
export interface SocialPostListResponse {
  posts: SocialPostPublic[];
  total_count: number;
  game_id: string;
}

/**
 * Custom React Query hook for fetching social posts for a specific game (Story 4-10).
 *
 * Uses TanStack Query for efficient data fetching with:
 * - 5-minute staleTime (social posts don't change rapidly)
 * - 15-minute cacheTime
 * - Conditional fetch when gameId is provided
 *
 * @param gameId - Natural key for game (e.g., "ncaam_401525257")
 * @param limit - Maximum number of posts to return (default 10, max 50)
 * @returns React Query result with { data, isLoading, isError, error }
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useSocialPosts(game.game_id);
 *
 * if (isLoading) return <Skeleton />;
 * if (!data || data.posts.length === 0) return null;
 * return <SocialPostsFeed posts={data.posts} />;
 * ```
 */
export function useSocialPosts(gameId: string, limit = 10) {
  return useQuery<SocialPostListResponse>({
    queryKey: ["social-posts", gameId, limit],
    queryFn: async (): Promise<SocialPostListResponse> => {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/games/${gameId}/social-posts?limit=${limit}`,
      );
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error(`Game not found: ${gameId}`);
        }
        throw new Error("Failed to fetch social posts");
      }
      return res.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes (social posts don't change rapidly)
    gcTime: 15 * 60 * 1000, // 15 minutes cache
    enabled: !!gameId, // Don't fetch if gameId is empty
  });
}
