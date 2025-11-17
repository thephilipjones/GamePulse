# Story 4-10: Social Posts Feed Integration

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-10
**Status:** todo
**Estimated Effort:** 10-14 hours
**Priority:** High (Week 2 - User-facing feature)
**Dependencies:** Story 4-5 (Sentiment analysis), Story 4-9 (Game card UI)

---

## User Story

**As a** basketball fan,
**I want** to see social media posts and fan reactions associated with each game,
**So that** I can understand the story and excitement around the game through real fan perspectives.

---

## Context

Stories 4-1 through 4-7 built the complete social data pipeline (Reddit + Bluesky → transform → sentiment). This story brings that data to the user interface by:

1. **Displaying social posts** linked to each game
2. **Showing engagement metrics** (upvotes, comments, likes)
3. **Providing source links** to original posts (Reddit, Bluesky)
4. **Color-coding sentiment** for quick emotional context

**Success Criteria:** Users can see fan reactions, click through to read full posts, and get a sense of game excitement from social sentiment.

---

## Dev Notes for Developer

### Architecture Patterns and Constraints

**Data Flow:**

```
Frontend → GET /api/v1/games/{game_id}/social-posts
  ↓
Backend queries fact_social_sentiment table
  ↓
Returns top posts by engagement_score
  ↓
Frontend renders post list with sentiment color coding
```

**Backend API Design:**

```python
# New endpoint: backend/app/api/routes/games.py

@router.get("/{game_id}/social-posts", response_model=SocialPostListResponse)
async def get_game_social_posts(
    game_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
) -> SocialPostListResponse:
    """
    Get social posts associated with a specific game.

    Returns posts ordered by engagement_score DESC.
    Includes sentiment scores for color coding.
    """
    # Query fact_social_sentiment table
    # Filter by game_id (join to fact_game on game_key)
    # Order by engagement_score DESC
    # Limit to top N posts
    pass
```

**Response Schema:**

```python
# backend/app/models/social.py (or new schemas file)

class SocialPostPublic(BaseModel):
    social_post_key: int
    platform: Literal["reddit", "bluesky"]
    post_text: str
    created_at: datetime
    engagement_score: int
    sentiment_compound: float  # -1.0 to +1.0
    sentiment_label: Literal["positive", "neutral", "negative"]  # Derived
    source_url: str  # Constructed from platform-specific fields

class SocialPostListResponse(BaseModel):
    posts: list[SocialPostPublic]
    total_count: int
    game_id: str
```

**Frontend Component Architecture:**

```typescript
// frontend/src/components/SocialPostsFeed.tsx

interface SocialPostsFeedProps {
  gameId: string;
}

export function SocialPostsFeed({ gameId }: SocialPostsFeedProps) {
  const { data, isLoading } = useSocialPosts(gameId);

  if (isLoading) return <Skeleton />;
  if (!data || data.posts.length === 0) return null; // Hide section if no posts

  return (
    <Box>
      <Heading size="sm">Top Moments</Heading>
      <VStack spacing={3}>
        {data.posts.map(post => (
          <SocialPostCard key={post.social_post_key} post={post} />
        ))}
      </VStack>
    </Box>
  );
}
```

**Empty State Behavior:**
- User requirement: "Empty state is just don't show the section, no text needed"
- Implementation: Return `null` from component if `posts.length === 0`
- No "No posts available" message
- Section completely hidden if no posts

### Learnings from Previous Stories

**Source:** [Story 4-5: Calculate Sentiment Analysis](4-5-calculate-sentiment.md)

Story 4-5 created the `fact_social_sentiment` table with VADER sentiment scores:

**Schema Fields Available:**
- `sentiment_compound`: -1.0 to +1.0 (primary sentiment score)
- `sentiment_positive`, `sentiment_negative`, `sentiment_neutral`: Component scores
- `game_key`: FK to fact_game (links posts to games)
- `social_post_key`: FK to stg_social_post (for platform-specific data)
- Denormalized fields: `platform`, `post_text`, `engagement_score`, `created_at`

**Sentiment Interpretation:**
```python
# VADER compound score thresholds
if sentiment_compound >= 0.05:
    label = "positive"  # Excitement, enthusiasm
elif sentiment_compound <= -0.05:
    label = "negative"  # Frustration, disappointment
else:
    label = "neutral"   # Facts, statistics
```

**Implications for Story 4-10:**

