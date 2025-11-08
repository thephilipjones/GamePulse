# Story 3.3: Initialize React Dashboard with Chakra UI

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to set up the basic React dashboard structure with Chakra UI dark theme,
So that I have a foundation for displaying game data.

---

## Acceptance Criteria

**Given** the FastAPI template includes a React frontend with Chakra UI
**When** I configure the dashboard application structure
**Then** the application:
- Uses Chakra UI dark mode by default
- Has a main Dashboard page component
- Includes a header with "GamePulse" title
- Has responsive layout container (max-width for desktop, full-width for mobile)
- Removes authentication-related pages and routes

**And** I configure Chakra UI theme:
- Default to dark color mode
- Team color utilities for accent colors

**And** I set up React Query for API data fetching:
- QueryClient configured with 15-minute stale time
- QueryClientProvider wraps the app

**And** the dashboard loads at `http://localhost:5173` with empty state (no games yet)

**And** the page is mobile-responsive (tested in Chrome DevTools device mode)

---

## Prerequisites

- Story 1.6 (auth removed)
- Story 3.1 (API endpoint exists to fetch from)

---

## Technical Notes

**Create File:** `frontend/src/pages/Dashboard.tsx`
```typescript
import { Container, Heading, Box } from '@chakra-ui/react';

export function Dashboard() {
  return (
    <Container maxW="container.xl" py={8}>
      <Heading as="h1" size="2xl" textAlign="center" mb={8}>
        GamePulse
      </Heading>
      <Box>
        {/* Game list will go here */}
        <p>No games yet...</p>
      </Box>
    </Container>
  );
}
```

**Update src/App.tsx:**
```typescript
import { Dashboard } from './pages/Dashboard';

function App() {
  return <Dashboard />;
}

export default App;
```

**Configure Chakra UI Theme:** `frontend/src/theme.ts`
```typescript
import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    // Team colors can be added here later
  },
});

export default theme;
```

**Set Up React Query:** `frontend/src/main.tsx`
```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider } from '@chakra-ui/react';
import theme from './theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15 * 60 * 1000, // 15 minutes
      refetchInterval: 15 * 60 * 1000, // Auto-refresh every 15 min
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ChakraProvider>
  </React.StrictMode>
);
```

**Verify Dependency:** `@tanstack/react-query = "^5.90.7"` in package.json (already in template)

**Remove Authentication Files:**
- `src/pages/Login.tsx`
- `src/contexts/AuthContext.tsx`
- Any other auth-related components

**Responsive Breakpoints:**
- Chakra UI provides: `sm`, `md`, `lg`, `xl`, `2xl`
- Container maxW="container.xl" handles desktop width
- Mobile: Full width by default

---

## Definition of Done

- [ ] Dashboard.tsx page created
- [ ] App.tsx updated to render Dashboard
- [ ] Chakra UI theme configured with dark mode
- [ ] React Query QueryClient set up
- [ ] QueryClientProvider wraps app
- [ ] Authentication files removed
- [ ] Header with "GamePulse" title displayed
- [ ] Dashboard loads at http://localhost:5173
- [ ] Dark mode enabled by default
- [ ] Layout responsive on mobile (tested in DevTools)
- [ ] Empty state shown (no games yet message)
- [ ] Code follows TypeScript best practices
- [ ] Changes committed to git
