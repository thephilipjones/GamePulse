# Story 4-9: Enhanced Game Card UI Design

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-9
**Status:** ready-for-dev
**Date Drafted:** 2025-11-16
**Date Ready:** 2025-11-16
**Estimated Effort:** 8-12 hours
**Priority:** High (Week 2 - User-facing feature)
**Dependencies:** Story 3.4 (Basic Game List Component), Story 2-3b (Team colors available)

## Dev Agent Record

### Context Reference
- `docs/stories/4-9-game-card-ui-design.context.xml` - Story context with documentation artifacts, code references, interfaces, constraints, and testing guidance

---

## User Story

**As a** basketball fan,
**I want** to see visually appealing game cards with team branding, scores, and game status,
**So that** I can quickly scan multiple games and identify which ones are live, finished, or upcoming.

---

## Context

Story 3.4 created a basic GameList component showing team names and scores in a simple card layout. This story transforms it into a polished, story-driven interface that:

1. **Groups games by status** for better scanability (Live → Final → Scheduled)
2. **Uses team branding** (colors, logos) for visual recognition
3. **Shows game context** (time remaining, final status, start time)
4. **Provides visual hierarchy** to highlight live games

**Success Criteria:** Users can glance at the dashboard and immediately identify which games are happening now, which just finished, and which are upcoming - all with rich team branding.

---

## Dev Notes for Developer

### Architecture Patterns and Constraints

**Frontend Component Architecture:**