- All required data already in `fact_social_sentiment` table
- No need to join to `stg_social_post` or raw tables (denormalized design)
- Sentiment label can be derived in backend (classify compound score)
- Engagement scores pre-calculated (platform-specific formula)

**Source:** [Story 4-1: Reddit Posts Extraction](4-1-extract-reddit-posts.md)
**Source:** [Story 4-2: Bluesky Posts Extraction](4-2-extract-bluesky-posts.md)

**URL Construction Logic:**

**Reddit Posts:**
```python
# Backend: backend/app/api/routes/games.py
def construct_reddit_url(post_id: str, permalink: str) -> str:
    """
    Construct Reddit post URL from post data.

    Args:
        post_id: Reddit ID like "t3_abc123"
        permalink: Relative path like "/r/CollegeBasketball/comments/abc123/post_title/"

    Returns:
        Full URL: "https://www.reddit.com/r/CollegeBasketball/comments/abc123/post_title/"
    """
    if permalink:
        return f"https://www.reddit.com{permalink}"
    # Fallback if permalink missing
    return f"https://reddit.com/comments/{post_id.replace('t3_', '')}"
```

**Bluesky Posts:**
```python
# Backend: backend/app/api/routes/games.py
def construct_bluesky_url(author_handle: str, post_uri: str) -> str:
    """
    Construct Bluesky post URL from post data.

    Args:
        author_handle: User handle like "user.bsky.social"
        post_uri: AtProto URI like "at://did:plc:abc123.../app.bsky.feed.post/xyz456..."

    Returns:
        Full URL: "https://bsky.app/profile/user.bsky.social/post/xyz456"
    """
    # Extract post ID (last segment after final slash)
    post_id = post_uri.split('/')[-1]
    return f"https://bsky.app/profile/{author_handle}/post/{post_id}"
```

**Important:** URL construction happens in **backend**, not frontend. Frontend receives ready-to-use `source_url` field.

### Project Structure Notes

**Backend Files:**

```
backend/app/
├── api/
│   └── routes/
│       └── games.py                 # THIS STORY: Add /games/{id}/social-posts endpoint
├── models/
│   └── social.py                    # THIS STORY: Add SocialPostPublic schema
└── services/
    └── social_post_service.py       # NEW (optional): Query logic extraction
```

**Frontend Files:**

```
frontend/src/
├── components/
│   ├── SocialPostsFeed.tsx          # NEW: Feed container
│   ├── SocialPostCard.tsx           # NEW: Individual post card
│   ├── SentimentBadge.tsx           # NEW: Color-coded sentiment indicator
│   └── GameCard.tsx                 # MODIFIED: Add <SocialPostsFeed> section
├── hooks/
│   └── useSocialPosts.ts            # NEW: TanStack Query hook for posts
└── client/
    └── *                            # AUTO-GENERATED: TypeScript client updated
```

### Data Structure Details

**fact_social_sentiment Table Fields (Source):**

```sql
-- Source: backend/app/models/social.py
CREATE TABLE fact_social_sentiment (
  social_sentiment_key BIGSERIAL PRIMARY KEY,
  social_post_key BIGINT REFERENCES stg_social_post(social_post_key),
  game_key BIGINT REFERENCES fact_game(game_key),
  date_key INTEGER REFERENCES dim_date(date_key),

  -- Denormalized fields (avoid joins)
  platform VARCHAR(20),              -- "reddit" or "bluesky"
  post_text TEXT,                    -- Full post text
  engagement_score INTEGER,          -- Platform-specific engagement
  created_at TIMESTAMP,              -- Post creation time

  -- Sentiment scores
  sentiment_compound DECIMAL(5,4),   -- -1.0 to +1.0
  sentiment_positive DECIMAL(5,4),
  sentiment_negative DECIMAL(5,4),
  sentiment_neutral DECIMAL(5,4),

  analyzed_at TIMESTAMP DEFAULT NOW()
);
```

**stg_social_post Table (Joined for URL Fields):**

```sql
-- Source: backend/app/models/social.py
CREATE TABLE stg_social_post (
  social_post_key BIGSERIAL PRIMARY KEY,
  platform VARCHAR(20),
  post_id VARCHAR(255),               -- Reddit ID or Bluesky URI
  post_text TEXT,

  -- Reddit-specific fields
  author_handle VARCHAR(255),         -- Reddit username or Bluesky handle
  subreddit VARCHAR(100),             -- Reddit only
  permalink TEXT,                     -- Reddit only

  -- Bluesky-specific fields (stored in JSONB in raw table, extracted here)
  -- author_handle (shared field above)

  created_at TIMESTAMP,
  fetched_at TIMESTAMP
);
```

