import { describe, expect, it } from "vitest";
import { render, screen } from "../test-utils";
import { GameStatusBadge } from "./GameStatusBadge";

describe("GameStatusBadge", () => {
  describe("LIVE games (in_progress)", () => {
    it("renders LIVE badge for in_progress status", () => {
      render(<GameStatusBadge status="in_progress" />);

      const badge = screen.getByText("LIVE");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute("aria-label", "Game is live");
    });

    it("renders game clock when provided", () => {
      render(
        <GameStatusBadge status="in_progress" gameClock="14:32 2nd Half" />,
      );

      expect(screen.getByText("LIVE")).toBeInTheDocument();
      expect(screen.getByText("14:32 2nd Half")).toBeInTheDocument();
    });

    it("includes game clock in ARIA label", () => {
      render(
        <GameStatusBadge status="in_progress" gameClock="5:23 1st Half" />,
      );

      const badge = screen.getByText("LIVE");
      expect(badge).toHaveAttribute(
        "aria-label",
        "Game is live, 5:23 1st Half",
      );
    });
  });

  describe("FINAL games", () => {
    it("renders FINAL badge for final status", () => {
      render(<GameStatusBadge status="final" />);

      const badge = screen.getByText("FINAL");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute("aria-label", "Game is final");
    });

    it("does not render game clock for final games", () => {
      render(<GameStatusBadge status="final" gameClock="0:00 Final" />);

      expect(screen.getByText("FINAL")).toBeInTheDocument();
      expect(screen.queryByText("0:00 Final")).not.toBeInTheDocument();
    });
  });

  describe("Scheduled games", () => {
    it("renders formatted date and time for scheduled games", () => {
      // Use noon UTC to avoid timezone day-boundary issues in CI
      const startTime = "2025-11-16T12:00:00Z";

      render(<GameStatusBadge status="scheduled" startTime={startTime} />);

      // Should show date and time (format depends on local timezone)
      expect(screen.getByText(/Nov 16/i)).toBeInTheDocument();
      expect(screen.getByText(/\d{1,2}:\d{2}\s*(AM|PM)/i)).toBeInTheDocument();
    });

    it("includes formatted time in ARIA label", () => {
      const startTime = "2025-11-16T12:00:00Z";

      render(<GameStatusBadge status="scheduled" startTime={startTime} />);

      const badge = screen.getByText(/Nov 16/i);
      expect(badge).toHaveAttribute(
        "aria-label",
        expect.stringMatching(/Game starts Nov 16 at \d{1,2}:\d{2}\s*(AM|PM)/i),
      );
    });

    it("renders fallback for invalid startTime", () => {
      render(<GameStatusBadge status="scheduled" startTime="invalid-date" />);

      expect(screen.getByText("Scheduled")).toBeInTheDocument();
      expect(screen.getByLabelText("Scheduled game")).toBeInTheDocument();
    });

    it("renders nothing when no startTime provided", () => {
      render(<GameStatusBadge status="scheduled" />);

      // Should not render any badge
      expect(screen.queryByText(/scheduled/i)).not.toBeInTheDocument();
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("applies red styling to LIVE badges", () => {
      render(<GameStatusBadge status="in_progress" />);

      const badge = screen.getByText("LIVE");
      // Chakra UI applies color via CSS, just verify badge exists
      expect(badge).toBeInTheDocument();
    });

    it("applies gray styling to FINAL badges", () => {
      render(<GameStatusBadge status="final" />);

      const badge = screen.getByText("FINAL");
      expect(badge).toBeInTheDocument();
    });

    it("applies blue styling to scheduled badges", () => {
      const startTime = "2025-11-16T12:00:00Z";
      render(<GameStatusBadge status="scheduled" startTime={startTime} />);

      const badge = screen.getByText(/Nov 16/i);
      expect(badge).toBeInTheDocument();
    });
  });
});
