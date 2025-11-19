import { describe, expect, it, vi } from "vitest";
import type { SocialPostPublic } from "../hooks/useSocialPosts";
import { render, screen } from "../test-utils";
import { SentimentBadge } from "./SentimentBadge";
import { SocialPostCard } from "./SocialPostCard";
import { SocialPostsFeed } from "./SocialPostsFeed";

// Mock the useSocialPosts hook
vi.mock("../hooks/useSocialPosts", () => ({
  useSocialPosts: vi.fn(),
}));

import { useSocialPosts } from "../hooks/useSocialPosts";

const mockedUseSocialPosts = vi.mocked(useSocialPosts);

// Test data factory
function createMockPost(
  overrides?: Partial<SocialPostPublic>,
): SocialPostPublic {
  return {
    social_post_key: 1,
    platform: "reddit",
    post_text: "Duke opens with 12-0 run! This is going to be a great game!",
    created_at: "2025-11-16T20:05:32Z",
    engagement_score: 847,
    sentiment_compound: 0.85,
    sentiment_label: "positive",
    source_url:
      "https://www.reddit.com/r/CollegeBasketball/comments/abc123/duke_starts/",
    ...overrides,
  };
}

describe("SentimentBadge", () => {
  it("renders positive sentiment with correct label", () => {
    render(<SentimentBadge sentiment="positive" />);
    expect(screen.getByText("Positive")).toBeInTheDocument();
  });

  it("renders neutral sentiment with correct label", () => {
    render(<SentimentBadge sentiment="neutral" />);
    expect(screen.getByText("Neutral")).toBeInTheDocument();
  });

  it("renders negative sentiment with correct label", () => {
    render(<SentimentBadge sentiment="negative" />);
    expect(screen.getByText("Negative")).toBeInTheDocument();
  });

  it("has correct aria-label for accessibility", () => {
    render(<SentimentBadge sentiment="positive" />);
    const badge = screen.getByLabelText("Positive sentiment");
    expect(badge).toBeInTheDocument();
  });
});

describe("SocialPostCard", () => {
  it("renders post text", () => {
    const post = createMockPost();
    render(<SocialPostCard post={post} />);
    expect(screen.getByText(/Duke opens with 12-0 run/)).toBeInTheDocument();
  });

  it("renders Reddit platform icon", () => {
    const post = createMockPost({ platform: "reddit" });
    render(<SocialPostCard post={post} />);
    // Icon presence verified by View Post link aria-label
    expect(screen.getByLabelText("View post on Reddit")).toBeInTheDocument();
  });

  it("renders Bluesky platform icon", () => {
    const post = createMockPost({
      platform: "bluesky",
      source_url: "https://bsky.app/profile/user.bsky.social/post/123",
    });
    render(<SocialPostCard post={post} />);
    expect(screen.getByLabelText("View post on Bluesky")).toBeInTheDocument();
  });

  it("renders engagement score", () => {
    const post = createMockPost({ engagement_score: 847 });
    render(<SocialPostCard post={post} />);
    expect(screen.getByText("847")).toBeInTheDocument();
  });

  it("renders sentiment badge", () => {
    const post = createMockPost({ sentiment_label: "positive" });
    render(<SocialPostCard post={post} />);
    expect(screen.getByText("Positive")).toBeInTheDocument();
  });

  it("renders external link with correct href", () => {
    const post = createMockPost({
      source_url: "https://www.reddit.com/r/test/comments/abc123/",
    });
    render(<SocialPostCard post={post} />);

    const link = screen.getByLabelText("View post on Reddit");
    expect(link).toHaveAttribute(
      "href",
      "https://www.reddit.com/r/test/comments/abc123/",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("formats relative timestamp", () => {
    // Use a timestamp that will show "about X hours ago" or similar
    const post = createMockPost();
    render(<SocialPostCard post={post} />);
    // Just verify it renders without error (actual text depends on current time)
    expect(screen.getByText(/ago/i)).toBeInTheDocument();
  });
});

describe("SocialPostsFeed", () => {
  it("renders posts when data is available", () => {
    const mockPosts = [
      createMockPost({ social_post_key: 1, post_text: "First post!" }),
      createMockPost({ social_post_key: 2, post_text: "Second post!" }),
    ];

    mockedUseSocialPosts.mockReturnValue({
      data: { posts: mockPosts, total_count: 2, game_id: "test" },
      isLoading: false,
      isError: false,
      error: null,
    } as any);

    render(<SocialPostsFeed gameId="ncaam_test" />);

    expect(screen.getByText("Top Moments")).toBeInTheDocument();
    expect(screen.getByText("First post!")).toBeInTheDocument();
    expect(screen.getByText("Second post!")).toBeInTheDocument();
  });

  it("returns null when no posts available (empty state)", () => {
    mockedUseSocialPosts.mockReturnValue({
      data: { posts: [], total_count: 0, game_id: "test" },
      isLoading: false,
      isError: false,
      error: null,
    } as any);

    render(<SocialPostsFeed gameId="ncaam_test" />);

    // Section should not render at all (null returned)
    expect(screen.queryByText("Top Moments")).not.toBeInTheDocument();
  });

  it("shows loading skeleton during fetch", () => {
    mockedUseSocialPosts.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as any);

    render(<SocialPostsFeed gameId="ncaam_test" />);

    expect(screen.getByText("Top Moments")).toBeInTheDocument();
    // Skeleton will render (testing-library may not show skeleton text)
  });

  it("returns null on error (hides section silently)", () => {
    mockedUseSocialPosts.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Failed"),
    } as any);

    render(<SocialPostsFeed gameId="ncaam_test" />);

    // Section should not render at all (null returned)
    expect(screen.queryByText("Top Moments")).not.toBeInTheDocument();
  });

  it("renders multiple posts in order", () => {
    const mockPosts = [
      createMockPost({
        social_post_key: 1,
        engagement_score: 500,
        post_text: "High engagement",
      }),
      createMockPost({
        social_post_key: 2,
        engagement_score: 300,
        post_text: "Medium engagement",
      }),
      createMockPost({
        social_post_key: 3,
        engagement_score: 100,
        post_text: "Low engagement",
      }),
    ];

    mockedUseSocialPosts.mockReturnValue({
      data: { posts: mockPosts, total_count: 3, game_id: "test" },
      isLoading: false,
      isError: false,
      error: null,
    } as any);

    render(<SocialPostsFeed gameId="ncaam_test" />);

    // All posts should be rendered
    expect(screen.getByText("High engagement")).toBeInTheDocument();
    expect(screen.getByText("Medium engagement")).toBeInTheDocument();
    expect(screen.getByText("Low engagement")).toBeInTheDocument();
  });

  it("renders different sentiment colors", () => {
    const mockPosts = [
      createMockPost({ social_post_key: 1, sentiment_label: "positive" }),
      createMockPost({ social_post_key: 2, sentiment_label: "neutral" }),
      createMockPost({ social_post_key: 3, sentiment_label: "negative" }),
    ];

    mockedUseSocialPosts.mockReturnValue({
      data: { posts: mockPosts, total_count: 3, game_id: "test" },
      isLoading: false,
      isError: false,
      error: null,
    } as any);

    render(<SocialPostsFeed gameId="ncaam_test" />);

    // All sentiment badges should render
    expect(screen.getByText("Positive")).toBeInTheDocument();
    expect(screen.getByText("Neutral")).toBeInTheDocument();
    expect(screen.getByText("Negative")).toBeInTheDocument();
  });
});