**Join Strategy for URL Construction:**

```sql
-- Query to get posts with source URLs
SELECT
  fss.social_sentiment_key,
  fss.platform,
  fss.post_text,
  fss.created_at,
  fss.engagement_score,
  fss.sentiment_compound,
  ssp.author_handle,
  ssp.permalink,        -- Reddit
  ssp.post_id           -- Bluesky post_uri
FROM fact_social_sentiment fss
JOIN stg_social_post ssp ON fss.social_post_key = ssp.social_post_key
JOIN fact_game fg ON fss.game_key = fg.game_key
WHERE fg.game_id = :game_id
ORDER BY fss.engagement_score DESC
LIMIT 10;
```

**Backend Query Implementation:**

```python
# backend/app/api/routes/games.py

from sqlmodel import select
from app.models.social import FactSocialSentiment, StgSocialPost
from app.models.fact_game import FactGame

stmt = (
    select(
        FactSocialSentiment,
        StgSocialPost.author_handle,
        StgSocialPost.permalink,
        StgSocialPost.post_id,
    )
    .join(StgSocialPost, FactSocialSentiment.social_post_key == StgSocialPost.social_post_key)
    .join(FactGame, FactSocialSentiment.game_key == FactGame.game_key)
    .where(FactGame.game_id == game_id)
    .order_by(FactSocialSentiment.engagement_score.desc())
    .limit(limit)
)

results = await session.execute(stmt)
rows = results.all()

posts = []
for row in rows:
    sentiment_obj = row[0]  # FactSocialSentiment
    author_handle = row[1]
    permalink = row[2]
    post_id = row[3]

    # Construct source URL based on platform
    if sentiment_obj.platform == "reddit":
        source_url = f"https://www.reddit.com{permalink}" if permalink else ""
    elif sentiment_obj.platform == "bluesky":
        post_uri_segment = post_id.split('/')[-1]
        source_url = f"https://bsky.app/profile/{author_handle}/post/{post_uri_segment}"
    else:
        source_url = ""

    # Classify sentiment
    if sentiment_obj.sentiment_compound >= 0.05:
        sentiment_label = "positive"
    elif sentiment_obj.sentiment_compound <= -0.05:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"

    posts.append(
        SocialPostPublic(
            social_post_key=sentiment_obj.social_post_key,
            platform=sentiment_obj.platform,
            post_text=sentiment_obj.post_text,
            created_at=sentiment_obj.created_at,
            engagement_score=sentiment_obj.engagement_score,
            sentiment_compound=sentiment_obj.sentiment_compound,
            sentiment_label=sentiment_label,
            source_url=source_url,
        )
    )

return SocialPostListResponse(
    posts=posts,
    total_count=len(posts),
    game_id=game_id,
)
```

### Frontend Design Specifications

**Sentiment Color Coding:**

| Sentiment Label | Text Color | Background Color | Icon |
|-----------------|------------|------------------|------|
| `positive` | green.600 | green.50 | 👍 or 🔥 |
| `neutral` | gray.600 | gray.50 | — |
| `negative` | red.600 | red.50 | 👎 or 😤 |

**Post Card Layout:**

```typescript
<Box
  p={3}
  bg={sentimentBgColor}
  borderLeft="3px solid"
  borderColor={sentimentBorderColor}
>
  <HStack justify="space-between">
    <HStack>
      <PlatformIcon platform={post.platform} /> {/* Reddit logo or Bluesky logo */}
      <Text fontSize="xs" color="gray.500">
        {formatDistanceToNow(post.created_at)} ago
      </Text>
    </HStack>
    <SentimentBadge sentiment={post.sentiment_label} />
  </HStack>

  <Text mt={2} fontSize="sm" noOfLines={3}>
    {post.post_text}
  </Text>

  <HStack mt={2} justify="space-between">
    <HStack spacing={4}>
      <HStack>
        <Icon as={FaHeart} boxSize={3} color="gray.500" />
        <Text fontSize="xs" color="gray.600">{post.engagement_score}</Text>
      </HStack>
    </HStack>
    <Link href={post.source_url} isExternal>
      <Button size="xs" variant="ghost" rightIcon={<ExternalLinkIcon />}>
        View Post
      </Button>
    </Link>
  </HStack>
</Box>
```

