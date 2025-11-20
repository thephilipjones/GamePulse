# GamePulse - Product Requirements Document

**Author:** Philip
**Date:** 2025-11-07
**Version:** 1.0

---

## Executive Summary

GamePulse is a real-time sports analytics platform that transforms how college basketball fans experience peak NCAA season. By integrating live game data with Reddit community signals, GamePulse solves the choice paralysis problem during March Madness when 50+ games happen simultaneously.

**The Core Innovation:** GamePulse creates a daily sports narrative from community signals - surfacing both real-time excitement ("what's happening NOW that I should watch") and retrospective discovery ("what happened today while I was working"). It's not a score tracker; it's a "story of the day" engine that identifies which games mattered and which moments within those games created community explosions.

**Dual Purpose:**
1. **Portfolio Showcase**: Demonstrates production-ready data engineering skills - multi-source streaming integration, time-series analysis, AWS infrastructure, and clean visualization UI - designed to impress hiring managers
2. **Genuine User Value**: Solves a real problem Philip experiences as a college basketball fan and can share with friends during March Madness

Built with constraint-aware intelligence: instead of streaming millions of Reddit comments (API nightmare), GamePulse tracks post-level patterns. When a 15-seed hits a buzzer beater, the community creates the highlight reel through post titles and upvote velocity - GamePulse surfaces those moments efficiently.

### What Makes This Special

**The Magic Moment:** Philip opens GamePulse after a Saturday of work during March Madness. Instead of scrolling dozens of box scores, he instantly sees "the games that mattered today" with excitement indicators showing which were legendary. He clicks into the top game and sees the Reddit posts that tell the story: "UNBELIEVABLE BUZZER BEATER BY 15-SEED OVER DUKE - 92-91" (8.2k upvotes). In 30 seconds, he knows exactly what happened and can watch the highlights with full context.

**The Dual Experience:**
- **Real-time**: Glanceable dashboard shows excitement spikes across live games - when one lights up, you know something crazy just happened
- **Retrospective**: Daily narrative of "games that mattered" + "moments that mattered" within each game, synthesized from Reddit community signals

**The Portfolio Angle:** This isn't just a sports app - it's a demonstration of modern data engineering competency wrapped in an engaging use case. Hiring managers see: multi-source integration, streaming data pipelines, time-series storage, sentiment analysis, cloud infrastructure, and user-facing visualization - all within AWS free tier constraints.

---

## Project Classification

**Technical Type:** Web Application + Data Engineering Pipeline
**Domain:** Sports Analytics / Data Science
**Complexity:** Medium (Data pipeline complexity with straightforward web UI)

**Project Architecture:**

This is a **data-first web application** - the core value is in the data engineering pipeline, not complex UI interactions. It combines:

1. **Data Engineering Pipeline** (Primary Focus)
   - Multi-source data integration (NCAA API + Reddit API)
   - Real-time streaming data processing
   - Time-series data storage and aggregation
   - Sentiment analysis and excitement scoring algorithms
   - Scheduled polling jobs optimized for API rate limits

2. **Web Application Frontend** (Supporting Component)
   - Single-page React dashboard for data visualization
   - Mobile-responsive timeline interface
   - Real-time updates via polling (10-15 min intervals)
   - Minimal user interaction - primarily read-only views

**Domain Characteristics:**

**Sports Analytics** is a well-established domain with accessible APIs and clear data patterns. Unlike healthcare or fintech, it requires no regulatory compliance, specialized certifications, or domain-specific expertise. The complexity lies in:
- Efficient multi-source data synchronization
- Sentiment analysis accuracy on social media text
- Time-series performance at scale
- API rate limit optimization

**Key Technical Challenges:**
- Matching Reddit posts to specific games without explicit tagging
- Calculating meaningful "excitement scores" from engagement metrics
- Handling NCAA tournament scale (32+ simultaneous games)
- Operating within AWS free tier cost constraints
- Designing for March Madness peak load (50+ games/day)

**Portfolio Context:**

This project is explicitly designed as a **data engineering portfolio piece** targeting:
- Data Engineer roles at tech companies
- Backend/Platform Engineer positions with data focus
- Interviews requiring technical depth demonstrations

Success is measured by interview callback rate and code review impressions, not user growth or revenue metrics.

---

## Success Criteria

### Primary Success: Portfolio Impact (Interview-Driven)

GamePulse's primary "customer" is the data engineering hiring manager reviewing Philip's work during active job interviews. Success metrics:

**Immediate Demo Readiness:**
- ✅ **Working demo within 2-3 weeks** - Philip is actively interviewing NOW, not waiting for March Madness 2026
- ✅ **Live public URL** that works reliably during interview screen shares
- ✅ **Code review ready** - Clean, documented codebase that impresses during technical deep-dives
- ✅ **Narrative clarity** - Can articulate architectural decisions and trade-offs in 5 minutes

**Technical Competency Demonstration:**

Must prove mastery of modern data engineering patterns:

1. **Dual Processing Paradigms** (CRITICAL)
   - **Streaming**: Real-time Reddit post ingestion, live game event processing
   - **Batch**: Daily aggregations, historical analysis, excitement score recalculations
   - Portfolio value: Shows understanding of when to use each paradigm

2. **Multi-Source Integration**
   - NCAA API + Reddit API synchronization with different refresh cadences
   - Demonstrates data pipeline orchestration skills

3. **Time-Series Expertise**
   - QuestDB optimization for high-velocity sports data
   - Shows modern database selection reasoning

4. **Cloud Infrastructure**
   - AWS deployment within free tier constraints
   - Production-ready architecture (monitoring, error handling, graceful degradation)

5. **Clear Trade-Off Documentation**
   - Why 10-15 min polling (API limits + free tier) vs real-time streaming
   - Articulates upgrade path: "With Kafka + paid APIs, this becomes <1min latency"
   - Shows production thinking constrained by portfolio budget

**Interview Impact Signals:**
- Hiring manager asks follow-up technical questions (engaged, not just reviewing)
- "Can you walk me through your architecture?" → Leads to deeper discussion
- Callback rate improvement vs previous portfolio projects
- Offers specifically mentioning "impressive data engineering project"

### Secondary Success: Technical Performance

Measurable engineering quality within free tier constraints:

**Operational Constraints:**
- **Cost**: ≤$10/month operational cost
  - Acceptable to exceed free tier for quality improvements
  - Budget allows paid streaming services, better cloud tier if needed
  - Demonstrates real-world cost/quality trade-off thinking
- **Freshness**: As real-time as services allow
  - 10-15 min polling acceptable for rate-limited APIs
  - **MUST include true streaming component** for portfolio demonstration
  - If existing sources (NCAA, Reddit) are polling-only, add streaming source (sports WebSocket, betting odds, etc.)
- **Performance**: Dashboard loads in <3 seconds on mobile connection
- **API Compliance**: Stays within rate limits without errors
- **Scale**: Quality over coverage
  - **March Madness reality**: 5 concurrent games max (16 games in peak day)
  - **Regular season**: 50 games/day but most meaningless
  - **Priority**: High-quality deep data on 5-10 most interesting games > shallow coverage of all 50
  - Better to richly track top games than lightly track everything

**Reliability Metrics:**
- **Uptime**: 95%+ during demo periods (allowed downtime for maintenance/iteration)
- **Error Handling**: Graceful degradation when APIs fail (cached data fallback)
- **Data Quality**: <5% missing game events due to API failures

### Tertiary Success: User Value Validation

Proves this solves a real problem, not just a technical exercise:

**Accuracy:**
- Excitement algorithm identifies "most exciting" games with 70%+ accuracy
  - Validated against post-game Reddit consensus and ESPN highlights
  - Buzzer beaters and major upsets flagged within 15 minutes of occurrence

**Personal Use Test:**
- Philip actually uses GamePulse during NCAA season
- Provides genuine value: "This helped me find the right game to watch"
- Shareable with friends who find it useful

**Retrospective Value:**
- "What happened today" summary accurately captures daily narrative
- Top Reddit posts for each game tell the story effectively

### Critical Milestones

**Week 1-2: Core Pipeline + Basic UI**
- Data ingestion working for both sources
- QuestDB storage and basic queries functional
- Simple React dashboard showing game list

**Week 3: Demo Ready**
- Excitement algorithm tuned and working
- AWS deployment live and accessible
- Documentation complete (README, architecture decisions)
- Can confidently demo during interviews

**Bonus (March 2026): Peak Load Validation**
- Fully functional during March Madness tournament
- Handles 32+ simultaneous games during peak rounds
- Real-world traffic validation at scale

**Success Measured By:**
- Not revenue or user growth
- **Interview callbacks and technical discussion depth**
- Code review impressions from hiring managers
- Job offer quality and compensation

---

## Product Scope

### MVP - Minimum Viable Product (2-3 Week Demo Target)

**Philosophy: Data-first, UI as time allows**

Start with robust data pipeline and time-series storage, then build UI to visualize. Core value is demonstrating data engineering competency - pixel-perfect UI is secondary.

**Core Data Pipeline (CRITICAL - Must Demonstrate Both Paradigms):**

1. **Streaming Data Source** (Real-time WebSocket)
   - **Betfair Exchange API + flumine framework** for betting odds streaming
   - True WebSocket streaming (not polling) - demonstrates streaming architecture competency
   - Free delayed API key (3-minute latency acceptable for portfolio)
   - Python-native flumine framework (1-2% CPU overhead, event-driven)
   - Betting odds → Converted to implied win probability for games
   - Deploy to AWS t2.micro for 24/7 streaming ingestion

2. **Batch Data Sources** (Scheduled Polling)
   - **NCAA API (henrygd/ncaa-api)**: Game schedules, live scores, final results (10-15 min polling)
   - **Reddit API (PRAW)**: Post-level tracking from r/CollegeBasketball (10-15 min polling, 100 QPM limit)
   - Demonstrates when batch processing is appropriate vs streaming

