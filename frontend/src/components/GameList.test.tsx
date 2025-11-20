import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { GameListResponse } from "../client/types.gen";
import * as useGamesHook from "../hooks/useGames";
import { render, screen, waitFor } from "../test-utils";
import { GameList } from "./GameList";

// Mock game list response factory
function createMockGameListResponse(games: any[] = []): GameListResponse {
  return {
    games,
    total_count: games.length,
    generated_at: "2025-11-16T20:00:00Z",
    requested_date: "2025-11-16",
  };
}

// Mock individual game
function createMockGame(overrides: any = {}) {
  return {
    game_key: Math.random(),
    game_id: "test_game",
    game_date: "2025-11-16T20:00:00Z",
    game_start_time: "2025-11-16T20:00:00-05:00",
    game_status: "scheduled",
    game_clock: null,
    away_team: {
      team_key: 1,
      team_id: "team_away",
      team_name: "Away Team",
      team_group_name: "Conference A",
      primary_color: "#FF0000",
      secondary_color: "#FFFFFF",
    },
    home_team: {
      team_key: 2,
      team_id: "team_home",
      team_name: "Home Team",
      team_group_name: "Conference B",
      primary_color: "#0000FF",
      secondary_color: "#FFFFFF",
    },
    away_score: 0,
    home_score: 0,
    ...overrides,
  };
}

// Helper to render GameList with QueryClient
function renderGameList() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <GameList />
    </QueryClientProvider>,
  );
}

describe("GameList", () => {
  describe("Loading State", () => {
    it("renders skeleton placeholders while loading", () => {
      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        isFetching: false,
      } as any);

      const { container } = renderGameList();

      // Chakra Skeleton components are rendered (check for multiple elements)
      const skeletons = container.querySelectorAll('[class*="skeleton"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Error States", () => {
    it("shows error message when fetch fails with no cached data", () => {
      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        isFetching: false,
      } as any);

      renderGameList();

      expect(
        screen.getByText(
          "Unable to load games. Please check that the backend is running.",
        ),
      ).toBeInTheDocument();
    });

    it("shows warning banner with cached data when fetch fails", () => {
      const cachedData = createMockGameListResponse([
        createMockGame({ game_status: "final" }),
      ]);

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: cachedData,
        isLoading: false,
        isError: true,
        isFetching: false,
      } as any);

      renderGameList();

      expect(
        screen.getByText(
          "Unable to fetch latest data. Showing cached results.",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("Away Team")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows empty message when no games scheduled", () => {
      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse([]),
        isLoading: false,
        isError: false,
        isFetching: false,
      } as any);

      renderGameList();

      expect(
        screen.getByText("No games scheduled for this date."),
      ).toBeInTheDocument();
    });
  });

  describe("Status Grouping", () => {
    it("groups games into Live, Final, and Upcoming sections", () => {
      const games = [
        createMockGame({ game_key: 1, game_status: "in_progress" }),
        createMockGame({ game_key: 2, game_status: "final" }),
        createMockGame({ game_key: 3, game_status: "scheduled" }),
      ];

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse(games),
        isLoading: false,
        isError: false,
        isFetching: false,
      } as any);

      renderGameList();

      expect(screen.getByText("Live Games")).toBeInTheDocument();
      expect(screen.getByText("Final Games")).toBeInTheDocument();
      expect(screen.getByText("Upcoming Games")).toBeInTheDocument();
    });

    it("hides empty sections", () => {
      const games = [
        createMockGame({ game_key: 1, game_status: "final" }),
        createMockGame({ game_key: 2, game_status: "final" }),
      ];

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse(games),
        isLoading: false,
        isError: false,
        isFetching: false,
      } as any);

      renderGameList();

      expect(screen.getByText("Final Games")).toBeInTheDocument();
      expect(screen.queryByText("Live Games")).not.toBeInTheDocument();
      expect(screen.queryByText("Upcoming Games")).not.toBeInTheDocument();
    });

    it("displays sections in correct order: Live → Final → Upcoming", () => {
      const games = [
        createMockGame({ game_key: 1, game_status: "scheduled" }),
        createMockGame({ game_key: 2, game_status: "in_progress" }),
        createMockGame({ game_key: 3, game_status: "final" }),
      ];

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse(games),
        isLoading: false,
        isError: false,
        isFetching: false,
      } as any);

      renderGameList();

      const headings = screen.getAllByRole("heading", { level: 2 });
      expect(headings[0]).toHaveTextContent("Live Games");
      expect(headings[1]).toHaveTextContent("Final Games");
      expect(headings[2]).toHaveTextContent("Upcoming Games");
    });
  });

  describe("Responsive Grid Layout", () => {
    it("renders games in a grid layout", () => {
      const games = [
        createMockGame({ game_key: 1, game_status: "final" }),
        createMockGame({ game_key: 2, game_status: "final" }),
      ];

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse(games),
        isLoading: false,
        isError: false,
        isFetching: false,
      } as any);

      renderGameList();

      // Verify games are rendered (grid layout is visual, tested manually)
      expect(screen.getByText("Final Games")).toBeInTheDocument();
      const awayTeams = screen.getAllByText("Away Team");
      expect(awayTeams.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Background Refetch Indicator", () => {
    it("shows updating indicator during background refetch", () => {
      const games = [createMockGame({ game_status: "final" })];

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse(games),
        isLoading: false,
        isError: false,
        isFetching: true, // Background refetch in progress
      } as any);

      renderGameList();

      expect(screen.getByText("Updating...")).toBeInTheDocument();
    });

    it("hides updating indicator when not refetching", () => {
      const games = [createMockGame({ game_status: "final" })];

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse(games),
        isLoading: false,
        isError: false,
        isFetching: false,
      } as any);

      renderGameList();

      expect(screen.queryByText("Updating...")).not.toBeInTheDocument();
    });
  });

  describe("Game Card Rendering", () => {
    it("renders GameCard components for each game", () => {
      const games = [
        createMockGame({
          game_key: 1,
          away_team: { ...createMockGame().away_team, team_name: "Duke" },
        }),
        createMockGame({
          game_key: 2,
          away_team: { ...createMockGame().away_team, team_name: "UNC" },
        }),
      ];

      vi.spyOn(useGamesHook, "useGames").mockReturnValue({
        data: createMockGameListResponse(games),
        isLoading: false,
        isError: false,
        isFetching: false,
      } as any);

      renderGameList();

      expect(screen.getByText("Duke")).toBeInTheDocument();
      expect(screen.getByText("UNC")).toBeInTheDocument();
    });
  });
});