**Truncation and Expansion:**

- **Truncate long posts:** Use Chakra UI `<Text noOfLines={3}>` to limit to 3 lines
- **Future enhancement (Epic 8):** Click to expand full post text
- **For MVP:** Keep it simple - truncate with ellipsis, link to source for full text

**Platform Icons:**

```typescript
// Use react-icons
import { FaReddit } from 'react-icons/fa';
import { SiBluesky } from 'react-icons/si';  // May need custom SVG

function PlatformIcon({ platform }: { platform: 'reddit' | 'bluesky' }) {
  if (platform === 'reddit') {
    return <Icon as={FaReddit} color="orange.500" />;
  }
  if (platform === 'bluesky') {
    return <Icon as={SiBluesky} color="blue.400" />;
  }
  return null;
}
```

**Integration with GameCard (Story 4-9):**

```typescript
// frontend/src/components/GameCard.tsx

export function GameCard({ game }: { game: GamePublic }) {
  return (
    <Box>
      {/* Existing game info (from Story 4-9) */}
      <HStack justify="space-between">
        <TeamDisplay team={game.home_team} score={game.home_score} />
        <GameStatusBadge status={game.game_status} clock={game.game_clock} />
        <TeamDisplay team={game.away_team} score={game.away_score} />
      </HStack>

      {/* NEW: Social posts feed (Story 4-10) */}
      <SocialPostsFeed gameId={game.game_id} />
    </Box>
  );
}
```

### Performance Considerations

**Query Optimization:**

- Limit posts to top 10 by default (user can request more via `?limit=` param)
- Index on `(game_key, engagement_score DESC)` for fast sorting
- Denormalized design avoids expensive joins to raw tables

**Frontend Caching:**

```typescript
// frontend/src/hooks/useSocialPosts.ts

import { useQuery } from '@tanstack/react-query';
import { GameService } from '@/client';

export function useSocialPosts(gameId: string, limit: number = 10) {
  return useQuery({
    queryKey: ['social-posts', gameId, limit],
    queryFn: () => GameService.getGameSocialPosts({ gameId, limit }),
    staleTime: 5 * 60 * 1000,  // 5 minutes (social posts don't change rapidly)
    cacheTime: 15 * 60 * 1000, // 15 minutes
    enabled: !!gameId,          // Don't fetch if gameId is empty
  });
}
```

**Why 5-minute staleTime:**
- Social posts are historical (already happened)
- New posts arrive every 5-10 minutes (Reddit/Bluesky polling)
- No need to re-fetch every 60 seconds like game scores
- Reduces API load by 83% (60s → 300s)

**Lazy Loading (Optional Enhancement):**

```typescript
// Load social posts only when game card is expanded
// For MVP: Always load top 3-5 posts per game
// Future: Implement "Show more" button or accordion
```

### API Design Details

**Endpoint Specification:**

```
GET /api/v1/games/{game_id}/social-posts
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Max posts to return (1-50) |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/games/ncaam_401525257/social-posts?limit=5" \
  -H "accept: application/json"
```

**Example Response:**

```json
{
  "posts": [
    {
      "social_post_key": 12345,
      "platform": "reddit",
      "post_text": "Duke opens with 12-0 run, crowd silenced! This is going to be a long night for UNC.",
      "created_at": "2025-11-16T20:05:32Z",
      "engagement_score": 847,
      "sentiment_compound": 0.8516,
      "sentiment_label": "positive",
      "source_url": "https://www.reddit.com/r/CollegeBasketball/comments/abc123/duke_starts_hot/"
    },
    {
      "social_post_key": 12346,
      "platform": "bluesky",
      "post_text": "Bacot with monster dunk, UNC takes momentum back! What a game!",
      "created_at": "2025-11-16T20:12:18Z",
      "engagement_score": 623,
      "sentiment_compound": 0.7264,
      "sentiment_label": "positive",
      "source_url": "https://bsky.app/profile/hoopsfan.bsky.social/post/xyz789"
    }
  ],
  "total_count": 2,
  "game_id": "ncaam_401525257"
}
```

**Error Responses:**

```json
// 404 Not Found - Game ID doesn't exist
{
  "detail": "Game not found: ncaam_invalid"
}

// 400 Bad Request - Invalid limit parameter
{
  "detail": "limit must be between 1 and 50"
}
```