3. **Time-Series Storage & Processing**
   - **QuestDB**: High-velocity sports data storage optimized for time-series queries
   - Excitement score calculations over time (enables sparkline charts)
   - Aggregations: Daily game summaries, historical trends, peak moment detection
   - Demonstrates modern database selection reasoning

4. **Multi-Source Data Fusion**
   - Match Reddit posts to specific games (fuzzy matching on team names, timing)
   - Correlate betting odds shifts with Reddit excitement spikes
   - Timestamp normalization across sources (game time vs wall clock time)
   - Demonstrates data integration orchestration skills

**Core Features (Demo-Ready MVP):**

1. **Game Dashboard with Excitement Tracking**
   - Display 5-10 most interesting games from today's NCAA schedule
   - Focus on quality (deep data on top games) over coverage (shallow data on all 50 games)
   - Game cards showing: teams, scores, game status (live/final), excitement score
   - Excitement score badge (0-100 scale, color-coded: red = high, orange = medium)
   - Live status indicators: "LIVE 2:34 2nd Half" vs "Final"

2. **Excitement Timeline Visualization**
   - Sparkline chart showing excitement score evolution throughout game
   - Requires continuous time-series data collection (not just snapshots)
   - Visual peaks indicate key moments (buzzer beaters, comebacks, etc.)
   - Demonstrates time-series query and visualization competency

3. **Top Moments from Reddit**
   - Display top 3-5 Reddit posts for each game
   - Post title, upvote count, comment count, timestamp
   - Timestamped to game time: "10:00 1st Half", "0:00 2nd Half"
   - Link to original Reddit thread
   - Provides narrative context: "What happened in this game?"

4. **Excitement Score Algorithm**
   - Multi-factor calculation combining:
     - Reddit post velocity (posts/minute during game)
     - Reddit engagement (upvotes, comments, awards)
     - Sentiment analysis (VADER on post titles)
     - Betting odds volatility (large odds shifts indicate significant events)
     - Game context (close score, upset potential, rivalry, tournament importance)
   - Simple v1 algorithm, can refine post-launch
   - Demonstrates data science / ML capability

5. **Basic Web UI (React SPA)**
   - Single-page dashboard matching mockup vision (as time allows)
   - Mobile-responsive layout
   - Auto-refresh every 10-15 minutes (polling, not WebSocket to frontend)
   - Dark theme matching mockups
   - Team color accents in game cards
   - **Date navigation** (Prev/Next day controls): Defaults to yesterday's games to surface social content
     - 💡 **Product Discovery**: Testing revealed yesterday's completed games have rich social posts and sentiment, while today's upcoming games have none. This feature is critical for delivering core user value.
   - **Simplification acceptable**: Basic list view works if timeline charts are complex

**Acceptable MVP Simplifications (If Timeline Tight):**

- ⚠️ **UI Polish**: Basic functional UI > pixel-perfect mockup
- ⚠️ **Excitement Algorithm**: Simple multi-factor formula (can tune post-launch)
- ⚠️ **Coverage**: 5-10 top games with rich data > all 50 games with shallow data
- ⚠️ **Win Probability Chart**: Optional if time-constrained (betting odds streaming is primary goal)

**Must NOT Simplify:**

- ✅ **Dual paradigms**: Both streaming (Betfair) and batch (Reddit/NCAA) data sources
- ✅ **Time-series storage**: QuestDB with historical data for sparkline charts
- ✅ **Multi-source integration**: At least 2 sources synchronized
- ✅ **Working demo URL**: Deployed to AWS and accessible during interviews
- ✅ **Clean code**: Documented, production-ready architecture

### Growth Features (Post-MVP)

**Enhanced after demo-ready milestone achieved:**

1. **Win Probability Visualization**
   - Overlay win probability curve (from betting odds) on excitement timeline
   - Shows correlation: "Excitement spike when underdog took lead (odds shifted 30%)"
   - Demonstrates advanced data fusion and visualization

2. **Historical Data & Trends**
   - ✅ **Basic date navigation** (Prev/Next day controls) - **IMPLEMENTED in MVP** (Story 4-11)
   - 📅 Date picker / calendar widget to browse past games (advanced enhancement)
   - Season-long excitement trends
   - "Most exciting games of the season" leaderboard
   - Demonstrates batch processing and historical analysis

3. **Enhanced Reddit Integration**
   - Top 1-3 comments from each post (not just post titles)
   - Sentiment analysis on comments for deeper narrative
   - Track multiple subreddits (team-specific + r/CollegeBasketball)

4. **Advanced Excitement Algorithm**
   - Machine learning model trained on historical "exciting game" labels
   - Predictive excitement scores before games start (based on matchup factors)
   - A/B test algorithm variants

5. **UI Enhancements**
   - Game detail drill-down pages
   - Advanced filtering (by conference, ranking, tournament round)
   - User preferences and saved teams
   - Push notifications for high-excitement spikes
   - Refined mobile experience

6. **Scale Improvements**
   - Upgrade Betfair to Live API key (£299 for real-time, <1 second latency)
   - Expand to full 50-game coverage with quality maintained
   - Add caching layer (Redis) for faster dashboard loads
   - Implement true frontend WebSocket updates (not polling)

### Vision Features (Future Possibilities)

**Demonstrates growth thinking and production upgrade path:**

1. **Multi-Sport Expansion**
   - NBA, NFL, March Madness expansion
   - Unified dashboard across sports
   - Sport-agnostic data abstraction layer (designed for this in MVP)

2. **Community Features**
   - User accounts and authentication
   - Personalized feeds based on team preferences
   - Social sharing: "Check out this crazy game!"
   - Crowdsourced excitement ratings validation

3. **Advanced Analytics**
   - Predictive models: "This game will be exciting" based on pre-game factors
   - Correlation analysis: Reddit sentiment vs betting market vs final score margin
   - Historical trend analysis: "Best rivalries by average excitement"
   - Excitement score accuracy validation against post-game consensus

4. **Production-Scale Infrastructure**
   - Migration from simple queues → Kafka or Kinesis for true event streaming
   - Microservices architecture (data ingestion, processing, API, frontend as separate services)
   - Kubernetes deployment for auto-scaling
   - Real-time ML inference for excitement scoring
   - Comprehensive monitoring, alerting, and observability (Datadog, Grafana)

5. **Monetization (If Real Product)**
   - Premium features (real-time updates, advanced filtering, notifications)
   - API access for third-party developers
   - Affiliate partnerships with sports streaming services
   - Premium betting insights integration

**Scope Boundaries:**

**OUT OF SCOPE for MVP:**
- ❌ User accounts or authentication
- ❌ Betting integration beyond odds data (no wagering)
- ❌ Video highlights integration
- ❌ Native mobile apps (web-responsive sufficient)
- ❌ Multi-sport beyond NCAA basketball
- ❌ Real-time frontend updates via WebSocket (polling sufficient)
- ❌ Advanced ML models (simple algorithms sufficient)
- ❌ Historical data backfill beyond current season

---

## Data Pipeline & Web App Architecture

### Data Model (QuestDB Schema)

**Dimensional Tables (Slow-Changing, Updated Weekly/Monthly):**

```sql
-- Teams dimensional table
CREATE TABLE dim_teams (
  team_id SYMBOL,
  team_name STRING,
  team_abbr STRING,  -- "DU", "UNC", "UK"
  conference_id SYMBOL,
  division STRING,  -- Generic: "ACC", "Big Ten" in NCAAM; "NFC East" in NFL
  aliases STRING[],  -- Common name variations: ["Duke", "Blue Devils", "DU"]
  primary_color STRING,  -- "#003087" for team color UI accents
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) timestamp(updated_at);

-- Players dimensional table (for player mention matching)
CREATE TABLE dim_players (
  player_id SYMBOL,
  player_name STRING,
  team_id SYMBOL,
  jersey_number INT,
  position STRING,
  aliases STRING[],  -- ["Zion", "Zion Williamson", "Z. Williamson"]
  active BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) timestamp(updated_at);

-- Conferences/Divisions (for rivalry detection)
CREATE TABLE dim_conferences (
  conference_id SYMBOL,
  conference_name STRING,
  sport STRING,  -- "NCAA_MBB", "NFL", etc. (future multi-sport)
  rivalry_factor DOUBLE,  -- Multiplier for excitement when same conference
  created_at TIMESTAMP
) timestamp(created_at);
```

**Fact Tables (High-Frequency, Real-Time/Near-Real-Time):**

