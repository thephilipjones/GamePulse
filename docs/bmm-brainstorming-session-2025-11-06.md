# Brainstorming Session Results

**Session Date:** 2025-11-06
**Facilitator:** Business Analyst Mary
**Participant:** Philip

## Executive Summary

**Topic:** Data Engineering Portfolio Project - Data Sources and Use Cases

**Session Goals:** Explore compelling data sources and use cases that demonstrate real-world data engineering skills, create interesting analytical stories, and impress interviewers with both technical depth and business impact

**Techniques Used:** What If Scenarios (Creative), Forced Relationships (partial - pivoted early to convergence)

**Total Ideas Generated:** 10+ major concepts explored, 3 prioritized for MVP implementation

### Key Themes Identified:

1. **Real-time Streaming Data as Differentiator** - Portfolio projects that process live data demonstrate more advanced engineering skills than batch-only systems

2. **Multi-Source Integration Creates Compelling Stories** - Combining game data + social sentiment + betting lines tells richer analytical narratives than single-source analysis

3. **Incremental MVP Approach** - Build foundational single-game analysis (#1), scale to multi-game portfolio view (#2), add predictive analytics layer (#3)

4. **Interview Storytelling Through Questions** - Frame features around compelling questions ("Does Reddit know better than Vegas?") rather than technical implementation details

5. **Free API Constraints Drive Creative Solutions** - Rate limits and cost constraints force strategic decisions about what to monitor and when, demonstrating real-world engineering trade-offs

6. **Business Value Through Betting Vertical** - Sports gambling provides clear business context that resonates with data science interviewers

7. **User-Centric Design for Portfolio** - "Should I tune in?" addresses real user need while showcasing product thinking alongside technical skills

## Technique Sessions

### Technique 1: What If Scenarios (Creative Exploration)

**Focus:** Exploring data source combinations without constraints

**Ideas Generated:**

**Sports Analytics Ecosystem (PRIMARY DIRECTION):**
- **Core concept:** Multi-source sports data platform combining real-time game data, social sentiment, betting lines, and viewership
- **Sports focus (priority order):** NFL, NCAAM, MLB
- **Data sources identified:**
  - Live game data (scores, play-by-play)
  - Reddit game threads (real-time sentiment)
  - Twitter/social volume and sentiment
  - Betting line movements
  - Viewership data (if available)
  - Player injury reports/news
  - Weather, historical matchups
  - Discord/Twitch betting/watch party activity

**Key Analytical Questions (HIGH INTEREST):**
1. Can you detect when Reddit sentiment diverges from betting lines? (Wisdom of crowds vs Vegas)
2. Does social media hype predict viewership surges?
3. When does a game become "must-watch" in real-time?
4. Can you spot the moment a game "breaks" the internet?
5. Which plays/moments go viral instantly?

**Alternative angles explored:**
- Personal data integration (watch patterns, fantasy decisions) - interesting but not primary focus
- End-user perspective: "Should I tune into this game RIGHT NOW?" dashboard
- Predicting the conversation, not just the outcome

**Other Creative Directions (explored but lower priority):**
- Sentiment analysis on non-financial data (health inspections, game reviews)
- Wikipedia edit wars in real-time
- Meme propagation speed across platforms
- Flight delay cascade networks

**Research needed:** API availability and costs for sports data feeds

## Idea Categorization

### Immediate Opportunities

_Ideas ready to implement now_

Based on free API research, these three features are buildable with BALLDONTLIE + PRAW + VADER + The Odds API:

1. Reddit Sentiment + Game Data Correlation
2. "Should I Tune In?" Multi-Game Dashboard
3. Social Buzz + Betting Lines Divergence

### Future Innovations

_Ideas requiring development/research_

[To be captured]

### Moonshots

_Ambitious, transformative concepts_

[To be captured]

### Insights and Learnings

_Key realizations from the session_

[To be captured]

## Action Planning

### Top 3 Priority Ideas

#### #1 Priority: Reddit Sentiment + Game Data Correlation

**Description:** Track live game threads during NFL/NBA games, correlate sentiment shifts with score changes, visualize the "story of the game" over time with representative (upvoted) comments at significant moments. Display daily summary view sorted by "exciting-ness".

**Rationale:**
- Demonstrates MVP and incremental building approach
- Tells the narrative story of the game through data
- Combines time series visualization, sentiment analysis, and real-time data ingestion
- Creates foundation for other features
- Shows both quantitative (sentiment scores) and qualitative (actual comments) analysis

**Next steps:**
1. Set up PRAW (Reddit API) with OAuth authentication
2. Implement VADER sentiment analysis on Reddit comments
3. Integrate BALLDONTLIE API for live game scores/events
4. Build data pipeline: Reddit stream → sentiment analysis → storage
5. Create time series visualization showing sentiment + score correlation
6. Implement "exciting-ness" ranking algorithm for daily summary
7. Design responsive web dashboard

**Resources needed:**
- BALLDONTLIE API (free, 60 req/min)
- Reddit API via PRAW (free, OAuth setup required)
- VADER sentiment library (Python, free)
- PostgreSQL or time series database
- Python + PySpark for data processing
- JavaScript/CSS framework for frontend visualization
- AWS free tier: RDS or EC2 for database, EC2 for web hosting

**Timeline:** MVP in 2-3 weeks, iterate from there

**Technical skills demonstrated:** Real-time streaming, sentiment analysis, time series analysis, API integration, rate limit management, data visualization, full-stack development

#### #2 Priority: "Should I Tune In?" Multi-Game Dashboard

**Description:** Real-time multi-game tracker showing which games have hot Reddit threads. Ranked by excitement metric (Reddit volume, sentiment swings, comment velocity). Mobile-first glanceable design answering "what should I be watching right now?"

**Rationale:**
- Builds on #1's infrastructure but scales to ALL games happening simultaneously
- Demonstrates aggregation algorithms and real-time ranking
- Shows architectural thinking: single-game analysis → portfolio view
- Mobile-first UX consideration demonstrates product thinking
- Solves real user problem (choice paralysis when many games on)

**Next steps:**
1. Extend #1's pipeline to monitor multiple game threads concurrently
2. Design excitement scoring algorithm (volume, velocity, sentiment volatility)
3. Build aggregation layer for multi-game comparison
4. Implement real-time ranking/sorting
5. Create mobile-responsive dashboard with auto-refresh
6. Optimize for API rate limits (60 req/min = 10 games @ 10-second updates)

**Resources needed:**
- Same APIs as #1 (BALLDONTLIE + PRAW + VADER)
- Enhanced data pipeline for concurrent streams
- Caching layer for rate limit optimization
- Mobile-responsive frontend framework

**Timeline:** 1-2 weeks after #1 MVP (reuses infrastructure)

**Technical skills demonstrated:** Scaling architecture, concurrent data streams, ranking algorithms, rate limit optimization, responsive design, real-time aggregation

#### #3 Priority: Social Buzz + Betting Lines Divergence

**Description:** Compare pregame betting odds with Reddit sentiment to detect divergence between "what Vegas thinks" vs "what Reddit thinks". Track which source is more accurate over time. Answer: does social sentiment contain signal or just noise?

**Rationale:**
- Provides compelling interview discussion angle around data science fundamentals
- Introduces "wisdom of crowds" vs professional oddsmakers question
- Clear business value connection (betting markets, real money)
- Demonstrates predictive modeling and statistical analysis thinking
- Data integration challenge: merging odds data with sentiment data
- Creates analytical "punchline" for portfolio demo

**Next steps:**
1. Integrate The Odds API (500 requests/month = ~16/day pregame odds)
2. Capture pregame Reddit sentiment from pre-game threads
3. Store odds + sentiment + actual game outcomes
4. Build analysis pipeline comparing predictions to results
5. Visualize divergence with scatter plots, accuracy metrics
6. Calculate "who was right?" statistics over time
7. Create narrative around findings for portfolio storytelling

**Resources needed:**
- The Odds API (free tier, 500 req/month)
- Historical game outcome data
- Statistical analysis tools (pandas, scipy)
- Visualization library for divergence plots
- Same infrastructure as #1/#2

**Timeline:** 1-2 weeks after #2 (adds new data source + analysis layer)

**Technical skills demonstrated:** Predictive analytics, statistical validation, data integration across disparate sources, hypothesis testing, business value articulation, storytelling with data

**Cost constraint note:** 16 daily requests = ~8 games pregame odds (if checking multiple bookmakers) OR 16 games single bookmaker. Strategic selection required.

## Reflection and Follow-up

### What Worked Well

- **Flexible approach adaptation:** Quickly pivoted from Progressive Flow (4 techniques, 60 min) to AI-Recommended (2 techniques, 30 min) when user wanted lighter exploration - kept session productive without feeling forced
- **Real constraints integration:** Mid-session API research findings grounded creative ideas in reality without killing momentum - transformed "what if" into "here's how"
- **Focus discipline:** Stayed targeted on data sources/use cases rather than drifting into infrastructure decisions (saved for Architecture workflow)
- **Incremental thinking:** User naturally identified MVP → scale → analytics progression showing product maturity
- **Convergence efficiency:** Moved to prioritization when direction was clear rather than over-brainstorming

### Areas for Further Exploration

**Technical deep-dives (for Research workflow):**
- Specific API authentication flows and quota management strategies
- PRAW Reddit streaming vs polling trade-offs
- Time series database options (PostgreSQL with TimescaleDB vs InfluxDB vs others)
- PySpark streaming architecture for real-time sentiment analysis
- Frontend framework selection (React vs Vue vs Svelte for real-time dashboards)

**Product decisions (for Product Brief / PRD):**
- Initial sport focus: NFL only for MVP, or multi-sport from day 1?
- Target audience definition: yourself as user, hiring managers as audience, or actual sports fans?
- "Exciting-ness" algorithm: what variables drive the score?
- Historical data strategy: start fresh from launch date or scrape/buy historical data?

**Business/portfolio strategy:**
- Project naming and branding
- Demo storytelling structure for interviews
- Which features to showcase in portfolio vs keep in codebase
- Technical blog post topics to accompany project

### Recommended Follow-up Techniques

For future brainstorming sessions as the project evolves:

- **First Principles Thinking** - When facing architectural trade-offs, strip away assumptions to find optimal solutions
- **SCAMPER Method** - When iterating on existing features (Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse)
- **Assumption Reversal** - Challenge core assumptions about what makes sports data interesting or how users would interact

### Questions That Emerged

**Data & APIs:**
1. Which specific Reddit communities have the most active game threads? (r/nfl, r/nba, team-specific subreddits?)
2. How do we handle deleted comments or moderated content in sentiment analysis?
3. What's the actual latency between game events and Reddit reactions?
4. Can we access comment edit history or just final state?

**Technical Architecture:**
5. Real-time streaming vs micro-batch processing - what's the right trade-off?
6. How to handle API failures gracefully during live games?
7. What's the storage strategy for historical sentiment data - keep everything or aggregate?
8. How to make the excitement algorithm explainable to interviewers?

**Product & UX:**
9. What makes a game "exciting" - is it absolute sentiment levels or rate of change?
10. Should the dashboard show games that haven't started yet (pregame hype)?
11. How to visualize sentiment over time - line chart, heatmap, something else?
12. Mobile-first means what exactly - native app or responsive web?

**Portfolio Strategy:**
13. Should this be one unified platform or three separate demo projects?
14. What's the right balance between "production-ready" and "portfolio demo"?
15. How much to invest in DevOps/deployment vs feature development?

### Next Session Planning

- **Suggested topics:**
  1. **Research workflow** (NEXT IMMEDIATE): Deep-dive into API specifics, authentication flows, rate limit strategies, data availability, and alternative data sources
  2. **Product Brief workflow**: Articulate portfolio project vision, target audience (hiring managers/interviewers), success metrics, and personal brand positioning
  3. **Architecture brainstorming**: Once APIs confirmed, explore system design trade-offs (streaming vs batch, database selection, AWS service choices)

- **Recommended timeframe:**
  - Research workflow: Within 1-2 days while momentum is high
  - Product Brief: After research findings available
  - Rest of BMM workflow as planned

- **Preparation needed:**
  - Create Reddit developer account and test PRAW authentication
  - Sign up for The Odds API and BALLDONTLIE API to verify access
  - Explore r/nfl and r/nba game thread structures
  - Review AWS free tier limits and services
  - Sketch rough system architecture diagram to guide research questions

---

_Session facilitated using the BMAD CIS brainstorming framework_
