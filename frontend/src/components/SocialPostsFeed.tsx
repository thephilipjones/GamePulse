import { Box, Skeleton, Text, VStack } from "@chakra-ui/react";
import { useSocialPosts } from "../hooks/useSocialPosts";
import { SocialPostCard } from "./SocialPostCard";

interface SocialPostsFeedProps {
  gameId: string;
}

/**
 * Social posts feed container component (Story 4-10).
 *
 * Fetches and displays social posts for a specific game.
 * Returns null if no posts exist (AC-4.10.9 empty state behavior).
 *
 * Features:
 * - "Top Moments" heading
 * - Loading skeleton during fetch
 * - Hidden when no posts (no empty state message)
 * - Posts ordered by engagement score (descending)
 */
export function SocialPostsFeed({ gameId }: SocialPostsFeedProps) {
  const { data, isLoading, isError } = useSocialPosts(gameId);

  // Loading state
  if (isLoading) {
    return (
      <Box>
        <Text fontSize="sm" fontWeight="medium" color="gray.400" mb={3}>
          Top Moments
        </Text>
        <VStack align="stretch" gap={2}>
          <Skeleton height="80px" borderRadius="md" />
          <Skeleton height="80px" borderRadius="md" />
        </VStack>
      </Box>
    );
  }

  // Error state - hide section silently
  if (isError) {
    return null;
  }

  // Empty state - hide section completely (AC-4.10.9)
  if (!data || data.posts.length === 0) {
    return null;
  }

  return (
    <Box>
      <Text fontSize="sm" fontWeight="medium" color="gray.400" mb={3}>
        Top Moments
      </Text>
      <VStack align="stretch" gap={2}>
        {data.posts.map((post) => (
          <SocialPostCard key={post.social_post_key} post={post} />
        ))}
      </VStack>
    </Box>
  );
}