```sql
-- Games table
CREATE TABLE games (
  game_id SYMBOL,
  game_date TIMESTAMP,
  home_team_id SYMBOL,  -- FK to dim_teams
  away_team_id SYMBOL,
  home_score INT,
  away_score INT,
  game_status SYMBOL,  -- scheduled, live, halftime, final
  game_clock STRING,  -- "2:34 2nd Half"
  game_start_time TIMESTAMP,  -- Actual tipoff time (for time mapping)
  game_end_time TIMESTAMP,
  venue STRING,
  is_rivalry BOOLEAN,  -- Same conference, historical rivalry
  is_tournament BOOLEAN,  -- March Madness vs regular season
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) timestamp(updated_at) PARTITION BY DAY;

-- Excitement scores (time-series)
CREATE TABLE excitement_scores (
  game_id SYMBOL,
  timestamp TIMESTAMP,
  score DOUBLE,  -- 0-100
  reddit_velocity DOUBLE,
  reddit_engagement INT,
  sentiment_score DOUBLE,
  odds_volatility DOUBLE,
  game_context_factor DOUBLE,
  rivalry_bonus DOUBLE,  -- Boost for same-conference games
  created_at TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY;

-- Reddit posts (two types: Game Threads vs Moment Posts)
CREATE TABLE reddit_posts (
  post_id SYMBOL,
  game_id SYMBOL,
  post_type SYMBOL,  -- "game_thread", "moment", "pre_game", "post_game"
  title STRING,
  author STRING,
  upvotes INT,
  comments_count INT,
  awards_count INT,
  post_time TIMESTAMP,
  game_time_context SYMBOL,  -- "pre_game", "1st_half", "halftime", "2nd_half", "post_game"
  estimated_game_clock STRING,  -- Inferred game time if applicable
  time_mapping_confidence DOUBLE,  -- How confident are we in game clock mapping?
  url STRING,
  match_method STRING,  -- "team_name", "player_mention", "game_thread_title"
  match_confidence DOUBLE,
  is_game_thread BOOLEAN,  -- TRUE for official game threads (comments matter)
  engagement_score DOUBLE,  -- (upvotes * 1.0) + (comments * 0.5) + (awards * 2.0)
  created_at TIMESTAMP
) timestamp(created_at) PARTITION BY DAY;

-- Game thread comments (only for official game threads)
CREATE TABLE game_thread_comments (
  comment_id SYMBOL,
  post_id SYMBOL,  -- FK to reddit_posts where is_game_thread=TRUE
  game_id SYMBOL,
  comment_text STRING,
  author STRING,
  upvotes INT,
  comment_time TIMESTAMP,
  estimated_game_clock STRING,
  sentiment_score DOUBLE,  -- VADER sentiment
  created_at TIMESTAMP
) timestamp(created_at) PARTITION BY DAY;

-- Betting odds (streaming source)
CREATE TABLE betting_odds (
  game_id SYMBOL,
  timestamp TIMESTAMP,
  market_type SYMBOL,  -- moneyline, spread, total
  home_odds DOUBLE,
  away_odds DOUBLE,
  implied_home_prob DOUBLE,
  implied_away_prob DOUBLE,
  volume INT,
  odds_shift_5min DOUBLE,  -- Change in implied prob over last 5 minutes
  odds_volatility_score DOUBLE,  -- Calculated volatility metric
  created_at TIMESTAMP
) timestamp(timestamp) PARTITION BY HOUR;
```

### Data Pipeline Architecture (Priority-Ordered for MVP)

**Philosophy: Deploy Early, Iterate Fast**

Get a working deployed system ASAP, even if basic. Incremental deployment beats feature-complete-but-not-deployed.

---

**Phase 1: Minimal Viable Pipeline + Deployment (Week 1)**

**Goal**: Working live demo by end of week 1, even if simple.

1. **Dimensional Data Setup (Minimal)**
   - Hardcode top 20 NCAA teams in JSON config → `dim_teams`
   - Basic conference data → `dim_conferences`
   - Skip players table initially (add in Phase 2)
   - **Rationale**: Manual curated list faster than scraping; enough for demos

2. **NCAA API Batch Ingestion (Basic)**
   - Scheduled job: Every 15 minutes
   - Fetch today's games + scores
   - Write to `games` table
   - Simple rivalry detection (same conference = true)
   - **Simplification**: No advanced error handling yet, just basic retry

3. **Reddit API Batch Ingestion (Basic)**
   - Scheduled job: Every 15 minutes
   - Fetch r/CollegeBasketball new posts
   - **SIMPLE** matching: Exact team name in title (case-insensitive)
   - Write to `reddit_posts` table
   - **Defer**: Fuzzy matching, player mentions, confidence scoring

4. **Excitement Score (v0.1 - Simplified)**
   - Basic formula: `excitement = (reddit_post_count * 10) + (score_margin_factor * 5)`
   - No sentiment analysis yet (add VADER in Phase 2)
   - No time mapping (just use raw timestamps)
   - **Goal**: Something that produces numbers, can refine later

5. **Backend API (Minimal)**
   - FastAPI with 2 endpoints:
     - `GET /api/games/today` - Returns games with basic excitement scores
     - `GET /api/health` - System status
   - **Defer**: `/moments`, `/timeline` details endpoints until Phase 2

6. **Frontend (Bare Minimum)**
   - Single React page
   - List of games (no cards yet, just rows)
   - Show: teams, scores, excitement score
   - **Defer**: Sparkline charts, dark theme, mobile polish

7. **Deployment (CRITICAL - Do This Week 1)**
   - Docker Compose setup for all services
   - Deploy to AWS EC2 t2.micro
   - GitHub Actions: Push to `main` → auto-deploy
   - **Result**: Live public URL by end of week 1
   - **Acceptable**: System might have bugs, data might be rough - that's fine!

**Week 1 Milestone**: You can share a URL in an interview that shows live NCAA games with excitement scores, even if simple.

---

**Phase 2: Refine Batch + Add Streaming (Week 2)**

**Goal**: Improve data quality and add streaming for portfolio demonstration.

1. **Refine Reddit Matching**
   - Add fuzzy team name matching (fuzzywuzzy library)
   - Basic player mention detection (check against player names list)
   - Add confidence scoring
   - Game thread detection ("[Game Thread]" title format)
   - Distinguish game threads vs moment posts

2. **Time Mapping Logic**
   - Implement wall-clock → game-clock heuristic
   - Add game_time_context classification (pre/live/post)
   - Store estimated_game_clock and confidence

3. **Enhanced Excitement Score (v0.2)**
   - Add VADER sentiment analysis on post titles
   - Add rivalry bonus for conference matchups
   - Add game context factors (close score, time remaining)
   - Configurable weights in JSON file
   - Calculate time-series (store scores every 15 min)

4. **Betfair Streaming Integration**
   - Set up flumine + Betfair delayed API key
   - WebSocket connection for betting odds
   - Write to `betting_odds` table
   - Calculate odds volatility
   - Incorporate into excitement score
   - **Demonstrates**: Dual paradigms (batch + streaming)

5. **API Expansion**
   - Add `GET /api/games/{game_id}/moments` endpoint
   - Add `GET /api/games/{game_id}/timeline` endpoint
   - Return structured data for frontend enhancements

6. **Frontend Improvements**
   - Game cards with styling (dark theme)
   - Sparkline charts for excitement timeline
   - Top moments expandable sections
   - Mobile-responsive layout
   - Team color accents

**Week 2 Milestone**: Refined demo with streaming data source, better matching, and polished UI.

---

**Phase 3: Polish & Testing (Week 3)**

**Goal**: Production-quality code and comprehensive testing.

1. **Testing Suite**
   - Unit tests for matching logic
   - Unit tests for excitement calculations
   - Integration tests for API endpoints
   - E2E tests with simulated game data
   - **Target**: >70% coverage

2. **Error Handling & Resilience**
   - Exponential backoff retry logic
   - Graceful degradation when APIs fail
   - Cached data fallback
   - Stale data warnings in UI

3. **Documentation**
   - README with architecture overview
   - API documentation (OpenAPI/Swagger)
   - Deployment guide
   - Architecture decision records (ADRs)
   - **Why QuestDB?** **Why post-level vs comments?** **Why 10-15 min polling?**

4. **Performance Optimization**
   - React.memo for components
   - Query optimization in QuestDB
   - API response caching
   - Frontend bundle size optimization

5. **Monitoring (Basic MVP)**
   - Enhanced `/api/health` endpoint with detailed metrics
   - Basic logging to stdout (captured by Docker)
   - **Defer**: Full observability stack (Prometheus/Grafana) to Growth phase

**Week 3 Milestone**: Interview-ready demo with clean code, tests, and comprehensive documentation.

---

**Growth Phase (Post-MVP):**

1. **Game Thread Comments**
   - Add `game_thread_comments` table
   - Poll comments from game threads
   - Sentiment analysis on comments
   - Comment velocity as excitement signal

2. **Advanced Time Mapping**
   - ML model trained on labeled data
   - Higher confidence game clock estimation

3. **Player Dimension**
   - Add `dim_players` table with full rosters
   - Player mention matching in Reddit posts
   - "Zion dunks" → Match to Duke vs UNC game

4. **Historical Data**
   - Date picker for past games
   - Season leaderboards
   - Excitement trends over time

5. **Win Probability Visualization**
   - Overlay win probability from betting odds on excitement chart
   - Show correlation between odds shifts and Reddit spikes

6. **Full Observability Stack**
   - Prometheus + Grafana for metrics
   - CloudWatch or ELK for logging
   - PagerDuty/SNS for alerting
   - dbt or Great Expectations for data quality

### Backend API Specification (FastAPI)

**Core Endpoints for MVP:**

```
GET /api/games/today
- Returns: List of today's games with current excitement scores
- Query params: ?limit=10 (default), ?sort=excitement_desc
- Response: [
    {
      game_id: "401234567",
      home_team: {id: "du", name: "Duke", color: "#003087"},
      away_team: {id: "unc", name: "UNC", color: "#7BAFD4"},
      home_score: 78,
      away_score: 81,
      status: "final",
      game_clock: null,
      excitement_score: 94,
      is_rivalry: true,
      excitement_trend: [{t: "...", score: 85}, ...]  // Last 10 data points
    }
  ]

GET /api/games/{game_id}/timeline
- Returns: Full excitement score time-series for sparkline chart
- Response: {
    game_id: "401234567",
    timeline: [{timestamp: "2025-11-07T19:00:00Z", score: 45}, ...],
    win_probability: [{timestamp: "...", home_prob: 0.52}, ...]  // Growth feature
  }

GET /api/games/{game_id}/moments
- Returns: Top Reddit posts (moment posts + game thread)
- Query params: ?type=all|moment|game_thread
- Response: {
    game_id: "401234567",
    game_thread: {
      post_id: "xyz",
      title: "[Game Thread] Duke vs UNC",
      url: "...",
      comments_count: 1247,
      top_comments: [...]  // Growth feature
    },
    moments: [
      {
        post_id: "abc123",
        title: "Duke opens with 12-0 run, crowd silenced",
        upvotes: 342,
        comments: 87,
        game_time_context: "1st_half",
        estimated_game_clock: "10:00 1st Half",
        time_mapping_confidence: 0.85,
        url: "https://reddit.com/..."
      }
    ]
  }

GET /api/games/{game_id}/details
- Returns: Comprehensive game details
- Includes: game info, excitement timeline, top moments, odds history
- Response: Aggregates data from multiple tables

GET /api/teams
- Returns: List of all teams with metadata
- Response: [{team_id, name, conference, colors}, ...]

GET /api/health
- Returns: System health and data freshness
- Response: {
    status: "healthy",
    last_update: "2025-11-07T14:32:00Z",
    sources: {
      betfair: {status: "connected", lag_ms: 150},
      ncaa_api: {status: "ok", last_poll: "...", games_tracked: 8},
      reddit_api: {status: "ok", rate_limit_remaining: 87, posts_ingested: 342}
    },
    database: {status: "ok", row_counts: {...}}
  }
```