### Testing Strategy

**Backend Tests:**

```python
# backend/app/tests/api/test_games.py

def test_get_social_posts_success(client: TestClient, db_session: Session):
    """Test GET /api/v1/games/{game_id}/social-posts returns posts."""
    # Setup: Create test game, sentiment records
    game = create_test_game(db_session, game_id="ncaam_test123")
    create_test_sentiment_records(db_session, game_key=game.game_key, count=15)

    # Execute
    response = client.get(f"/api/v1/games/ncaam_test123/social-posts?limit=10")

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert len(data["posts"]) == 10  # Respects limit
    assert data["total_count"] == 10
    assert data["game_id"] == "ncaam_test123"
    assert data["posts"][0]["engagement_score"] >= data["posts"][1]["engagement_score"]  # Sorted DESC

def test_get_social_posts_no_posts(client: TestClient, db_session: Session):
    """Test endpoint returns empty list if no posts for game."""
    game = create_test_game(db_session, game_id="ncaam_test456")
    # No sentiment records created

    response = client.get(f"/api/v1/games/ncaam_test456/social-posts")

    assert response.status_code == 200
    data = response.json()
    assert len(data["posts"]) == 0
    assert data["total_count"] == 0

def test_get_social_posts_game_not_found(client: TestClient):
    """Test 404 error if game doesn't exist."""
    response = client.get("/api/v1/games/ncaam_invalid/social-posts")
    assert response.status_code == 404

def test_social_post_url_construction_reddit(db_session: Session):
    """Test Reddit URL constructed correctly."""
    # Create test post with Reddit permalink
    post = create_test_sentiment(
        db_session,
        platform="reddit",
        permalink="/r/CollegeBasketball/comments/abc123/title/"
    )

    # Query endpoint
    # ...

    # Verify
    assert result["source_url"] == "https://www.reddit.com/r/CollegeBasketball/comments/abc123/title/"

def test_social_post_url_construction_bluesky(db_session: Session):
    """Test Bluesky URL constructed correctly."""
    post = create_test_sentiment(
        db_session,
        platform="bluesky",
        author_handle="user.bsky.social",
        post_id="at://did:plc:abc.../app.bsky.feed.post/xyz789"
    )

    # Verify
    assert result["source_url"] == "https://bsky.app/profile/user.bsky.social/post/xyz789"

def test_sentiment_label_classification():
    """Test sentiment compound scores mapped to labels correctly."""
    assert classify_sentiment(0.8) == "positive"   # >= 0.05
    assert classify_sentiment(0.02) == "neutral"   # -0.05 to 0.05
    assert classify_sentiment(-0.6) == "negative"  # <= -0.05
```

**Frontend Tests:**

```typescript
// frontend/src/components/SocialPostsFeed.test.tsx

describe('SocialPostsFeed', () => {
  it('should render posts when data available', async () => {
    const mockPosts = [
      {
        social_post_key: 1,
        platform: 'reddit',
        post_text: 'Great game!',
        sentiment_label: 'positive',
        // ...
      },
    ];

    // Mock useSocialPosts hook
    vi.mocked(useSocialPosts).mockReturnValue({
      data: { posts: mockPosts, total_count: 1, game_id: 'test' },
      isLoading: false,
    });

    render(<SocialPostsFeed gameId="ncaam_test" />);

    expect(screen.getByText('Great game!')).toBeInTheDocument();
  });

  it('should hide section when no posts available', () => {
    vi.mocked(useSocialPosts).mockReturnValue({
      data: { posts: [], total_count: 0, game_id: 'test' },
      isLoading: false,
    });

    const { container } = render(<SocialPostsFeed gameId="ncaam_test" />);

    // Section should not render at all (null returned)
    expect(container.firstChild).toBeNull();
  });

  it('should apply correct sentiment colors', () => {
    const positiveSentiment = { sentiment_label: 'positive', /* ... */ };
    render(<SocialPostCard post={positiveSentiment} />);

    const badge = screen.getByText(/positive/i);
    expect(badge).toHaveStyle({ color: 'green.600' });
  });

  it('should render external link to source', () => {
    const post = {
      source_url: 'https://www.reddit.com/r/test',
      // ...
    };

    render(<SocialPostCard post={post} />);

    const link = screen.getByRole('link', { name: /view post/i });
    expect(link).toHaveAttribute('href', 'https://www.reddit.com/r/test');
    expect(link).toHaveAttribute('target', '_blank'); // Opens in new tab
  });
});
```