- Extend existing `GameList.tsx` component (don't rebuild from scratch)
- Use Chakra UI design tokens for consistency
- Implement responsive design (mobile-first approach)
- Team colors from `dim_team.primary_color` and `secondary_color` (hex codes)
- Game status grouping logic in frontend (backend returns flat list)

**Game Status Grouping Logic:**

```typescript
// Group games by status in this specific order
const groupedGames = {
  in_progress: games.filter(g => g.game_status === "in_progress"),
  final: games.filter(g => g.game_status === "final"),
  scheduled: games.filter(g => g.game_status === "scheduled")
}

// Render order: Live games first, then Final, then Scheduled
```

**Design Principles:**

- **Live games** (in_progress): Bold styling, pulsing indicator, prominent placement
- **Final games**: Muted colors, final score emphasis
- **Scheduled games**: Lighter styling, show start time instead of score

### Learnings from Previous Stories

**Source:** [Story 3.4: Build Simple Game List Component](story-3.4-build-game-list.md)

Story 3.4 established the basic GameList foundation:

**Key Components:**
- `frontend/src/components/GameList.tsx` - List container with loading/error states
- `frontend/src/hooks/useGames.ts` - TanStack Query hook with 1-minute polling
- `frontend/src/routes/_layout/index.tsx` - Dashboard page

**Existing Features:**
- ✅ Auto-refresh every 60 seconds
- ✅ Loading skeleton states
- ✅ Error handling with retry
- ✅ Team names and scores displayed
- ✅ Basic team color left border accent

**Implications for Story 4-9:**

- Build on existing GameList component structure
- Preserve loading/error handling logic (don't regress)
- Enhance visual design without breaking polling behavior
- Team colors already available in API response (`home_team.primary_color`)

### Project Structure Notes

**Frontend Code Organization:**

```
frontend/src/
├── components/
│   ├── GameList.tsx              # THIS STORY: Major enhancements
│   ├── GameCard.tsx              # NEW: Extract card logic from GameList
│   └── GameStatusBadge.tsx       # NEW: Status indicator component
├── hooks/
│   └── useGames.ts               # Unchanged (already polling at 1 minute)
├── routes/
│   └── _layout/
│       └── index.tsx             # Minor updates (section headers)
└── theme/
    └── index.ts                  # May add custom color tokens
```

**Component Hierarchy (Proposed):**

```
<Box> (Dashboard container)
  └── <Heading> "Live Games" (if any in_progress games)
      └── <GameList> (in_progress games)
          └── <GameCard> (individual game)
              ├── <GameStatusBadge> "LIVE"
              ├── <HStack> Team names with colors
              ├── <Text> Scores
              └── <Text> Time remaining

  └── <Heading> "Final Games" (if any final games)
      └── <GameList> (final games)
          └── <GameCard>
              ├── <GameStatusBadge> "FINAL"
              └── ... (similar structure)

  └── <Heading> "Upcoming Games" (if any scheduled games)
      └── <GameList> (scheduled games)
          └── <GameCard>
              ├── <GameStatusBadge> Start time
              └── ... (similar structure)
```

### Design Specifications

**Game Status Values (Backend):**
- Source: `backend/app/models/fact_game.py` line 43-45
- Enum values: `"scheduled"`, `"in_progress"`, `"final"` (string literals, not Python Enum)

**Status Display Mapping:**

| Backend Status | Display Text | Badge Color | Visual Indicator |
|----------------|--------------|-------------|------------------|
| `in_progress` | "LIVE" | Red (red.500) | Pulsing dot animation |
| `final` | "FINAL" | Gray (gray.500) | Static badge |
| `scheduled` | Start time (e.g., "8:00 PM ET") | Blue (blue.500) | Static badge |

**Time Display Logic:**

```typescript
// For in_progress games
if (game.game_status === "in_progress") {
  timeDisplay = game.game_clock; // "14:32 2nd Half"
}

// For scheduled games
if (game.game_status === "scheduled") {
  timeDisplay = formatStartTime(game.game_start_time); // "8:00 PM ET"
}

// For final games
if (game.game_status === "final") {
  timeDisplay = "FINAL";
}
```

**Team Color Usage:**

```typescript
// Home team accent (left border or background gradient)
<Box borderLeft="4px solid" borderColor={game.home_team.primary_color}>
  {/* Card content */}
</Box>

// Away team accent (right border)
<Box borderRight="4px solid" borderColor={game.away_team.primary_color}>
  {/* Card content */}
</Box>

// Alternative: Gradient background
<Box
  bgGradient={`linear(to-r, ${game.home_team.primary_color}20, ${game.away_team.primary_color}20)`}
>
  {/* Subtle team color wash */}
</Box>
```

**Responsive Breakpoints:**

- **Mobile (<768px):** Single column, stacked layout
- **Tablet (768px-1024px):** Two-column grid
- **Desktop (>1024px):** Three-column grid

**Mockup References:**

The user provided directional mockups (not pixel-perfect specs):
- Desktop: `/Users/Philip/dev/gamepulse/docs/gamepulse-1-desktop.png`
- Mobile: `/Users/Philip/dev/gamepulse/docs/gamepulse-1-mobile.png`

Key design elements from mockups:
- Team logos/initials in circular badges (e.g., "DU" for Duke)
- Large score display (center of card)
- Sentiment badge in top-right corner (Story 5-1, not this story)
- Momentum graph below scores (Epic 5, not this story)
- "Top Moments" section (Story 4-10, not this story)

**For Story 4-9, implement:**
- ✅ Team badges with initials/abbreviations
- ✅ Score display
- ✅ Status badges (LIVE/FINAL/start time)
- ✅ Team color accents
- ❌ Sentiment score (deferred to Epic 5)
- ❌ Momentum graph (deferred to Epic 5)
- ❌ Top Moments (deferred to Story 4-10)

### Accessibility Considerations

**Color Contrast:**
- Team colors may not meet WCAG AA contrast ratios
- Always provide text labels in addition to color coding
- Use Chakra UI's color mode aware utilities

**Screen Readers:**
- Status badges should have aria-labels: `<Badge aria-label="Game is live">`
- Team logos should have alt text: `<Image alt="Duke Blue Devils logo" />`
- Scores should be announced: "Duke 78, UNC 81"

**Keyboard Navigation:**
- Game cards should be focusable (future: clickable to detail page)
- Tab order: Live games → Final games → Scheduled games

### Performance Considerations

**Rendering Optimization:**

- Use React.memo for GameCard component (prevent unnecessary re-renders)
- Virtual scrolling if >50 games (unlikely for daily games, but good practice)
- Image optimization: Use Next.js Image component if logos added

**Data Flow:**

```
TanStack Query (useGames hook)
  → Polls GET /api/v1/games?date=YYYY-MM-DD every 60 seconds
  → Returns GameListResponse with games[]
  → Component groups by status
  → Renders grouped sections
```

**No Backend Changes Required:**
- API already returns `game_status`, `game_clock`, team colors
- Frontend handles grouping logic (keeps backend simple)

### Testing Strategy

**Component Tests (Vitest + React Testing Library):**

```typescript
describe('GameList with grouping', () => {
  it('should group games by status in correct order', () => {
    const games = [
      { game_status: 'final', ... },
      { game_status: 'in_progress', ... },
      { game_status: 'scheduled', ... },
    ];

    render(<GameList games={games} />);

    const sections = screen.getAllByRole('heading');
    expect(sections[0]).toHaveTextContent('Live Games');
    expect(sections[1]).toHaveTextContent('Final Games');
    expect(sections[2]).toHaveTextContent('Upcoming Games');
  });

  it('should show LIVE badge for in_progress games', () => {
    const game = { game_status: 'in_progress', ... };
    render(<GameCard game={game} />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
  });

  it('should format start time for scheduled games', () => {
    const game = {
      game_status: 'scheduled',
      game_start_time: '2025-11-16T20:00:00Z',
      ...
    };
    render(<GameCard game={game} />);
    expect(screen.getByText(/8:00 PM/)).toBeInTheDocument();
  });

  it('should apply team colors as border accents', () => {
    const game = {
      home_team: { primary_color: '#012169' },
      away_team: { primary_color: '#7BAFD4' },
      ...
    };
    render(<GameCard game={game} />);
    const card = screen.getByTestId('game-card');
    expect(card).toHaveStyle({ borderLeftColor: '#012169' });
  });
});
```

**Visual Regression Tests (Chromatic/Percy - Optional):**
- Capture screenshots of grouped games in different states
- Verify responsive breakpoints (mobile, tablet, desktop)
- Test dark mode compatibility

**Manual Testing:**

1. Wait for live game to appear (game_status = "in_progress")
   - Verify LIVE badge shows
   - Verify time remaining displays (game_clock)
   - Verify live game appears in "Live Games" section first

2. Wait for game to finish (game_status = "final")
   - Verify game moves to "Final Games" section
   - Verify FINAL badge replaces LIVE badge
   - Verify final score displayed

3. View scheduled games (game_status = "scheduled")
   - Verify start time displays instead of score
   - Verify games appear in "Upcoming Games" section

4. Test responsive design
   - Resize browser from mobile → desktop
   - Verify grid columns adjust (1 → 2 → 3)
   - Verify text remains readable on mobile

### API Data Structure Reference

**GamePublic Schema (from backend):**

```typescript
interface GamePublic {
  game_key: number;
  game_id: string;
  game_date: string;
  game_start_time: string;
  game_status: "scheduled" | "in_progress" | "final";
  game_clock?: string | null;  // "14:32 2nd Half" or null
  home_team: {
    team_key: number;
    team_id: string;
    team_name: string;
    team_group_name: string;
    primary_color: string;      // Hex code "#012169"
    secondary_color?: string;   // Hex code "#FFFFFF"
  };
  away_team: {
    // Same structure as home_team
  };
  home_score: number;
  away_score: number;
  venue?: string | null;
  broadcast_network?: string | null;
}
```

**Already Available (No API Changes Needed):**
- ✅ `game_status` for grouping
- ✅ `game_clock` for time remaining
- ✅ `game_start_time` for scheduled games
- ✅ `primary_color` and `secondary_color` for team branding

### Future Enhancements (Out of Scope)

**Story 4-9 focuses on visual design only. Future stories will add:**

- **Story 4-10:** Social posts feed below each game card
- **Story 5-1:** Excitement score badge (sentiment-based ranking)
- **Epic 5:** Momentum graph visualization
- **Epic 8:** Clickable game cards → detail page
- **Epic 8:** Team logos from NCAA API or external source

---

## Acceptance Criteria Hints

### AC-4.9.1: Game Status Grouping
- [ ] Games grouped into three sections: "Live Games", "Final Games", "Upcoming Games"
- [ ] Section order: Live → Final → Upcoming (matches user scanning priority)
- [ ] Empty sections hidden (no "No live games" placeholder text)
- [ ] Sections have clear visual separation (headings, spacing)

### AC-4.9.2: Status Badges
- [ ] `in_progress` games show "LIVE" badge in red (Chakra red.500)
- [ ] LIVE badge has pulsing animation (CSS keyframe or Chakra animation)
- [ ] `final` games show "FINAL" badge in gray (Chakra gray.500)
- [ ] `scheduled` games show formatted start time (e.g., "8:00 PM ET")
- [ ] Badge styling consistent with Chakra UI Badge component

### AC-4.9.3: Time Display
- [ ] `in_progress` games: Display `game_clock` value (e.g., "14:32 2nd Half")
- [ ] `final` games: Display "FINAL" text
- [ ] `scheduled` games: Display formatted start time from `game_start_time` (convert UTC to ET)
- [ ] Time updates every 60 seconds via existing polling (no regression)

### AC-4.9.4: Team Branding
- [ ] Team abbreviations displayed (e.g., "DU" for Duke, "UNC" for North Carolina)
  - Extract from `team_name` (first 2-3 characters or common abbreviations)
- [ ] Team colors used as visual accents (border, background, or badge)
- [ ] Home team color: Left border (4px solid) using `home_team.primary_color`
- [ ] Away team color: Right border (4px solid) using `away_team.primary_color`
- [ ] Colors render correctly as hex codes (no color conversion issues)

### AC-4.9.5: Score Display
- [ ] Scores prominently displayed (large font size, center of card)
- [ ] Home score on left, away score on right
- [ ] Score format: "78 - 81" or "78  81" (clear separation)
- [ ] `scheduled` games: Show "—" or hide scores (game hasn't started)
- [ ] Scores update live for `in_progress` games (via polling)

### AC-4.9.6: Responsive Design
- [ ] Mobile (<768px): Single column layout, cards stack vertically
- [ ] Tablet (768px-1024px): Two-column grid
- [ ] Desktop (>1024px): Three-column grid
- [ ] Card layout readable on all screen sizes (text doesn't wrap awkwardly)
- [ ] Touch-friendly tap targets on mobile (min 44x44px)

### AC-4.9.7: Loading and Error States
- [ ] Loading skeleton preserves grouped section layout (Live/Final/Upcoming placeholders)
- [ ] Error state shows user-friendly message (no raw error text)
- [ ] Retry logic works (TanStack Query automatic retry)
- [ ] No visual regression from Story 3.4 (existing states still work)

### AC-4.9.8: Performance
- [ ] GameCard component wrapped in React.memo (prevent unnecessary re-renders)
- [ ] No layout shift when games transition between sections (stable UI)
- [ ] Polling continues at 60-second interval (no change from Story 3.6)
- [ ] Page renders within 500ms on 4G connection

### AC-4.9.9: Accessibility
- [ ] Status badges have aria-labels: "Game is live", "Game is final", etc.
- [ ] Team names announced by screen readers
- [ ] Color contrast meets WCAG AA (text on background, not color alone)
- [ ] Keyboard navigation works (tab through cards in logical order)

### AC-4.9.10: Verification Queries
```sql
-- Verify team colors exist for all teams in today's games
SELECT
  t.team_id,
  t.team_name,
  t.primary_color,
  t.secondary_color
FROM dim_team t
JOIN fact_game fg ON (fg.home_team_key = t.team_key OR fg.away_team_key = t.team_key)
WHERE fg.game_date = CURRENT_DATE
  AND t.is_current = TRUE
  AND (t.primary_color IS NULL OR t.secondary_color IS NULL);
-- Should return 0 rows (all teams have colors)

-- Check game status distribution
SELECT
  game_status,
  COUNT(*) as num_games
FROM fact_game
WHERE game_date = CURRENT_DATE
GROUP BY game_status;
-- Verify all statuses are "scheduled", "in_progress", or "final"
```

---

## Dependencies

**Required (Must be complete):**
- ✅ Story 3.4: Basic Game List Component (foundation)
- ✅ Story 2-3b: Team metadata sync (team colors available)
- ✅ Story 3.6: 1-minute polling (live feel)

**Nice to Have (Can proceed without):**
- Story 4-10: Social posts feed (this story only does card layout, not posts)
- Story 5-1: Excitement scoring (deferred to Epic 5)

---

## Files Modified

**Primary Changes:**
- `frontend/src/components/GameList.tsx` - Add grouping logic, section headers
- `frontend/src/components/GameCard.tsx` - NEW: Extract card component
- `frontend/src/components/GameStatusBadge.tsx` - NEW: Status indicator
- `frontend/src/routes/_layout/index.tsx` - Update layout for grouped sections

**Tests:**
- `frontend/src/components/GameList.test.tsx` - NEW: Component tests
- `frontend/src/components/GameCard.test.tsx` - NEW: Card tests

**Optional:**
- `frontend/src/theme/index.ts` - Custom color tokens if needed

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Team colors don't meet contrast ratio | Medium | Low | Fallback to Chakra color tokens, add text labels |
| Status grouping breaks existing polling | Low | Medium | Preserve useGames hook unchanged, test thoroughly |
| Responsive layout breaks on edge cases | Medium | Low | Test on real devices (iOS Safari, Android Chrome) |
| Performance degrades with >50 games | Very Low | Low | Unlikely (max ~20-30 games/day), add virtual scrolling later |

**Overall Risk:** **LOW** - Well-scoped visual enhancement, no backend changes.

---

## Success Metrics

- ✅ Users can identify live games in <2 seconds (visual prominence)
- ✅ Game status transitions (scheduled → live → final) reflected within 60 seconds
- ✅ Team branding visible (colors, names, abbreviations)
- ✅ Responsive design works on mobile, tablet, desktop
- ✅ No performance regression (page load <500ms, re-render <50ms)

---

## References

- Mockups: `docs/gamepulse-1-desktop.png`, `docs/gamepulse-1-mobile.png`
- Story 3.4: [Build Simple Game List Component](story-3.4-build-game-list.md)
- Story 3.6: [Increase Refresh Cadence to 1 Minute](../epics.md#story-36)
- Backend Model: `backend/app/models/fact_game.py` (game_status enum)
- Frontend Hook: `frontend/src/hooks/useGames.ts` (60-second polling)