**Growth/Optional Endpoints:**

```
GET /api/games/{game_id}/comments
- Returns: Game thread comments with sentiment scores
- Pagination support
- Growth feature: Requires comment ingestion pipeline

GET /api/leaderboard/excitement
- Returns: Most exciting games of the season
- Query params: ?timeframe=today|week|season
- Growth feature: Historical data required

GET /api/teams/{team_id}/games
- Returns: All games for specific team
- Growth feature: Historical browsing
```

### Frontend Architecture (React + TypeScript)

**Component Structure:**

```
src/
├── components/
│   ├── GameCard.tsx           // Individual game display with excitement badge
│   ├── ExcitementTimeline.tsx // Sparkline chart component
│   ├── TopMoments.tsx         // Reddit posts list
│   ├── LoadingSkeleton.tsx    // Loading state UI
│   └── ErrorBoundary.tsx      // Error handling wrapper
├── pages/
│   ├── Dashboard.tsx          // Main page: today's games
│   └── (Growth: GameDetail.tsx, HistoricalView.tsx)
├── hooks/
│   ├── useGames.ts            // React Query hook for /api/games/today
│   ├── useGameTimeline.ts     // Fetch excitement timeline
│   └── usePolling.ts          // Auto-refresh every 10-15 min
├── utils/
│   ├── api.ts                 // Axios client with retry logic
│   ├── formatters.ts          // Date/time/score formatting
│   └── colors.ts              // Team color utilities
└── App.tsx
```

**Key User Flows:**

1. **Dashboard Load**
   - Fetch `/api/games/today`
   - Display game cards sorted by excitement_score descending
   - Show loading skeletons during fetch
   - Auto-refresh every 10-15 minutes using React Query polling

2. **View Excitement Timeline**
   - Embedded sparkline in each game card (lightweight)
   - Hover tooltip shows timestamp + score
   - Data comes from `excitement_trend` in `/api/games/today` response

3. **View Top Moments**
   - Expandable section in game card
   - Default: Show top 3 moments collapsed
   - Click "Show more" → expand to 5-10 moments
   - Each moment links to Reddit (opens new tab)

4. **Error States**
   - API failure → Show cached data + "Last updated X min ago" banner
   - No games today → "No games scheduled" message
   - Stale data (>30 min old) → Yellow warning indicator

**Performance Optimizations:**

- React.memo for GameCard components (prevent unnecessary re-renders)
- Virtualized lists if >20 games displayed (react-window)
- Code splitting (React.lazy) for dashboard page
- Image lazy loading for team logos
- Bundle size budget: <500KB gzipped

### Build Priority Summary

**Week 1: Minimal Viable Pipeline + LIVE DEPLOYMENT**

1. ✅ Hardcoded team data (top 20 teams JSON) → dim_teams
2. ✅ NCAA API batch ingestion (basic - scores only)
3. ✅ Reddit API batch ingestion (exact team name matching only)
4. ✅ Simple excitement score v0.1 (post count + score margin)
5. ✅ FastAPI with 2 endpoints (/ api/games/today, /api/health)
6. ✅ Bare minimum React frontend (game list, no styling)
7. ✅ Docker Compose + AWS EC2 deployment
8. ✅ GitHub Actions CI/CD (push to main → auto-deploy)

**Milestone**: Live public URL by end of week 1 showing NCAA games with excitement scores

---

**Week 2: Refinement + Streaming**

1. ✅ Fuzzy team name matching + player mention detection
2. ✅ Time mapping logic (wall-clock → game-clock heuristic)
3. ✅ Enhanced excitement score v0.2 (VADER sentiment, rivalry bonus, game context)
4. ✅ Betfair streaming integration (flumine + WebSocket odds)
5. ✅ API expansion (/moments, /timeline endpoints)
6. ✅ Frontend improvements (game cards, sparklines, dark theme, mobile responsive)

**Milestone**: Refined demo with dual paradigms (batch + streaming), better matching, polished UI

---

**Week 3: Polish + Testing**

1. ✅ Testing suite (unit, integration, E2E - >70% coverage)
2. ✅ Error handling & resilience (retry logic, graceful degradation, caching)
3. ✅ Documentation (README, API docs, ADRs explaining tech choices)
4. ✅ Performance optimization (React.memo, query optimization, bundle size)
5. ✅ Enhanced monitoring (/api/health with detailed metrics, logging)

**Milestone**: Interview-ready demo with clean code, tests, comprehensive documentation

---

**Growth Phase (Post-MVP):**

1. Game thread comments ingestion + sentiment analysis
2. Advanced time mapping (ML model trained on labeled data)
3. Player dimension table + player mention matching
4. Historical data browsing (date picker, season leaderboards)
5. Win probability visualization (overlay odds on excitement chart)
6. Full observability stack (Prometheus, Grafana, CloudWatch, alerting)

**Vision (Future):**

1. Multi-sport expansion (NBA, NFL)
2. Predictive excitement models (pre-game forecasting)
3. Advanced analytics (correlation studies, accuracy validation)
4. Production-scale infrastructure (Kafka, Kubernetes, microservices)

---

## User Experience Principles

### UX Philosophy: Data Clarity Over Design Complexity

GamePulse is a **data visualization tool**, not a feature-rich application. The UX prioritizes getting users to insights quickly with minimal friction.

**Core Principle:** "Glanceable insights in <5 seconds, deep dive in <30 seconds"

---

### Visual Personality

**Dark, Data-Dense, Sports-Focused**

- **Dark Theme**: Reduces eye strain during evening game viewing, makes colored data (team colors, excitement badges) pop visually
- **Card-Based Layout**: Each game is a self-contained information unit
- **Data-Dense But Scannable**: Show all key metrics (score, excitement, status) without requiring clicks
- **Team Colors as Accents**: Use actual team primary colors for visual identity (Duke blue, UNC light blue)
- **Minimal Chrome**: No heavy navigation bars, sidebars, or complex menus - just content

**Design References:** ESPN ScoreCenter (data density) + Vercel Dashboard (dark theme, clean cards) + Bloomberg Terminal (information hierarchy)

---

### Key Interaction Patterns

**Pattern 1: Instant Context**
- User opens GamePulse → Immediately sees games ranked by excitement
- **No loading screens** - show skeleton UI while fetching
- **No onboarding** - interface is self-explanatory
- **No login** - public, read-only access

**Pattern 2: Progressive Disclosure**
- **Level 1 (Card View)**: Team names, scores, excitement badge, mini sparkline - visible without scrolling
- **Level 2 (Expand Moments)**: Click "Top Moments" → see 3-5 Reddit posts inline
- **Level 3 (External Link)**: Click Reddit post → opens thread in new tab for full context

**Pattern 3: Passive Updates**
- Dashboard auto-refreshes every 10-15 minutes
- **No manual refresh button needed** - data stays current automatically
- Visual indicator shows "Last updated X minutes ago"
- **Stale data warning** if API fails (yellow banner)

**Pattern 4: Mobile-First Thinking**
- Works on phone during commute/work breaks
- Vertical scroll (not horizontal)
- Large touch targets (no tiny click areas)
- Readable without zooming

---

### Information Hierarchy

**Visual Priority (Top to Bottom):**

1. **Excitement Score Badge** (Largest, most prominent)
   - 0-100 scale
   - Color-coded: Red (90-100) = must-watch, Orange (70-89) = interesting, Gray (<70) = skip
   - Purpose: Immediate "should I care about this game?" signal

2. **Team Names & Scores**
   - Large, readable font
   - Team colors for visual recognition
   - Score margin tells story (blowout vs close game)

3. **Game Status**
   - "LIVE 2:34 2nd Half" (urgent, happening now)
   - "Final" (retrospective, what happened)
   - "Scheduled 7:00 PM EST" (future, preview)

4. **Excitement Timeline** (Sparkline)
   - Shows how excitement evolved
   - Peaks = key moments worth investigating
   - Flat line = boring game (skip it)

5. **Top Moments** (Collapsed by default)
   - Reddit post titles tell the story
   - Upvote/comment counts validate importance
   - Expandable for details

---

### Critical User Flows (UX Lens)

**Flow 1: Real-Time Discovery**
```
User: "It's Saturday, 50 games are happening, which should I watch?"
1. Open GamePulse
2. Scan excitement badges (red/orange stand out)
3. See Kansas vs Kentucky has 88 excitement score + rising sparkline
4. Read top post: "Reeves hits back-to-back threes, Kansas up 8"
5. Decision made: Switch to that game
Time: < 10 seconds
```

**Flow 2: Retrospective Catch-Up**
```
User: "I was at work all day, what games mattered?"
1. Open GamePulse after games end
2. Sort shows Duke vs UNC at top (94 excitement score)
3. Expand "Top Moments"
4. Read 3 posts that tell the story:
   - "Duke opens with 12-0 run, crowd silenced" (10:00 1st Half)
   - "Bacot with monster dunk, UNC takes momentum" (0:00 2nd Half)
   - "Davis hits clutch 3 to put UNC up 5 with 5:00 left" (15:00 2nd Half)
5. User understands full game narrative without watching
Time: < 30 seconds
```

**Flow 3: Error Recovery**
```
User: Dashboard shows stale data (API failed)
1. Yellow banner appears: "Last updated 32 minutes ago - refresh in progress"
2. Old data remains visible (graceful degradation)
3. Once API recovers, banner disappears
4. Fresh data loads without user intervention
User experience: Slightly stale data > no data
```

---

### Responsive Design Strategy