**Manual Testing:**

1. Navigate to dashboard with today's games
2. Find a game with social posts (check Dagster logs for sentiment pipeline completion)
3. Verify social posts section appears below game card
4. Click "View Post" link → Opens Reddit/Bluesky in new tab
5. Verify sentiment colors match post tone (positive = green, negative = red)
6. Test game without posts → Section should be hidden (no empty state text)
7. Test responsive design → Posts readable on mobile

### Database Query Verification

```sql
-- Verify social posts exist for today's games
SELECT
  fg.game_id,
  COUNT(fss.social_sentiment_key) as num_posts,
  AVG(fss.engagement_score) as avg_engagement,
  AVG(fss.sentiment_compound) as avg_sentiment
FROM fact_game fg
LEFT JOIN fact_social_sentiment fss ON fg.game_key = fss.game_key
WHERE fg.game_date = CURRENT_DATE
GROUP BY fg.game_id
ORDER BY num_posts DESC;

-- Check URL construction fields exist in staging table
SELECT
  platform,
  author_handle,
  permalink,
  post_id
FROM stg_social_post
LIMIT 5;

-- Verify no NULL source URL fields (data quality check)
SELECT
  COUNT(*) as null_permalinks
FROM stg_social_post
WHERE platform = 'reddit'
  AND (permalink IS NULL OR permalink = '');
-- Should be 0 or very few

SELECT
  COUNT(*) as null_handles
FROM stg_social_post
WHERE platform = 'bluesky'
  AND (author_handle IS NULL OR author_handle = '');
-- Should be 0
```

### Future Enhancements (Out of Scope)

**Story 4-10 focuses on basic post display. Future improvements:**

- **Pagination:** Load more posts with "Show more" button (Epic 8)
- **Real-time updates:** WebSocket or SSE for live post streaming (Epic 6)
- **Post filtering:** Filter by sentiment (show only positive/negative) (Epic 8)
- **Inline expansion:** Click to show full post text without external link (Epic 8)
- **Author profiles:** Link to user profiles, show avatars (Epic 11)
- **Comment threading:** Show top replies from Reddit threads (Epic 11)
- **Media preview:** Embed images/videos from posts (Epic 11)

---

## Acceptance Criteria Hints

### AC-4.10.1: Backend API Endpoint
- [ ] `GET /api/v1/games/{game_id}/social-posts` endpoint created
- [ ] Endpoint returns `SocialPostListResponse` with posts array
- [ ] Posts ordered by `engagement_score DESC` (most viral first)
- [ ] Query parameter `limit` supported (default 10, max 50)
- [ ] 404 error if game_id doesn't exist
- [ ] 400 error if limit invalid (< 1 or > 50)

### AC-4.10.2: Source URL Construction
- [ ] Reddit posts: URL format `https://www.reddit.com{permalink}`
- [ ] Bluesky posts: URL format `https://bsky.app/profile/{author_handle}/post/{post_id_segment}`
- [ ] All URLs valid (manually test 5-10 random posts)
- [ ] URLs open in new tab (target="_blank" in frontend)
- [ ] Handle edge cases: missing permalink (fallback URL), malformed URIs

### AC-4.10.3: Sentiment Classification
- [ ] `sentiment_compound >= 0.05` → label = "positive"
- [ ] `sentiment_compound <= -0.05` → label = "negative"
- [ ] `-0.05 < sentiment_compound < 0.05` → label = "neutral"
- [ ] Sentiment label included in API response
- [ ] Frontend applies correct color coding (green/red/gray)

### AC-4.10.4: Frontend Component Integration
- [ ] `SocialPostsFeed` component created
- [ ] Component integrated into `GameCard` below game info
- [ ] Section hidden if no posts (component returns null)
- [ ] No empty state text displayed (per user requirement)
- [ ] Section has heading "Top Moments" (matches mockup)

### AC-4.10.5: Post Card Display
- [ ] Post text displayed (truncated to 3 lines with ellipsis)
- [ ] Platform icon shown (Reddit orange, Bluesky blue)
- [ ] Timestamp displayed (relative format: "5 minutes ago")
- [ ] Engagement score shown with icon (heart or upvote)
- [ ] Sentiment badge color-coded (green/red/gray)
- [ ] "View Post" link with external icon

