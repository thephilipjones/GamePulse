# Product Brief: GamePulse

**Date:** 2025-11-06
**Author:** Philip
**Context:** Data engineering portfolio project

---

## Executive Summary

GamePulse is a real-time sports analytics platform that integrates live game data, social sentiment from Reddit, and betting odds to answer compelling questions about sports engagement. Built as a portfolio showcase for data engineering interviews, it demonstrates multi-source streaming data integration, time-series analysis, and modern cloud architecture while addressing real user needs around game discovery and social sentiment analysis.

---

## Core Vision

### Problem Statement

Sports fans face overwhelming choice paralysis during peak NCAA basketball season. On a typical Saturday, 50+ games happen simultaneously across different conferences and time zones. Fans miss incredible moments - buzzer beaters, major upsets, breakout performances - because they can't track excitement across dozens of games in real-time.

Traditional solutions fall short:
- Score apps show numbers but not narrative or excitement
- Highlight reels come hours/days later after the moment has passed
- Social media (Reddit/Twitter) requires active monitoring across multiple threads
- No unified view of "what's happening RIGHT NOW that I should care about"

The result: Fans consistently choose the wrong game to watch, miss legendary moments, and discover the day's best stories only through post-game analysis when the excitement is gone.

### Proposed Solution

GamePulse is a unified daily timeline platform that surfaces the excitement and narrative of NCAA basketball games through social media signals and game data integration.

**Core Experience:**
- **Morning View**: See today's scheduled games with predicted excitement based on rankings, rivalries, and historical matchups
- **Live Tracking**: Monitor games in progress with real-time excitement scores calculated from Reddit post velocity, upvotes, and community engagement
- **Post-Game Discovery**: Catch up on completed games with curated "what happened" summaries from top Reddit posts and reactions

**The Innovation:**
Instead of streaming millions of comments, GamePulse tracks Reddit post patterns across r/CollegeBasketball and team subreddits. When something crazy happens, the community creates the highlight reel through post titles ("UNBELIEVABLE BUZZER BEATER BY 15-SEED") and upvote velocity. GamePulse surfaces these moments as they unfold.

**Technical Foundation:**
- Sport-agnostic data abstraction layer (NCAA API for MVP, extensible to other leagues)
- Efficient Reddit post tracking (not comments) optimized for API rate limits
- Excitement scoring algorithm combining engagement velocity, post sentiment, and game context
- Timeline visualization showing game state transitions and excitement peaks

**Built for portfolios, designed for users:** While showcasing modern data engineering practices (multi-source integration, real-time processing, time-series analysis), GamePulse solves a genuine user need that existing solutions miss.

---

## Target Users

### Primary Users

**Audience 1: Data Engineering Hiring Managers & Interview Panels**

The immediate "customers" evaluating this portfolio project:
- Review dozens of candidate portfolios seeking signals of production-ready thinking
- Looking for differentiation beyond basic single-source ETL pipelines
- Value real-time streaming capabilities, modern tech stack choices, and clear architectural trade-off documentation
- Want candidates who can articulate why they made specific technology decisions
- Impressed by projects that solve actual user problems, not just technical exercises

**Audience 2: College Basketball Fans (Product Users)**

The actual users GamePulse is designed to serve:
- Follow NCAA basketball season but can't watch every game live
- Active in Reddit sports communities (r/CollegeBasketball, team subreddits)
- Experience severe FOMO during March Madness when 32+ games happen across 48 hours
- Want to discover legendary moments without manually scrolling dozens of game threads
- Prefer community-driven narrative and highlights over traditional broadcaster coverage
- Need mobile-friendly glanceable updates during work/commute

**Philip himself represents both audiences** - building to showcase technical skills while solving a problem he personally experiences as a college basketball fan.

---

## MVP Scope

### Core Features

**1. Daily Game Timeline Dashboard**
- Display all NCAA Men's Basketball games for the current day in chronological order
- Show game state indicators: scheduled (with start time), in-progress (with live score), completed (with final score)
- Visual timeline representation showing when games start and end throughout the day
- Mobile-responsive single-page design optimized for glanceable updates