**Desktop (1024px+):**
- 2-column grid of game cards
- Wider sparkline charts for detail
- Hover states show tooltips on charts

**Tablet (768-1023px):**
- 1-column grid, full-width cards
- Simplified spacing
- Touch-optimized buttons

**Mobile (<768px):**
- Single column, vertical scroll
- Compressed card layout (less padding)
- Smaller but still readable text
- Excitement badge remains prominent
- Sparklines simplified (fewer data points)

---

### Accessibility & Performance UX

**Accessibility (MVP Baseline):**
- Color is not the only signal (excitement score is numeric + color)
- Sufficient contrast ratios (WCAG AA minimum)
- Semantic HTML for screen readers
- **Defer**: Full keyboard navigation, ARIA labels (Growth phase)

**Performance as UX Feature:**
- <3 second dashboard load = user doesn't abandon
- Skeleton loading UI = feels fast even while loading
- Cached data = instant display on repeat visits
- Optimistic UI updates = feels responsive

---

### How UX Reinforces "The Magic"

The UX design directly supports the product magic:

**Magic: "Know which games matter in 5 seconds"**
→ **UX**: Excitement scores are largest element, color-coded, ranked descending

**Magic: "Understand what happened without watching"**
→ **UX**: Expandable Reddit posts with game-clock timestamps tell the story

**Magic: "Catch legendary moments as they happen"**
→ **UX**: Real-time updates + sparkline spikes + post titles like "UNBELIEVABLE BUZZER BEATER"

**Magic: "Community-driven narrative, not corporate highlights"**
→ **UX**: Reddit posts are featured prominently with upvote counts (social proof)

---

### UX Simplifications for MVP

**Week 1 (Acceptable for live demo):**
- No styling (bare HTML)
- No dark theme
- Simple list instead of cards
- **Goal**: Functional, not pretty

**Week 2 (Polished for interviews):**
- Dark theme implemented
- Styled game cards
- Sparkline charts working
- Mobile responsive
- **Goal**: Looks professional

**Growth (Post-MVP):**
- Animations (fade-ins, smooth transitions)
- Advanced filtering UI
- Game detail drill-down pages
- User preferences
- **Goal**: Production polish

---

## Functional Requirements

All functional requirements organized by capability area. Each requirement links to user value and includes acceptance criteria.

### FR-1: Game Data Ingestion & Storage

**FR-1.1: NCAA Game Schedule & Scores**
- **Requirement**: System SHALL ingest NCAA Men's Basketball game schedules, live scores, and final results from NCAA API
- **Frequency**: Every 10-15 minutes during game days
- **Acceptance Criteria**:
  - ✓ Fetch today's complete game schedule on system startup
  - ✓ Poll for score updates every 10-15 minutes
  - ✓ Store game_id, teams, scores, status, game clock in `games` table
  - ✓ Handle API rate limits (5 req/sec) without errors
  - ✓ Detect game status transitions (scheduled → live → halftime → final)
- **User Value**: Provides ground truth for which games exist and their current state

**FR-1.2: Team & Conference Dimensional Data**
- **Requirement**: System SHALL maintain dimensional data for NCAA teams and conferences
- **Implementation**: Static JSON configuration files for MVP, automated updates in Growth
- **Acceptance Criteria**:
  - ✓ Minimum 20 top NCAA teams with names, abbreviations, colors, conference IDs
  - ✓ Conference data with rivalry factors
  - ✓ Team aliases for matching variations (e.g., "Duke", "Blue Devils", "DU")
- **User Value**: Enables team identification, rivalry detection, visual team colors in UI

---

### FR-2: Social Sentiment Data Collection

**FR-2.1: Reddit Post Tracking**
- **Requirement**: System SHALL track Reddit posts from r/CollegeBasketball related to NCAA games
- **Frequency**: Every 10-15 minutes
- **Acceptance Criteria**:
  - ✓ Authenticate with Reddit API using PRAW (100 QPM limit)
  - ✓ Fetch new posts from r/CollegeBasketball
  - ✓ Extract: post_id, title, author, upvotes, comments_count, awards_count, timestamp, URL
  - ✓ Stay within API rate limits without throttling
- **User Value**: Captures community reactions and excitement signals

**FR-2.2: Reddit Post-to-Game Matching**
- **Requirement**: System SHALL match Reddit posts to specific games
- **MVP**: Exact team name matching (case-insensitive)
- **Growth**: Fuzzy matching, player mentions, confidence scoring
- **Acceptance Criteria**:
  - ✓ Week 1: Match posts containing exact team names in title
  - ✓ Week 2: Fuzzy match using team aliases (fuzzywuzzy library, >80% confidence)
  - ✓ Week 2: Store match_method and match_confidence for each post
  - ✓ Growth: Player mention detection using dim_players lookup
- **User Value**: Connects social narrative to specific games

**FR-2.3: Game Thread vs Moment Post Classification**
- **Requirement**: System SHALL distinguish between game threads and moment posts
- **Acceptance Criteria**:
  - ✓ Detect official game threads by title format: "[Game Thread] Team vs Team"
  - ✓ Set is_game_thread=TRUE for official threads
  - ✓ Classify post_type: game_thread, moment, pre_game, post_game
  - ✓ Classify game_time_context: pre_game, 1st_half, halftime, 2nd_half, post_game
- **User Value**: Game threads show community engagement; moment posts show highlights

---

### FR-3: Streaming Odds Data

**FR-3.1: Betfair Betting Odds Ingestion**
- **Requirement**: System SHALL ingest real-time betting odds via Betfair Exchange API + flumine
- **Implementation**: WebSocket streaming connection (Week 2)
- **Acceptance Criteria**:
  - ✓ Establish WebSocket connection to Betfair Stream API
  - ✓ Subscribe to NCAA basketball markets
  - ✓ Ingest market updates (home_odds, away_odds, volume) in real-time
  - ✓ Convert odds → implied win probabilities
  - ✓ Calculate odds_shift_5min (probability change over 5-minute window)
  - ✓ Run 24/7 with auto-reconnect on connection loss
- **User Value**: Provides market-based win probability and detects significant events via odds shifts

**FR-3.2: Odds Volatility Calculation**
- **Requirement**: System SHALL calculate odds volatility scores from betting data
- **Acceptance Criteria**:
  - ✓ Calculate magnitude of probability shifts over 5-minute windows
  - ✓ Large shifts (>10% probability change) indicate significant game events
  - ✓ Store odds_volatility_score in betting_odds table
- **User Value**: Odds volatility correlates with exciting moments (big plays, comebacks)

---

### FR-4: Excitement Score Algorithm

**FR-4.1: Excitement Score Calculation (Multi-Factor)**
- **Requirement**: System SHALL calculate excitement scores (0-100 scale) combining multiple signals
- **MVP v0.1** (Week 1): `excitement = (reddit_post_count * 10) + (score_margin_factor * 5)`
- **v0.2** (Week 2): Multi-factor weighted formula
- **Acceptance Criteria**:
  - ✓ Reddit velocity: posts/minute in rolling window
  - ✓ Reddit engagement: weighted sum of (upvotes + comments*0.5 + awards*2.0)
  - ✓ Sentiment: VADER sentiment analysis on post titles (Week 2)
  - ✓ Odds volatility: betting odds shift magnitude (Week 2)
  - ✓ Game context: close score, time remaining, upset potential, rivalry
  - ✓ Configurable weights via JSON config file
  - ✓ Normalized output: 0-100 scale
- **User Value**: Single number answer to "How exciting is this game?"

**FR-4.2: Time-Series Excitement Tracking**
- **Requirement**: System SHALL store excitement scores as time-series data
- **Frequency**: Every 15 minutes during games
- **Acceptance Criteria**:
  - ✓ Write excitement score to excitement_scores table with timestamp
  - ✓ Store component scores (reddit_velocity, sentiment, odds_volatility, game_context, rivalry_bonus)
  - ✓ Enable time-series queries for sparkline chart visualization
- **User Value**: Shows how excitement evolved throughout game (key moments visible as spikes)

---

### FR-5: Time Mapping & Temporal Context

**FR-5.1: Wall-Clock to Game-Clock Time Mapping**
- **Requirement**: System SHALL map Reddit post timestamps (wall-clock) to game clock times
- **MVP**: Simple heuristic using game start time + elapsed time
- **Growth**: ML model trained on labeled data
- **Acceptance Criteria**:
  - ✓ IF post_time < game_start_time THEN "pre_game"
  - ✓ ELIF post_time > game_end_time THEN "post_game"
  - ✓ ELSE: Calculate elapsed_time = post_time - game_start_time, estimate game clock
  - ✓ Account for halftime (20min + 15min halftime + 20min)
  - ✓ Store estimated_game_clock and time_mapping_confidence
- **User Value**: Displays "10:00 1st Half" instead of "7:35 PM EST" for better narrative

---

### FR-6: Backend API

**FR-6.1: Games Today Endpoint**
- **Requirement**: `GET /api/games/today` SHALL return today's games with excitement scores
- **Acceptance Criteria**:
  - ✓ Returns array of games sorted by excitement_score descending
  - ✓ Each game includes: teams (with colors), scores, status, excitement_score, is_rivalry
  - ✓ Include excitement_trend (last 10 time-series data points) for sparkline
  - ✓ Query param: ?limit=N (default 10)
  - ✓ Response time: <500ms
- **User Value**: Powers dashboard game list

**FR-6.2: Game Moments Endpoint**
- **Requirement**: `GET /api/games/{game_id}/moments` SHALL return top Reddit posts for a game
- **Acceptance Criteria** (Week 2):
  - ✓ Returns game_thread (if exists) with metadata
  - ✓ Returns top 5-10 moment posts ranked by engagement_score
  - ✓ Each post includes: title, upvotes, comments, estimated_game_clock, time_mapping_confidence, URL
  - ✓ Filter by post_type via query param: ?type=all|moment|game_thread
- **User Value**: Provides "what happened" narrative via Reddit posts

