import { ChakraProvider } from "@chakra-ui/react";
import "@testing-library/jest-dom";
import { type RenderOptions, render } from "@testing-library/react";
import type React from "react";
import type { ReactElement } from "react";
import { ColorModeProvider } from "./components/ui/color-mode";
import { system } from "./theme";

// Mock window.matchMedia for tests (required for Chakra UI dark mode)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  }),
});

/**
 * Custom render function that wraps components with Chakra providers
 * for testing. This ensures all Chakra UI components work correctly in tests.
 */
function AllTheProviders({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider value={system}>
      <ColorModeProvider defaultTheme="light">{children}</ColorModeProvider>
    </ChakraProvider>
  );
}

/**
 * Custom render function for testing React components with Chakra UI.
 * Use this instead of @testing-library/react's render function.
 *
 * @example
 * ```tsx
 * import { renderWithProviders } from "./test-utils";
 *
 * it("renders component", () => {
 *   const { getByText } = renderWithProviders(<MyComponent />);
 *   expect(getByText("Hello")).toBeInTheDocument();
 * });
 * ```
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, { wrapper: AllTheProviders, ...options });
}

// Re-export everything from @testing-library/react
export * from "@testing-library/react";

// Override render with our custom version
export { renderWithProviders as render };