**2. Excitement Score Calculation & Display**
- Track Reddit posts in r/CollegeBasketball related to each game
- Calculate excitement metrics from: post velocity (posts/minute), upvote count, comment engagement
- Display excitement level per game with visual indicators (heat/intensity score)
- Update scores every 10-15 minutes during games (API-limit optimized)

**3. Post-Game "What Happened" Summary**
- Automatically surface top 3-5 Reddit posts for each completed game
- Display post title, upvote count, and link to original thread
- Sort by engagement (upvotes × comments) to find most significant moments
- Provides instant narrative context without watching full highlights

**4. NCAA Game Data Integration**
- Fetch game schedule, live scores, and final results via henrygd/ncaa-api
- Abstract sport data layer for future extensibility to other leagues
- Periodic polling (10-15 min intervals) balancing freshness with API efficiency
- Handle API failures gracefully with cached data fallback

**5. Reddit Post Tracking System**
- Monitor r/CollegeBasketball for game-related posts (not comment streaming)
- Match posts to games via team names, game context, timestamps
- Track post metadata: title, upvotes, comment count, timestamp
- Optimized for Reddit API rate limits (100 QPM = efficient post-level tracking)

**6. Basic Data Pipeline Architecture**
- Python-based data collection with simple queues for processing
- QuestDB time-series database for excitement metrics and post data
- Scheduled jobs for game data refresh and Reddit post polling
- Backend API serving dashboard data to frontend

### Out of Scope for MVP

**Advanced Data & Analytics (Phase 2+):**
- Betting odds integration (The Odds API integration deferred)
- Win probability charts overlaid on game timelines
- Predictive excitement modeling using machine learning
- Historical trend analysis across multiple seasons
- Advanced sentiment analysis with transformer models (staying with VADER baseline)
- Comment-level sentiment analysis (post-level only for MVP)

**Multi-Sport Expansion:**
- NBA, NFL, other professional leagues
- NCAA Football addition
- Multi-sport unified dashboard
- Cross-sport excitement comparisons

**User-Facing Features:**
- User accounts and authentication
- Personalized team/conference preferences
- Custom notification and alert system
- Saved games and bookmarked moments
- Social sharing and viral moment distribution

**Technical & Scale Enhancements:**
- Production-scale streaming infrastructure (Kafka/Kinesis vs simple queues)
- Team-specific subreddit monitoring (staying with r/CollegeBasketball only)
- Real-time WebSocket push updates (10-15 min polling sufficient for MVP)
- Advanced filtering by conference, ranking, or rivalry
- Historical data backfill beyond current season
- Native mobile applications (web-responsive sufficient)

**Rationale:** MVP focuses on proving core value - daily game timeline with excitement scoring and narrative discovery - before expanding scope. Clean demo during March Madness is the North Star.

### MVP Success Criteria

**Demo Capability:**
- Fully functional during March Madness 2026 (target demo period)
- Handles 50+ NCAA basketball games per peak day
- Surfaces top moments from 5+ exciting games daily

**Technical Performance:**
- Runs within AWS free tier ($0 operational cost)
- Updates game data and excitement scores every 10-15 minutes
- Dashboard loads in < 3 seconds on mobile
- Stays within Reddit API rate limits (100 QPM)

**Portfolio Impact:**
- Clean, documented codebase ready for interview code review
- Clear architectural decision documentation (why QuestDB, why post-level tracking, etc.)
- Live demo URL that works reliably during interview season
- Demonstrates multi-source data integration and time-series analysis

**User Value:**
- Successfully identifies "most exciting" games with 70%+ accuracy (measured by post-game consensus)
- Surfaces buzzer beaters and major upsets within 15 minutes of occurrence
- Provides useful "what happened today" retrospective view

---

## Technical Preferences

Based on comprehensive technical research validating 2025 technology options, the following stack is recommended for MVP:

**Data Sources:**
- **NCAA Game Data**: henrygd/ncaa-api (free, self-hostable, 5 req/sec limit)
- **Social Data**: Reddit API via PRAW (100 QPM with OAuth, post-level tracking)

**Backend & Processing:**
- **Language**: Python 3.11+
- **Processing**: Simple queues (asyncio/threading) for MVP velocity
- **Sentiment Analysis**: VADER (339x faster than transformers, social media optimized)
- **API Layer**: FastAPI or Flask

**Database:**
- **Primary**: QuestDB (2025 performance leader - 6.5x faster ingestion than TimescaleDB)
- **Rationale**: SQL interface, Python-native client, lightweight for AWS free tier

**Frontend:**
- **Framework**: React 18+ with TypeScript
- **Real-time**: Socket.IO or polling (10-15 min intervals sufficient)
- **Styling**: Tailwind CSS
- **Charts**: Recharts or Chart.js

**Infrastructure:**
- **Cloud**: AWS EC2 t2.micro (free tier)
- **Database Hosting**: QuestDB on same EC2 instance
- **Static Assets**: S3 + CloudFront
- **Deployment**: Docker Compose for simplicity

**Scalability Path (Phase 2+):**
- Migrate to Quix Streams or Kafka for production-scale streaming
- Add transformer-based sentiment analysis (batch mode)
- Consider serverless architecture (Lambda + DynamoDB)

**Decision Philosophy:** Choose technologies that balance MVP velocity (2-3 weeks), interview impact (modern 2025 stack), and clear production upgrade paths.

---

## Timeline

**Target MVP Delivery**: 2-3 weeks from project start

**Phase 1: Foundation (Week 1)**
- AWS setup and billing alerts configuration
- Reddit API OAuth registration
- QuestDB local development environment
- NCAA API integration and testing
- Basic Python data collection scripts

**Phase 2: Core Features (Week 2)**
- Reddit post tracking implementation
- Excitement score calculation algorithm
- QuestDB schema and time-series storage
- Basic React dashboard with timeline view
- Game state indicators (scheduled/live/complete)

**Phase 3: Polish & Deploy (Week 3)**
- Post-game summary feature
- Mobile-responsive design refinement
- Error handling and graceful degradation
- AWS EC2 deployment
- Documentation and README

**Phase 4: Iterate (Week 4+)**
- Monitor during live NCAA games
- Refine excitement algorithm based on real data
- Performance optimizations
- Prepare demo narrative for interviews

**Critical Milestone**: Fully functional before March Madness 2026 (March-April) for peak demo impact.

---

## Supporting Materials

This product brief incorporates insights from:

**Brainstorming Session (2025-11-06):**
- Explored data sources and use cases for sports analytics platform
- Identified compelling analytical questions (Reddit vs Vegas, tune-in recommendations)
- Prioritized three-phase roadmap: single-game → multi-game → betting analysis
- Generated 10+ ideas, converged on sports + social sentiment integration
- Reference: `docs/bmm-brainstorming-session-2025-11-06.md`

**Technical Research Report (2025-11-06):**
- Comprehensive 2025 technology validation across 20+ options
- Performance benchmarks: QuestDB 6.5x faster than alternatives
- Sports analytics market validation: $4.75B by 2030, 15.7% CAGR
- Data engineering job market alignment: real-time streaming "exploding in demand"
- All APIs verified active and accessible in 2025
- Reference: `docs/research-technical-2025-11-06.md`

**Key Insights Applied:**
- Pivoted from NBA (BALLDONTLIE too expensive) to NCAA (free API available)
- Chose post-level tracking over comment streaming (API efficiency)
- Selected QuestDB based on performance research (2025 time-series leader)
- Emphasized constraint-aware design (10-15 min updates acceptable)
- Positioned as "data engineering complexity" not "sports fan project"

---

_This Product Brief captures the vision and requirements for GamePulse._

_It was created through collaborative discovery and reflects the unique needs of this data engineering portfolio project._

_Next: The PRD workflow will transform this brief into detailed planning artifacts._