**FR-6.3: Health Check Endpoint**
- **Requirement**: `GET /api/health` SHALL return system status and data freshness
- **Acceptance Criteria**:
  - ✓ Returns overall status: healthy | degraded | unhealthy
  - ✓ Returns per-source status: betfair, ncaa_api, reddit_api
  - ✓ Includes: last_poll timestamps, games_tracked count, rate_limit_remaining
  - ✓ Database health: row_counts for key tables
- **User Value**: Enables monitoring and debugging; shown in UI during API failures

---

### FR-7: Web Dashboard

**FR-7.1: Game List View**
- **Requirement**: Dashboard SHALL display today's games ranked by excitement
- **MVP** (Week 1): Simple list, no styling
- **Polished** (Week 2): Styled game cards with dark theme
- **Acceptance Criteria**:
  - ✓ Fetch /api/games/today on page load
  - ✓ Display games in descending excitement_score order
  - ✓ Show: team names (with colors), scores, status, excitement badge
  - ✓ Auto-refresh every 10-15 minutes
  - ✓ Skeleton loading UI while fetching
- **User Value**: Instant view of which games matter most

**FR-7.2: Excitement Timeline Visualization**
- **Requirement**: Dashboard SHALL show excitement evolution via sparkline charts
- **Implementation**: Week 2 (defer if timeline tight)
- **Acceptance Criteria**:
  - ✓ Embedded sparkline in each game card
  - ✓ Data from excitement_trend in API response
  - ✓ Visual peaks indicate key moments
  - ✓ Tooltip on hover shows timestamp + score
- **User Value**: See when exciting moments happened during game

**FR-7.3: Top Moments Display**
- **Requirement**: Dashboard SHALL show top Reddit posts for each game
- **Implementation**: Week 2 expandable sections
- **Acceptance Criteria**:
  - ✓ Collapsed by default (show top 3)
  - ✓ Click "Show more" → expand to 5-10 posts
  - ✓ Display: post title, upvotes, comments, estimated_game_clock
  - ✓ Click post → open Reddit thread in new tab
- **User Value**: Understand "what happened" without watching game

**FR-7.4: Responsive Mobile Design**
- **Requirement**: Dashboard SHALL work on mobile devices
- **Implementation**: Week 2
- **Acceptance Criteria**:
  - ✓ Desktop (1024px+): 2-column grid
  - ✓ Tablet (768-1023px): 1-column grid
  - ✓ Mobile (<768px): Single column, optimized spacing
  - ✓ Touch-optimized buttons (min 44px targets)
  - ✓ Loads in <3 seconds on mobile 4G
- **User Value**: Use during commute, work breaks

---

### FR-8: Deployment & Operations

**FR-8.1: Continuous Deployment**
- **Requirement**: System SHALL auto-deploy on code changes
- **Implementation**: GitHub Actions CI/CD (Week 1)
- **Acceptance Criteria**:
  - ✓ Push to main → trigger GitHub Actions workflow
  - ✓ Run tests (unit, integration)
  - ✓ Build Docker images
  - ✓ Deploy to AWS EC2 t2.micro
  - ✓ Restart services without downtime
  - ✓ Rollback capability (keep last N images)
- **User Value**: Rapid iteration, always-current demo

**FR-8.2: Graceful Degradation**
- **Requirement**: System SHALL handle API failures gracefully
- **Acceptance Criteria**:
  - ✓ If NCAA API fails: Retry with exponential backoff, serve cached data
  - ✓ If Reddit API fails: Retry, show stale data with warning
  - ✓ If Betfair stream disconnects: Auto-reconnect within 30 seconds
  - ✓ UI shows yellow banner: "Last updated X minutes ago"
  - ✓ Frontend displays cached data even when backend is degraded
- **User Value**: Slightly stale data > no data; system stays useful during outages

---

## Non-Functional Requirements

Non-functional requirements define system quality attributes critical to portfolio demonstration and user experience.

### NFR-1: Performance

**NFR-1.1: API Response Times**
- **Requirement**: Backend API SHALL respond within performance thresholds to support responsive UX
- **Targets**:
  - `GET /api/games/today`: <500ms (p50), <1000ms (p95)
  - `GET /api/games/{id}/moments`: <300ms (p50), <700ms (p95)
  - `GET /api/health`: <100ms (p50), <200ms (p95)
- **Measurement**: Add response time logging to FastAPI middleware (Week 3)
- **Rationale**: Sub-second API responses enable <3 second dashboard load target

**NFR-1.2: Dashboard Load Performance**
- **Requirement**: Frontend dashboard SHALL load within 3 seconds on typical mobile 4G connection
- **Breakdown**:
  - Initial HTML/CSS/JS bundle: <1 second
  - API fetch `/api/games/today`: <1 second
  - Render + paint: <1 second
- **Optimizations**:
  - Code splitting (React.lazy) for non-critical components
  - Bundle size budget: <500KB gzipped
  - Image lazy loading for team logos
  - Skeleton UI displayed immediately (perceived performance)
- **Measurement**: Lighthouse CI in GitHub Actions (Week 3), target score >85

**NFR-1.3: Database Query Performance**
- **Requirement**: Time-series queries SHALL complete within performance thresholds
- **Targets**:
  - Excitement score calculation (15-min rolling window): <200ms
  - Sparkline data fetch (last 10 data points): <50ms
  - Game moments query (top 10 posts by engagement): <100ms
- **Optimizations**:
  - QuestDB SYMBOL type for high-cardinality columns (team_id, game_id)
  - Time-based partitioning (PARTITION BY DAY)
  - Indexes on timestamp + game_id composite keys
- **Measurement**: Query profiling with QuestDB EXPLAIN command

**NFR-1.4: Data Freshness**
- **Requirement**: Dashboard data SHALL be fresh enough to support "near real-time" experience
- **Targets**:
  - Game scores: Updated every 10-15 minutes during live games
  - Reddit posts: Polled every 10-15 minutes
  - Betfair odds (Week 2): Streamed in real-time (WebSocket)
  - Excitement scores: Recalculated every 15 minutes
- **UI Indicator**: "Last updated X minutes ago" timestamp visible in dashboard
- **Acceptance**: Data up to 15 minutes stale is acceptable for MVP (not millisecond real-time)

---

### NFR-2: Security

**NFR-2.1: API Authentication**
- **Requirement**: External data source APIs SHALL authenticate securely
- **Implementation**:
  - **Reddit API**: OAuth 2.0 credentials stored in environment variables (.env file)
  - **Betfair API**: API key + session token management via flumine
  - **NCAA API**: No authentication required (public)
- **Security Practices**:
  - NEVER commit credentials to git (enforce via .gitignore + pre-commit hooks)
  - Rotate credentials every 90 days
  - Use environment variables injected via AWS Systems Manager Parameter Store (Growth)

**NFR-2.2: Rate Limiting & Abuse Prevention**
- **Requirement**: System SHALL respect upstream API rate limits and prevent abuse
- **Targets**:
  - **Reddit API**: 100 queries per minute (QPM) with OAuth → Implement token bucket algorithm
  - **NCAA API**: 5 requests/second → Add 200ms delay between requests
  - **Betfair API**: No explicit limit but implement reconnect backoff
- **Frontend Rate Limiting**: Defer to Growth phase (public read-only, no user auth)
- **Monitoring**: Track rate limit headers (`X-Ratelimit-Remaining`) and log warnings at 80% capacity

**NFR-2.3: Data Privacy**
- **Requirement**: System SHALL NOT collect or store personal user information
- **Justification**: MVP is public, read-only dashboard with no user authentication
- **Data Collected**:
  - ✓ Publicly available Reddit post metadata (no user tracking)
  - ✓ Public NCAA game data
  - ✓ Public betting odds data
  - ✗ NO user accounts, sessions, or analytics cookies
- **Future Consideration**: If adding user accounts (Growth), implement GDPR-compliant consent flow

**NFR-2.4: Dependency Security**
- **Requirement**: System SHALL use secure, maintained dependencies
- **Practices**:
  - Run `pip-audit` (Python) and `npm audit` (frontend) in CI/CD pipeline
  - Pin dependency versions in requirements.txt / package.json
  - Auto-update security patches via Dependabot
  - Review dependency licenses for compatibility (MIT/Apache preferred)

---

### NFR-3: Scalability

**NFR-3.1: Peak Load Capacity**
- **Requirement**: System SHALL handle March Madness peak traffic without degradation
- **Expected Load**:
  - **Games tracked**: 5-10 concurrent games (16 peak day)
  - **Reddit posts**: ~100-200 posts/hour during peak
  - **API requests**: ~10 req/min to backend API
  - **Concurrent users**: 10-50 (portfolio demo scale, not production traffic)
- **Scaling Strategy for MVP**: Single EC2 t2.micro sufficient (1 vCPU, 1GB RAM)
- **Growth Scaling Path**:
  - Phase 1: Vertical scaling (upgrade to t3.small: 2 vCPU, 2GB RAM)
  - Phase 2: Horizontal scaling (multi-instance + load balancer)
  - Phase 3: Microservices (separate ingestion, API, frontend services)

**NFR-3.2: Data Storage Growth**
- **Requirement**: System SHALL accommodate data growth over NCAA basketball season
- **Estimates** (5-month season, Nov-Mar):
  - **Games**: ~5,000 games × 500 bytes = 2.5MB
  - **Reddit posts**: 200 posts/day × 150 days × 1KB = 30MB
  - **Excitement scores**: 5,000 games × 10 scores/game × 200 bytes = 10MB
  - **Betfair odds**: 10 games/day × 150 days × 100 ticks/game × 100 bytes = 15MB
  - **Total**: ~60MB data storage for full season
- **QuestDB Capacity**: Can handle 100s of GB efficiently, 60MB is negligible
- **Retention Policy**: Keep all data for portfolio demonstration (no automatic deletion)