### AC-4.10.6: Performance
- [ ] API response time < 100ms for 10 posts
- [ ] Database query uses index on `(game_key, engagement_score DESC)`
- [ ] Frontend caches posts for 5 minutes (staleTime)
- [ ] Component lazy loads (doesn't block game card render)

### AC-4.10.7: Data Quality Validation
- [ ] No NULL source URLs in response
- [ ] No malformed URLs (all start with https://)
- [ ] Post text not empty (minimum 10 characters)
- [ ] Created_at timestamps valid (not future dates)
- [ ] Engagement scores positive integers (>= 0)

### AC-4.10.8: Accessibility
- [ ] External links have aria-label: "View post on Reddit" / "View post on Bluesky"
- [ ] Sentiment badges have aria-label: "Positive sentiment" / etc.
- [ ] Color is not the only indicator (text labels present)
- [ ] Keyboard navigation works (tab through "View Post" links)

### AC-4.10.9: Empty State Behavior
- [ ] Section completely hidden if `posts.length === 0`
- [ ] No "No posts available" message displayed
- [ ] No visual gap in UI (section removed from layout)
- [ ] Verified with game that has no social posts

### AC-4.10.10: TypeScript Client Generation
- [ ] Run `npm run generate-client` after backend endpoint added
- [ ] New `GameService.getGameSocialPosts()` method available
- [ ] TypeScript types match API response schema
- [ ] No TypeScript errors in frontend code

---

## Dependencies

**Required (Must be complete):**
- ✅ Story 4-5: Calculate Sentiment Analysis (fact_social_sentiment table exists)
- ✅ Story 4-4: Transform Social Posts (stg_social_post table exists)
- ✅ Story 4-9: Game Card UI Design (component to integrate with)

**Nice to Have (Can proceed without):**
- Story 4-7: Orchestration & Data Management (more posts available)
- Story 5-1: Excitement scoring (can add sentiment-based sorting later)

---

## Files Modified

**Backend:**
- `backend/app/api/routes/games.py` - Add `GET /games/{id}/social-posts` endpoint
- `backend/app/models/social.py` - Add `SocialPostPublic`, `SocialPostListResponse` schemas
- `backend/app/tests/api/test_games.py` - Add endpoint tests

**Frontend:**
- `frontend/src/components/SocialPostsFeed.tsx` - NEW: Feed component
- `frontend/src/components/SocialPostCard.tsx` - NEW: Individual post card
- `frontend/src/components/SentimentBadge.tsx` - NEW: Sentiment indicator
- `frontend/src/components/GameCard.tsx` - MODIFIED: Integrate posts feed
- `frontend/src/hooks/useSocialPosts.ts` - NEW: TanStack Query hook
- `frontend/src/client/*` - AUTO-GENERATED: Update after backend changes

**Tests:**
- `frontend/src/components/SocialPostsFeed.test.tsx` - NEW
- `backend/app/tests/api/test_games.py` - Add social posts tests

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missing permalinks in Reddit data | Low | Medium | Fallback URL construction, data quality checks |
| Bluesky post URI parsing fails | Medium | Medium | Handle malformed URIs gracefully, log errors |
| Too many posts slows page load | Low | Low | Limit to 10 posts by default, implement pagination later |
| Sentiment colors not accessible | Medium | Low | Add text labels, meet WCAG AA contrast |
| External links open in same tab | Very Low | Low | Enforce target="_blank" in all Link components |

**Overall Risk:** **LOW** - Well-defined data model, clear API design.

---

## Success Metrics

- ✅ Social posts visible for games with sentiment data (>80% of live games)
- ✅ External links valid (>95% success rate when clicked)
- ✅ Sentiment colors intuitive (user can distinguish positive/negative at glance)
- ✅ Empty state handled gracefully (no UI errors for games without posts)
- ✅ API response time < 100ms (fast enough for dashboard)

---

## References

- Mockups: `docs/gamepulse-1-desktop.png`, `docs/gamepulse-1-mobile.png`
- Story 4-5: [Calculate Sentiment Analysis](4-5-calculate-sentiment.md)
- Story 4-9: [Enhanced Game Card UI Design](4-9-game-card-ui-design.md)
- Backend Models: `backend/app/models/social.py` (FactSocialSentiment, StgSocialPost)
- Frontend Hook: `frontend/src/hooks/useSocialPosts.ts` (to be created)
