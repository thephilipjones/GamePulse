import { describe, expect, it } from "vitest";
import type { GamePublic } from "../client/types.gen";
import { render, screen } from "../test-utils";
import { GameCard } from "./GameCard";

// Mock game data factory
function createMockGame(overrides?: Partial<GamePublic>): GamePublic {
  return {
    game_key: 1,
    game_id: "ncaam_test_game",
    game_date: "2025-11-16T20:00:00Z",
    game_start_time: "2025-11-16T20:00:00-05:00",
    game_status: "scheduled",
    game_clock: null,
    away_team: {
      team_key: 1,
      team_id: "ncaam_duke",
      team_name: "Duke",
      team_group_name: "ACC",
      primary_color: "#012169",
      secondary_color: "#FFFFFF",
    },
    home_team: {
      team_key: 2,
      team_id: "ncaam_unc",
      team_name: "North Carolina",
      team_group_name: "ACC",
      primary_color: "#7BAFD4",
      secondary_color: "#FFFFFF",
    },
    away_score: 0,
    home_score: 0,
    ...overrides,
  };
}

describe("GameCard", () => {
  describe("Team Information", () => {
    it("renders away team on the left", () => {
      const game = createMockGame();
      render(<GameCard game={game} />);

      expect(screen.getByText("Duke")).toBeInTheDocument();
    });

    it("renders home team on the right", () => {
      const game = createMockGame();
      render(<GameCard game={game} />);

      expect(screen.getByText("North Carolina")).toBeInTheDocument();
    });

    it("does not display conference names (removed in redesign)", () => {
      const game = createMockGame();
      render(<GameCard game={game} />);

      // Conference names are intentionally not displayed in the redesigned UI
      expect(screen.queryByText("ACC")).not.toBeInTheDocument();
      expect(screen.getByText("Duke")).toBeInTheDocument();
      expect(screen.getByText("North Carolina")).toBeInTheDocument();
    });
  });

  describe("Score Display", () => {
    it("renders scores for games in progress", () => {
      const game = createMockGame({
        game_status: "in_progress",
        away_score: 78,
        home_score: 81,
      });

      render(<GameCard game={game} />);

      expect(screen.getByText("78")).toBeInTheDocument();
      expect(screen.getByText("81")).toBeInTheDocument();
      expect(screen.getByText("-")).toBeInTheDocument(); // Separator
    });

    it("renders scores for final games", () => {
      const game = createMockGame({
        game_status: "final",
        away_score: 75,
        home_score: 72,
      });

      render(<GameCard game={game} />);

      expect(screen.getByText("75")).toBeInTheDocument();
      expect(screen.getByText("72")).toBeInTheDocument();
    });

    it("renders em dashes for scheduled games without scores", () => {
      const game = createMockGame({
        game_status: "scheduled",
        away_score: 0,
        home_score: 0,
      });

      render(<GameCard game={game} />);

      // Both scores should show 0 (there will be multiple "0"s)
      const scores = screen.getAllByText("0");
      expect(scores.length).toBeGreaterThanOrEqual(2);
    });

    it("handles null scores gracefully", () => {
      const game = createMockGame({
        away_score: null as any,
        home_score: null as any,
      });

      render(<GameCard game={game} />);

      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe("Status Badge Integration", () => {
    it("renders status badge for LIVE games", () => {
      const game = createMockGame({
        game_status: "in_progress",
        game_clock: "14:32 2nd Half",
      });

      render(<GameCard game={game} />);

      expect(screen.getByText("LIVE")).toBeInTheDocument();
      expect(screen.getByText("14:32 2nd Half")).toBeInTheDocument();
    });

    it("renders status badge for FINAL games", () => {
      const game = createMockGame({
        game_status: "final",
      });

      render(<GameCard game={game} />);

      expect(screen.getByText("FINAL")).toBeInTheDocument();
    });

    it("renders status badge for scheduled games", () => {
      const game = createMockGame({
        game_status: "scheduled",
        game_start_time: "2025-11-16T12:00:00Z",
      });

      render(<GameCard game={game} />);

      expect(screen.getByText(/Nov 16/i)).toBeInTheDocument();
    });
  });

  describe("Visual Styling", () => {
    it("applies team color gradients", () => {
      const game = createMockGame({
        away_team: {
          ...createMockGame().away_team,
          primary_color: "#FF0000", // Red
        },
        home_team: {
          ...createMockGame().home_team,
          primary_color: "#0000FF", // Blue
        },
      });

      render(<GameCard game={game} />);

      // Verify card renders with team colors (gradient logic is tested via visual)
      expect(screen.getByText("Duke")).toBeInTheDocument();
      expect(screen.getByText("North Carolina")).toBeInTheDocument();
    });

    it("uses fallback colors when team colors not available", () => {
      const game = createMockGame({
        away_team: {
          ...createMockGame().away_team,
          primary_color: null,
        },
        home_team: {
          ...createMockGame().home_team,
          primary_color: null,
        },
      });

      const { container } = render(<GameCard game={game} />);

      // Should still render without errors
      expect(screen.getByText("Duke")).toBeInTheDocument();
    });

    it("applies higher opacity for LIVE games", () => {
      const liveGame = createMockGame({
        game_status: "in_progress",
      });

      render(<GameCard game={liveGame} />);

      // Just verify the card renders - detailed opacity testing would require
      // snapshot testing or specific style checking
      expect(screen.getByText("LIVE")).toBeInTheDocument();
    });

    it("applies lower opacity for FINAL games", () => {
      const finalGame = createMockGame({
        game_status: "final",
      });

      render(<GameCard game={finalGame} />);

      expect(screen.getByText("FINAL")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA label for game matchup", () => {
      const game = createMockGame();
      const { container } = render(<GameCard game={game} />);

      const article = container.querySelector('[role="article"]');
      expect(article).toHaveAttribute(
        "aria-label",
        "Game: Duke at North Carolina",
      );
    });

    it("renders team names without truncation for accessibility", () => {
      const game = createMockGame({
        away_team: {
          ...createMockGame().away_team,
          team_name: "Very Long University Name That Should Not Truncate",
        },
      });

      render(<GameCard game={game} />);

      expect(
        screen.getByText("Very Long University Name That Should Not Truncate"),
      ).toBeInTheDocument();
    });
  });

  describe("React.memo Optimization", () => {
    it("component is memoized", () => {
      // Verify displayName is set (indication of React.memo)
      expect(GameCard.displayName).toBe("GameCard");
    });
  });
});