**NFR-3.3: Time-Series Query Scalability**
- **Requirement**: Time-series queries SHALL remain performant as data accumulates
- **Optimization Strategy**:
  - Partition by DAY (QuestDB native feature) for efficient time-range queries
  - SYMBOL type for categorical columns (game_id, team_id) reduces storage + query time
  - Leverage QuestDB columnar storage (only read columns needed)
- **Benchmark Target**: Sparkline query (10 data points for single game) <50ms even with 6 months data

---

### NFR-4: Reliability

**NFR-4.1: Uptime Target**
- **Requirement**: System SHALL maintain high availability during peak demo periods (March Madness)
- **Target**: 95% uptime during March-April (acceptable for portfolio project)
- **Acceptable Downtime**: 1-2 hours/day off-peak for maintenance
- **Monitoring**: Basic health check pings via UptimeRobot (free tier)
- **Rationale**: Not a production SLA, but reliable enough for interview demos

**NFR-4.2: Graceful Degradation**
- **Requirement**: System SHALL remain partially functional when dependencies fail
- **Failure Modes**:
  - **NCAA API down**: Serve cached game data + show stale data warning
  - **Reddit API down**: Show games without social sentiment data
  - **Betfair stream disconnects**: Auto-reconnect with exponential backoff (5s, 10s, 30s, 60s)
  - **Database unreachable**: Return HTTP 503 with clear error message
- **User Experience**: Yellow banner "Last updated 32 minutes ago - refresh in progress"
- **Implementation**: Retry logic with exponential backoff (tenacity library)

**NFR-4.3: Error Handling & Logging**
- **Requirement**: System SHALL log errors comprehensively for debugging
- **Logging Strategy**:
  - **Structured logging**: JSON format with timestamp, level, component, message
  - **Log levels**: DEBUG (local dev), INFO (production), ERROR (API failures, exceptions)
  - **Log destinations**: stdout → captured by Docker → CloudWatch Logs (Week 3)
  - **Log retention**: 7 days (sufficient for debugging recent issues)
- **Error Tracking**: Defer Sentry integration to Growth phase (manual log review sufficient for MVP)

**NFR-4.4: Data Quality Metrics**
- **Requirement**: System SHALL track data quality to ensure reliability
- **Metrics**:
  - **Match confidence**: % of Reddit posts matched to games with >80% confidence
  - **Data completeness**: % of games with at least 1 Reddit post
  - **API success rate**: % of API calls returning 2xx status
  - **Stale data events**: Count of times cached data served due to API failure
- **Monitoring**: Expose in `/api/health` endpoint, log daily summary
- **Alerting**: Defer to Growth phase (manual review sufficient for MVP)

---

### NFR-5: Maintainability

**NFR-5.1: Code Quality & Documentation**
- **Requirement**: Codebase SHALL be interview-ready with clear documentation
- **Code Quality Standards**:
  - **Python**: Black formatter, pylint linter, type hints (mypy)
  - **TypeScript**: ESLint + Prettier, strict TypeScript mode
  - **Test coverage**: >70% for core logic (matching, excitement calculation, API endpoints)
  - **Max cyclomatic complexity**: 10 (enforce via linters)
- **Documentation Requirements**:
  - **README.md**: Project overview, architecture diagram, setup instructions, demo link
  - **API docs**: Auto-generated OpenAPI/Swagger spec from FastAPI
  - **ADRs** (Architecture Decision Records): Why QuestDB? Why post-level vs comments? Why 10-15 min polling?
  - **Inline comments**: Document complex algorithms (excitement score, time mapping)

**NFR-5.2: Testing Strategy**
- **Requirement**: System SHALL have comprehensive automated tests for core functionality
- **Testing Pyramid**:
  - **Unit Tests** (60% of coverage):
    - Excitement score calculation logic
    - Reddit post-to-game matching logic
    - Time mapping algorithm
    - API response serialization
  - **Integration Tests** (30% of coverage):
    - FastAPI endpoint tests with mocked database
    - Database query tests against test QuestDB instance
    - Reddit API client integration tests (with cassette-recorded responses)
  - **E2E Tests** (10% of coverage):
    - Full pipeline test with simulated game data
    - Dashboard smoke test (frontend loads, API calls work)
- **Test Execution**: Run via pytest (backend) + Jest (frontend) in GitHub Actions CI

**NFR-5.3: Deployment Automation**
- **Requirement**: Deployment SHALL be fully automated via CI/CD pipeline
- **GitHub Actions Workflow** (Week 1):
  1. **Trigger**: Push to `main` branch
  2. **Lint & Test**: Run black, pylint, pytest, eslint, jest
  3. **Build**: Docker build for backend + frontend
  4. **Deploy**: SSH to EC2, pull images, docker-compose restart
  5. **Smoke Test**: Curl `/api/health` to verify deployment
  6. **Rollback**: Keep last 3 Docker images for manual rollback if needed
- **Deployment Time**: <5 minutes from push to live
- **Zero-Downtime**: Use docker-compose rolling restart (acceptable brief downtime for MVP)

**NFR-5.4: Configuration Management**
- **Requirement**: System configuration SHALL be externalized and environment-specific
- **Configuration Strategy**:
  - **Environment variables**: Database URLs, API keys, polling intervals
  - **.env files**: Local development (gitignored)
  - **AWS Systems Manager Parameter Store**: Production secrets (Growth phase)
  - **config.yaml**: Excitement algorithm weights, team data, conference rivalries
- **Versioning**: Configuration changes tracked in git (except secrets)

---

### NFR-6: Cost Constraints

**NFR-6.1: Budget Ceiling**
- **Requirement**: System SHALL operate within $10/month budget
- **Cost Breakdown** (AWS us-east-1):
  - **EC2 t2.micro**: $0/month (free tier, 750 hours/month)
  - **EBS storage**: $0.10/GB × 20GB = $2/month
  - **Data transfer**: ~5GB/month × $0.09/GB = $0.45/month
  - **S3 + CloudFront**: <$1/month (static assets)
  - **CloudWatch Logs**: Free tier sufficient (<5GB/month)
  - **Total Estimated**: ~$3.50/month (well under $10 limit)
- **External API Costs**:
  - Reddit API: $0 (free with OAuth)
  - NCAA API: $0 (self-hosted, free)
  - Betfair API: $0 (free personal account, no transaction fees as read-only)
- **Cost Monitoring**: AWS Budget alert at $8/month threshold

**NFR-6.2: Resource Efficiency**
- **Requirement**: System SHALL optimize resource usage to stay within free tier when possible
- **Optimization Strategies**:
  - **CPU**: Efficient polling (no busy-wait loops), batch processing where possible
  - **Memory**: QuestDB footprint <300MB, FastAPI <200MB, leaving headroom on 1GB instance
  - **Disk I/O**: Leverage QuestDB columnar storage (minimal disk I/O for queries)
  - **Network**: Compress API responses (gzip), minimize polling frequency (10-15 min)
- **Monitoring**: Track resource usage via `/api/health` endpoint (CPU %, memory %, disk %)

---

### NFR-7: Accessibility

**NFR-7.1: Baseline Accessibility (MVP)**
- **Requirement**: Dashboard SHALL meet minimum accessibility standards
- **MVP Standards**:
  - **Color contrast**: WCAG AA minimum (4.5:1 for normal text)
  - **Semantic HTML**: Proper heading hierarchy (h1 → h2 → h3)
  - **Color independence**: Excitement score includes numeric value + color (not color-only)
  - **Text readability**: Minimum 16px font size, sufficient line height
- **Defer to Growth**:
  - Full keyboard navigation
  - ARIA labels for screen readers
  - WCAG AAA compliance
  - Accessibility audit tooling
- **Rationale**: Portfolio demo users are likely not using assistive tech; baseline sufficient for MVP

---

### NFR-8: Browser & Platform Compatibility

**NFR-8.1: Browser Support**
- **Requirement**: Dashboard SHALL work on modern browsers
- **Supported Browsers** (last 2 major versions):
  - ✓ Chrome/Edge (Chromium)
  - ✓ Firefox
  - ✓ Safari (desktop + iOS)
- **Not Supported**: Internet Explorer, legacy browsers
- **Testing Strategy**: Manual testing on Chrome (primary) + Safari (secondary)
- **Polyfills**: Use browserslist + babel to transpile for target browsers

**NFR-8.2: Device Support**
- **Requirement**: Dashboard SHALL work on desktop, tablet, and mobile devices
- **Responsive Breakpoints**:
  - Desktop: 1024px+ (2-column grid)
  - Tablet: 768-1023px (1-column grid)
  - Mobile: <768px (single column, optimized spacing)
- **Touch Optimization**: Minimum 44px touch targets for buttons/links
- **Testing**: Chrome DevTools device emulation + physical iPhone/Android testing

---

### Non-Functional Requirements Summary

The non-functional requirements prioritize **portfolio demonstration value** and **interview readiness** while maintaining acceptable user experience quality. Key trade-offs:

- **Performance**: Fast enough to feel responsive (<3s load), not millisecond-optimized
- **Security**: Secure credential management, but no user authentication complexity
- **Scalability**: Handles March Madness load, not production millions of users
- **Reliability**: 95% uptime acceptable, comprehensive error handling prioritized
- **Maintainability**: Interview-ready code quality, >70% test coverage, clear ADRs
- **Cost**: Well under $10/month budget with headroom
- **Accessibility**: Baseline WCAG AA compliance, full accessibility deferred to Growth

These NFRs balance **technical sophistication** (demonstrates engineering maturity) with **pragmatic MVP scope** (ships in 2-3 weeks).

---

## PRD Validation & Review

### Completeness Checklist

**✓ Executive Summary** - Product vision, magic, and target users clearly defined
**✓ Project Classification** - Web app + data pipeline, sports analytics domain, medium complexity
**✓ Success Criteria** - Portfolio impact, technical performance, user validation metrics
**✓ Product Scope** - MVP, Growth, Vision features with clear boundaries
**✓ Data Pipeline Architecture** - Batch + streaming paradigms, QuestDB time-series storage
**✓ User Experience Principles** - Dark theme, data-dense, glanceable insights
**✓ Functional Requirements** - 8 capability areas (FR-1 through FR-8) with acceptance criteria
**✓ Non-Functional Requirements** - 8 quality attributes (NFR-1 through NFR-8) with measurable targets

