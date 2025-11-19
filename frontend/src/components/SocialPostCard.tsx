import { Box, HStack, Icon, Link, Text } from "@chakra-ui/react";
import { formatDistanceToNow, parseISO } from "date-fns";
import { FaHeart, FaReddit } from "react-icons/fa";
import { LuExternalLink } from "react-icons/lu";
import { SiBluesky } from "react-icons/si";
import type { SocialPostPublic } from "../hooks/useSocialPosts";
import { SentimentBadge } from "./SentimentBadge";

interface SocialPostCardProps {
  post: SocialPostPublic;
}

/**
 * Individual social post card component (Story 4-10).
 *
 * Displays:
 * - Platform icon (Reddit orange, Bluesky blue)
 * - Relative timestamp (e.g., "5 minutes ago")
 * - Sentiment badge (color-coded)
 * - Post text (truncated to 3 lines)
 * - Engagement score with heart icon
 * - "View Post" external link
 *
 * Styled with left border color matching sentiment.
 * Meets accessibility requirements (AC-4.10.8).
 */
export function SocialPostCard({ post }: SocialPostCardProps) {
  // Sentiment-based styling
  const borderColors = {
    positive: "green.500",
    neutral: "gray.400",
    negative: "red.500",
  };

  const bgColors = {
    positive: "green.900/20",
    neutral: "gray.700/20",
    negative: "red.900/20",
  };

  // Format relative timestamp
  let relativeTime = "Just now";
  try {
    const date = parseISO(post.created_at);
    relativeTime = formatDistanceToNow(date, { addSuffix: true });
  } catch {
    // Keep default if parsing fails
  }

  // Platform display config
  const platformConfig = {
    reddit: {
      icon: FaReddit,
      color: "orange.500",
      label: "Reddit",
    },
    bluesky: {
      icon: SiBluesky,
      color: "blue.400",
      label: "Bluesky",
    },
  };

  const platform = platformConfig[post.platform];

  return (
    <Box
      p={3}
      bg={bgColors[post.sentiment_label]}
      borderLeft="3px solid"
      borderColor={borderColors[post.sentiment_label]}
      borderRadius="md"
    >
      {/* Header: Platform + Timestamp + Sentiment Badge */}
      <HStack justify="space-between" mb={2}>
        <HStack gap={2}>
          <Icon as={platform.icon} color={platform.color} boxSize={4} />
          <Text fontSize="xs" color="gray.400">
            {relativeTime}
          </Text>
        </HStack>
        <SentimentBadge sentiment={post.sentiment_label} />
      </HStack>

      {/* Post Text (truncated to 3 lines) */}
      <Text
        fontSize="sm"
        color="gray.200"
        lineClamp={3}
        mb={2}
        title={post.post_text}
      >
        {post.post_text}
      </Text>

      {/* Footer: Engagement Score + View Post Link */}
      <HStack justify="space-between">
        <HStack gap={1}>
          <Icon as={FaHeart} boxSize={3} color="gray.500" />
          <Text fontSize="xs" color="gray.400">
            {post.engagement_score.toLocaleString()}
          </Text>
        </HStack>
        <Link
          href={post.source_url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`View post on ${platform.label}`}
          _hover={{ textDecoration: "none" }}
        >
          <HStack
            gap={1}
            fontSize="xs"
            color="blue.400"
            _hover={{ color: "blue.300" }}
          >
            <Text>View Post</Text>
            <Icon as={LuExternalLink} boxSize={3} />
          </HStack>
        </Link>
      </HStack>
    </Box>
  );
}
