import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "../test-utils";
import { DateNavigator } from "./DateNavigator";

/**
 * DateNavigator Component Tests
 *
 * Satisfies AC-4.11.7: Component Tests
 * - Test: Prev button decrements date by 1 day
 * - Test: Next button increments date by 1 day
 * - Test: Date formatted correctly (long format)
 * - Test: onDateChange callback called with correct date string
 * - Test: Aria-labels present on navigation buttons
 */
describe("DateNavigator", () => {
  it("should call onDateChange with previous day when prev button clicked", () => {
    const mockOnChange = vi.fn();
    render(
      <DateNavigator currentDate="2025-11-20" onDateChange={mockOnChange} />
    );

    const prevButton = screen.getByLabelText("Previous day");
    fireEvent.click(prevButton);

    expect(mockOnChange).toHaveBeenCalledWith("2025-11-19");
  });

  it("should call onDateChange with next day when next button clicked", () => {
    const mockOnChange = vi.fn();
    render(
      <DateNavigator currentDate="2025-11-20" onDateChange={mockOnChange} />
    );

    const nextButton = screen.getByLabelText("Next day");
    fireEvent.click(nextButton);

    expect(mockOnChange).toHaveBeenCalledWith("2025-11-21");
  });

  it("should format date as 'Thursday, November 20, 2025'", () => {
    render(
      <DateNavigator currentDate="2025-11-20" onDateChange={vi.fn()} />
    );

    // Check for formatted date string (Nov 20, 2025 is a Thursday)
    expect(screen.getByText(/Thursday, November 20, 2025/i)).toBeInTheDocument();
  });

  it("should have accessible aria-labels on navigation buttons", () => {
    render(
      <DateNavigator currentDate="2025-11-20" onDateChange={vi.fn()} />
    );

    // AC-4.11.7: Verify aria-labels for accessibility
    expect(screen.getByLabelText("Previous day")).toBeInTheDocument();
    expect(screen.getByLabelText("Next day")).toBeInTheDocument();
  });

  it("should handle month transitions correctly (prev day)", () => {
    const mockOnChange = vi.fn();
    render(
      <DateNavigator currentDate="2025-11-01" onDateChange={mockOnChange} />
    );

    fireEvent.click(screen.getByLabelText("Previous day"));

    // Should go back to previous month (Oct 31)
    expect(mockOnChange).toHaveBeenCalledWith("2025-10-31");
  });

  it("should handle month transitions correctly (next day)", () => {
    const mockOnChange = vi.fn();
    render(
      <DateNavigator currentDate="2025-10-31" onDateChange={mockOnChange} />
    );

    fireEvent.click(screen.getByLabelText("Next day"));

    // Should advance to next month (Nov 1)
    expect(mockOnChange).toHaveBeenCalledWith("2025-11-01");
  });

  it("should handle year transitions correctly", () => {
    const mockOnChange = vi.fn();
    render(
      <DateNavigator currentDate="2024-12-31" onDateChange={mockOnChange} />
    );

    fireEvent.click(screen.getByLabelText("Next day"));

    // Should advance to next year
    expect(mockOnChange).toHaveBeenCalledWith("2025-01-01");
  });

  it("should not call onDateChange if buttons are not clicked", () => {
    const mockOnChange = vi.fn();
    render(
      <DateNavigator currentDate="2025-11-20" onDateChange={mockOnChange} />
    );

    // Just rendering, no clicks
    expect(mockOnChange).not.toHaveBeenCalled();
  });
});