### Key Architectural Decisions

The PRD documents critical technical choices with rationale:

1. **QuestDB for Time-Series Storage** - 6.5x faster than TimescaleDB, SQL interface, lightweight for free tier
2. **Post-Level Reddit Tracking** - API-efficient (100 QPM sufficient), captures high-signal moments
3. **Betfair Streaming Integration** - Demonstrates genuine WebSocket streaming for portfolio value
4. **10-15 Minute Polling** - Balances freshness with API limits, "near real-time" acceptable for MVP
5. **Week 1 Deployment Priority** - Live demo URL early, iterate from there
6. **Dimensional Data Model** - Teams/conferences for matching, rivalry detection, visual accents
7. **Wall-Clock to Game-Clock Mapping** - Enables narrative timeline ("10:00 1st Half" context)
8. **Dual Processing Paradigms** - Batch (NCAA, Reddit) + Streaming (Betfair) shows engineering range

### Portfolio Story Arc

This PRD positions GamePulse for maximum interview impact:

**Technical Depth**: Multi-source integration, time-series analysis, streaming + batch processing, sentiment analysis
**Pragmatic Trade-offs**: Documented decisions (why not Kafka? why not transformers?) show mature engineering judgment
**User-Centric**: Solves real problem (game discovery paralysis) with measurable value
**Demo-Ready**: 2-3 week timeline, live URL before interviews, handles March Madness scale
**Growth Narrative**: Clear Phase 2+ expansion shows long-term product thinking

### Known Constraints & Risks

**Constraints Acknowledged:**
- Reddit API 100 QPM limit → Constrains polling frequency
- NCAA API 5 req/sec limit → Requires rate limiting
- AWS free tier 1GB RAM → Single EC2 t2.micro, no multi-instance scaling in MVP
- 2-3 week timeline → Aggressive, requires strict scope discipline

**Risks & Mitigations:**
- **Risk**: Reddit matching accuracy low → **Mitigation**: Fuzzy matching + confidence scoring in Week 2
- **Risk**: Betfair API complex to integrate → **Mitigation**: flumine library abstracts complexity
- **Risk**: Excitement algorithm produces poor rankings → **Mitigation**: Configurable weights, iterate based on real data
- **Risk**: March Madness demo fails during interview → **Mitigation**: Graceful degradation, cached data fallback

---

## Implementation Planning

### Epic Breakdown Required

The PRD functional requirements (FR-1 through FR-8) map naturally to implementation epics:

**Suggested Epic Structure:**

1. **Epic 1: Foundation & Deployment** (Week 1)
   - AWS infrastructure setup
   - QuestDB database schema
   - Docker + Docker Compose configuration
   - GitHub Actions CI/CD pipeline
   - Basic health check endpoint
   - **Milestone**: Live public URL

2. **Epic 2: Game Data Ingestion** (Week 1)
   - NCAA API client implementation
   - Game schedule, scores, status polling
   - Dimensional data (teams, conferences) as JSON config
   - Games table schema and ingestion logic
   - **Milestone**: Dashboard shows today's games with scores

3. **Epic 3: Reddit Social Sentiment** (Week 1-2)
   - Reddit API OAuth authentication
   - Post fetching from r/CollegeBasketball
   - Post-to-game matching (exact → fuzzy)
   - Game thread vs moment post classification
   - Reddit posts table storage
   - **Milestone**: Posts linked to games

4. **Epic 4: Excitement Score Algorithm** (Week 1-2)
   - v0.1 simple scoring (post count + score margin)
   - v0.2 multi-factor scoring (velocity, engagement, sentiment, odds, context)
   - VADER sentiment analysis integration
   - Time-series excitement_scores table
   - Configurable weights via config.yaml
   - **Milestone**: Games ranked by excitement

5. **Epic 5: Streaming Odds Integration** (Week 2)
   - Betfair API account setup
   - flumine framework integration
   - WebSocket stream connection
   - Odds → win probability conversion
   - Odds volatility calculation
   - Betting_odds table storage
   - **Milestone**: Real-time odds streaming demonstrated

6. **Epic 6: Time Mapping & Context** (Week 2)
   - Wall-clock → game-clock heuristic algorithm
   - Game status tracking (pre_game, 1st_half, halftime, 2nd_half, post_game)
   - Estimated game clock storage with confidence scores
   - **Milestone**: Moments displayed with game-time context

7. **Epic 7: Backend API Development** (Week 1-2)
   - FastAPI application setup
   - `/api/games/today` endpoint with excitement scores
   - `/api/games/{id}/moments` endpoint with Reddit posts
   - `/api/health` endpoint with system status
   - Response time logging middleware
   - **Milestone**: Frontend can fetch all necessary data

8. **Epic 8: Frontend Dashboard** (Week 1-2)
   - React + TypeScript setup
   - Game list view with sorting
   - Dark theme + Tailwind CSS styling
   - Game cards with team colors and excitement badges
   - Sparkline excitement timeline charts
   - Top moments expandable sections
   - Mobile-responsive design
   - Auto-refresh every 10-15 minutes
   - **Milestone**: Polished, mobile-friendly dashboard

9. **Epic 9: Testing & Quality** (Week 3)
   - Unit tests (excitement calculation, matching, time mapping)
   - Integration tests (API endpoints, database queries)
   - E2E tests (full pipeline simulation)
   - Linting + formatting (Black, ESLint)
   - >70% test coverage
   - **Milestone**: Interview-ready code quality

10. **Epic 10: Documentation & Polish** (Week 3)
    - README with architecture diagram
    - API documentation (OpenAPI/Swagger)
    - Architecture Decision Records (ADRs)
    - Performance optimization (React.memo, query tuning)
    - Error handling refinement
    - **Milestone**: Complete portfolio artifact

**Next Step:** Run `/bmad:bmm:workflows:create-epics-and-stories` to generate detailed epic files and story breakdown.

---

## Workflow Transition Guidance

### Completed: PRD Creation

The Product Requirements Document is now complete with:
- Strategic product vision and portfolio positioning
- Comprehensive functional requirements (8 capability areas)
- Measurable non-functional requirements (8 quality attributes)
- Clear MVP scope with Growth roadmap
- 3-week phased implementation plan

### Next: Architecture Design

**Before implementation, run the architecture workflow to document:**

1. **System Architecture** - Component diagram showing data pipeline, backend API, frontend, databases
2. **Data Flow** - How data moves from NCAA/Reddit/Betfair → QuestDB → API → Dashboard
3. **Technology Stack Validation** - Confirm QuestDB, FastAPI, React, Docker choices
4. **Deployment Architecture** - AWS EC2 setup, Docker Compose orchestration, CI/CD flow
5. **Key Design Patterns** - Retry logic, graceful degradation, time-series aggregation
6. **API Contract Specs** - Detailed OpenAPI schemas for endpoints
7. **Database Schema** - Complete QuestDB table definitions with indexes and partitioning

**Command:** `/bmad:bmm:workflows:architecture`

**Why Architecture Before Implementation?**
- Validates technical feasibility of PRD requirements
- Documents system-level decisions for interview discussions
- Creates reference guide for development phase
- Identifies potential integration issues before coding

### Alternative: Quick Flow to Implementation

If you want to skip architecture documentation and start building immediately:

1. Run `/bmad:bmm:workflows:sprint-planning` to generate sprint status tracking
2. Run `/bmad:bmm:workflows:create-story` to generate first story from PRD
3. Run `/bmad:bmm:workflows:dev-story` to implement the story

**Trade-off:** Faster to first code, but less interview documentation to showcase architectural thinking.

---

## References

This PRD builds upon prior discovery and research artifacts:

- **Product Brief:** [docs/product-brief-data-project-2025-11-06.md](docs/product-brief-data-project-2025-11-06.md)
  - Initial product vision and technical preferences
  - Target users and MVP scope definition
  - 2-3 week timeline and success criteria

- **Technical Research:** [docs/research-technical-2025-11-06.md](docs/research-technical-2025-11-06.md)
  - QuestDB performance benchmarks (6.5x faster than TimescaleDB)
  - Sports analytics market validation ($4.75B by 2030)
  - API verification (NCAA, Reddit, Betfair all active in 2025)
  - VADER vs transformer sentiment analysis comparison (339x faster)

- **Brainstorming Session:** [docs/bmm-brainstorming-session-2025-11-06.md](docs/bmm-brainstorming-session-2025-11-06.md)
  - Generated 10+ sports analytics ideas
  - Converged on Reddit + betting odds integration
  - Identified compelling use cases (tune-in recommendations, Reddit vs Vegas analysis)

- **UI Mockups:**
  - [docs/gamepulse-1-desktop.png](docs/gamepulse-1-desktop.png) - Dark theme game cards with excitement badges
  - [docs/gamepulse-1-mobile.png](docs/gamepulse-1-mobile.png) - Mobile-responsive layout

---

## Document History

**Version:** 1.0
**Date:** 2025-11-07
**Status:** ✓ Complete - Ready for Architecture Phase
**Author:** Philip (Product Owner) + PM Agent (Facilitation)

**Change Log:**
- 2025-11-07: Initial PRD creation via `/bmad:bmm:workflows:prd` workflow
- Completed all 10 workflow steps: Vision → Success → Scope → Deep Dive → UX → Functional Reqs → Non-Functional Reqs → Review

---

_This PRD captures the essence of **GamePulse** - a platform that answers "Which games matter right now?" in 5 seconds and reveals "What happened today?" in 30 seconds through community-driven sports narrative._

_GamePulse demonstrates data engineering competency (multi-source integration, time-series analysis, streaming + batch processing) while solving a genuine user need during March Madness chaos._

_Created through collaborative discovery between Philip and AI Product Manager facilitator._

_Ready for architecture design and epic breakdown._
