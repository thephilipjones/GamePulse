import { ChakraProvider } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@testing-library/jest-dom";
import { type RenderOptions, render } from "@testing-library/react";
import type React from "react";
import type { ReactElement } from "react";
import { ColorModeProvider } from "./components/ui/color-mode";
import { system } from "./theme";

// Create a fresh QueryClient for each test
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

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
 * Custom render function that wraps components with all necessary providers
 * for testing. This ensures all Chakra UI and TanStack Query components work correctly in tests.
 */
function AllTheProviders({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={system}>
        <ColorModeProvider defaultTheme="light">{children}</ColorModeProvider>
      </ChakraProvider>
    </QueryClientProvider>
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
