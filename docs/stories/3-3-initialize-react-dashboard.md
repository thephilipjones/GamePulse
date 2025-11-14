# Story 3.3: Initialize React Dashboard with Chakra UI

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** ready-for-dev
**Assignee:** Claude Code (Dev Agent)
**Sprint:** Week 1
**Story Points:** 5
**Dependencies:** Story 1.2 (Remove Authentication), Story 3.1 (Games API Endpoint), Story 3.2 (Health Check Endpoint)

---

## User Story

**As a** frontend developer setting up the GamePulse dashboard
**I want** to initialize the React application structure with Chakra UI, React Query, and routing configuration
**So that** I have a functional foundation for displaying NCAA game data with proper state management and responsive layout

---

## Business Context

Story 3.3 establishes the frontend application foundation required for the "Working Demo" milestone (Epic 3 goal: shareable live URL by end of Week 1). This story transforms the FastAPI full-stack template's React frontend from an authentication-focused application into a sports dashboard optimized for displaying time-series game data with automatic polling refresh.

**Why This Story Matters:**

- Provides the architectural foundation for all frontend work in Epic 3 (Stories 3.4, 3.5) and Epic 8 enhancements
- Configures TanStack Query (React Query) for efficient API data caching matching the 15-minute Dagster ingestion cadence
- Sets up Chakra UI component library for rapid UI development without custom CSS (saves 2-3 days vs building components from scratch)
- Removes authentication complexity from template (per Epic 1 Story 1.2 backend work), simplifying to read-only public dashboard

**Impact of Delays:**

- Blocks Story 3.4 (GameList component) and Story 3.5 (Auto-refresh polling) - entire Epic 3 frontend track stops
- Delays Week 1 working demo milestone - Philip actively interviewing, needs shareable URL ASAP
- Frontend-backend integration testing delayed - can't validate CORS configuration from Story 3.1 without frontend making requests

---

## Acceptance Criteria

### AC-3.11: React Application Structure

**Given** the FastAPI full-stack template provides a React 18 + TypeScript + Vite frontend
**When** I initialize the dashboard application structure
**Then** the application:
- Renders without errors at `http://localhost:5173` in development mode
- Has a main Dashboard page component at `frontend/src/pages/Dashboard.tsx`
- Includes a header with "GamePulse" title (centered, large heading)
- Uses Chakra UI Container with responsive max-width (container.xl breakpoint)
- Removes all authentication-related pages, routes, and contexts from template

**Validation:**

```bash
# Start frontend dev server
cd frontend
npm run dev

# Open browser to http://localhost:5173
# Expected: Dashboard page loads, "GamePulse" header visible, no auth UI
```

---

### AC-3.12: Chakra UI Theme Configuration

**Given** Chakra UI is included in the FastAPI template
**When** I configure the theme system
**Then** the application:
- Uses Chakra UI default light theme (dark mode deferred to Epic 8 per tech spec)
- Has a ChakraProvider wrapping the entire app in `main.tsx`
- Includes responsive breakpoint support (sm, md, lg, xl, 2xl)
- Works correctly on mobile viewports (tested in Chrome DevTools device mode)

**Validation:**

```typescript
// frontend/src/main.tsx should include:
<ChakraProvider>
  <App />
</ChakraProvider>

// Dashboard.tsx should use responsive Container:
<Container maxW="container.xl" py={8}>
```

---

### AC-3.13: React Query (TanStack Query) Configuration

**Given** frontend needs to fetch data from backend API with automatic caching and refresh
**When** I configure React Query (TanStack Query)
**Then** the application:
- Has a QueryClient configured with 15-minute staleTime (900000ms)
- Has a QueryClientProvider wrapping the app
- Enables React Query DevTools in development mode only
- Matches backend Dagster ingestion cadence (15-minute data freshness acceptable per NFR-1.4)

**Validation:**

```typescript
// frontend/src/main.tsx should configure:
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 900000,  // 15 minutes
      retry: 3,           // Automatic retry on API failures
    },
  },
});

<QueryClientProvider client={queryClient}>
  <ReactQueryDevtools initialIsOpen={false} />
  <ChakraProvider>
    <App />
  </ChakraProvider>
</QueryClientProvider>
```

---

### AC-3.14: Environment-Based API Configuration

**Given** frontend needs to call backend API at different URLs in development vs production
**When** I configure API endpoint URLs
**Then** the application:
- Reads API base URL from `VITE_API_URL` environment variable
- Defaults to `http://localhost:8000` for local development
- Uses `https://api.gamepulse.top` in production (set via .env file)
- Validates environment variable is set before making requests

**Validation:**

```bash
# Development (.env.development)
VITE_API_URL=http://localhost:8000

# Production (.env.production)
VITE_API_URL=https://api.gamepulse.top

# frontend/src/config.ts exports API_BASE_URL constant
```

---

### AC-3.15: Routing Configuration

**Given** the dashboard is a single-page application with minimal routing
**When** I configure TanStack Router
**Then** the application:
- Has a root route rendering Dashboard component
- Removes authentication-protected routes from template
- Maintains clean URL structure: `/` → Dashboard
- Prepares for future routes: `/game/:id` (deferred to Epic 8)

**Validation:**

```typescript
// frontend/src/routes.tsx defines single route:
const routes = [
  { path: '/', component: Dashboard },
];
```

---

### AC-3.16: TypeScript Type Safety

**Given** frontend uses TypeScript for compile-time type checking
**When** I implement the dashboard structure
**Then** the code:
- Passes TypeScript compilation with zero errors (`tsc --noEmit`)
- Uses proper type annotations for all component props
- Imports types correctly from dependencies
- Follows Chakra UI and React Query type patterns

**Validation:**

```bash
cd frontend
npm run build  # Should complete without TypeScript errors
```

---

### AC-3.17: Empty State Display

**Given** no API integration exists yet (deferred to Story 3.4)
**When** I load the dashboard
**Then** the application:
- Displays "GamePulse" header
- Shows placeholder text: "Loading games..." or "No games available"
- Has proper spacing and layout (not broken/unstyled)
- Provides visual confirmation dashboard structure works

**Validation:**

Manual browser check: Dashboard renders with header and placeholder content, no console errors

---

## Tasks / Subtasks

- [ ] **Task 1: Clean Up Authentication Boilerplate** (AC: 3.11, 3.15)

  - [ ] Remove `frontend/src/pages/Login.tsx` (auth page not needed)
  - [ ] Remove `frontend/src/contexts/AuthContext.tsx` (no user sessions)
  - [ ] Remove authentication-protected route wrappers
  - [ ] Delete unused auth-related components (ProtectedRoute, etc.)
  - [ ] Update `App.tsx` to remove auth context providers

- [ ] **Task 2: Configure React Query (TanStack Query)** (AC: 3.13)

  - [ ] Install `@tanstack/react-query` if not in template (check package.json)
  - [ ] Install `@tanstack/react-query-devtools` as dev dependency
  - [ ] Create QueryClient with 15-minute staleTime in `main.tsx`
  - [ ] Wrap app with QueryClientProvider
  - [ ] Add ReactQueryDevTools for development debugging (conditionally enabled)
  - [ ] Test QueryClient configuration by checking DevTools in browser

- [ ] **Task 3: Configure Chakra UI Theme** (AC: 3.12)

  - [ ] Verify Chakra UI installed in package.json (template includes v3.8+)
  - [ ] Add ChakraProvider to `main.tsx` wrapping App component
  - [ ] Use default light theme (no custom theme file needed for MVP)
  - [ ] Test responsive breakpoints in Chrome DevTools device mode (mobile, tablet, desktop)

- [ ] **Task 4: Create Dashboard Page Component** (AC: 3.11, 3.17)

  - [ ] Create `frontend/src/pages/Dashboard.tsx` file
  - [ ] Import Chakra UI components: Container, Heading, Box
  - [ ] Implement responsive Container with maxW="container.xl"
  - [ ] Add centered "GamePulse" heading (size="2xl", mb={8} for spacing)
  - [ ] Add placeholder Box with "Loading games..." text
  - [ ] Export Dashboard component as default

- [ ] **Task 5: Configure Routing** (AC: 3.15)

  - [ ] Update `frontend/src/App.tsx` to render Dashboard directly (minimal routing for MVP)
  - [ ] Remove authentication-protected route logic
  - [ ] Simplify to single route: `/` → Dashboard
  - [ ] Prepare for future expansion: comment structure for `/game/:id` route (Epic 8)

- [ ] **Task 6: Environment Configuration** (AC: 3.14)

  - [ ] Create `frontend/.env.development` with `VITE_API_URL=http://localhost:8000`
  - [ ] Create `frontend/.env.production` with `VITE_API_URL=https://api.gamepulse.top`
  - [ ] Create `frontend/src/config.ts` exporting API_BASE_URL constant from import.meta.env
  - [ ] Add type declaration for VITE_API_URL in `vite-env.d.ts` (TypeScript support)

- [ ] **Task 7: Testing and Validation** (AC: All)

  - [ ] Start frontend dev server: `npm run dev`
  - [ ] Verify dashboard loads at http://localhost:5173 without errors
  - [ ] Check browser console for warnings (React Query, Chakra UI)
  - [ ] Test responsive layout in Chrome DevTools (mobile, tablet, desktop views)
  - [ ] Run TypeScript type check: `tsc --noEmit` (should pass with 0 errors)
  - [ ] Run linter: `npm run lint` (should pass)
  - [ ] Verify React Query DevTools visible in development (bottom-left icon)

- [ ] **Task 8: Documentation and Cleanup** (AC: All)

  - [ ] Add JSDoc comments to Dashboard component
  - [ ] Document environment variables in frontend/README.md
  - [ ] Update package.json scripts if needed (ensure dev/build work)
  - [ ] Commit changes with descriptive message
  - [ ] Update sprint-status.yaml: 3-3-initialize-react-dashboard = "in-progress"

---

## Dev Notes

### Architecture Patterns from Epic 3 Tech Spec

**Frontend Stack** (from Tech Spec [System Architecture Alignment](../tech-spec-epic-3.md#system-architecture-alignment)):

- **React 18.2+**: Modern React with hooks, concurrent features
- **TypeScript**: Compile-time type safety, auto-generated API client types
- **Vite 5.4+**: Fast HMR (Hot Module Replacement), optimized production builds
- **Chakra UI 3.8+**: Pre-built responsive components, saves 2-3 days vs custom CSS
- **TanStack Query 5.90.7**: Server state management, automatic caching, polling refresh

**State Management Strategy** (from Tech Spec [Dependencies](../tech-spec-epic-3.md#dependencies-and-integrations)):

- **TanStack Query (React Query)**: Manages all server state (API data)
  - Automatic background refetch every 15 minutes (matches Dagster cadence)
  - Stale-while-revalidate pattern (show cached data during refetch)
  - Automatic retry with exponential backoff (3 attempts: 1s, 2s, 4s)
  - DevTools for debugging cache state
- **React useState**: Local UI state only (modal open/close, form inputs)
- **No global state library needed**: Single dashboard page, minimal UI state

**CORS Integration** (from Tech Spec [Security](../tech-spec-epic-3.md#security)):

- Backend configured in Story 3.1 with allowed origins:
  - Development: `http://localhost:5173` (Vite dev server)
  - Production: `https://gamepulse.top`
- Frontend must use correct API_BASE_URL from environment variables
- Preflight OPTIONS requests handled automatically by browser + FastAPI middleware

**Performance Targets** (from Tech Spec [Performance](../tech-spec-epic-3.md#performance)):

- **Frontend Initial Load**: <2 seconds (P95)
  - React bundle size: <500KB gzipped (Vite tree-shaking)
  - Chakra UI lazy-loaded components
- **Polling Overhead**: Negligible (background fetch, no UI blocking)
  - TanStack Query uses stale-while-revalidate (displays cached data during refetch)

### Project Structure Alignment

**FastAPI Full-Stack Template Structure** (from Epic 1):

```
frontend/
├── src/
│   ├── components/      # Reusable UI components (Epic 3.4: GameList)
│   ├── pages/           # Route-level components (Dashboard)
│   │   └── Dashboard.tsx  # NEW - This story creates this file
│   ├── hooks/           # Custom React hooks (Epic 3.5: useGamesQuery)
│   ├── routes.tsx       # TanStack Router configuration - SIMPLIFY
│   ├── config.ts        # NEW - Environment-based API URL config
│   ├── App.tsx          # MODIFY - Remove auth, render Dashboard
│   └── main.tsx         # MODIFY - Add QueryClientProvider, ChakraProvider
├── .env.development     # NEW - VITE_API_URL=http://localhost:8000
├── .env.production      # NEW - VITE_API_URL=https://api.gamepulse.top
├── package.json
├── vite.config.ts
└── tsconfig.json
```

**Story 3.3 File Changes:**

- **NEW FILES**:
  - `frontend/src/pages/Dashboard.tsx` - Main dashboard page component
  - `frontend/src/config.ts` - API base URL configuration
  - `frontend/.env.development` - Development environment variables
  - `frontend/.env.production` - Production environment variables

- **MODIFIED FILES**:
  - `frontend/src/main.tsx` - Add QueryClientProvider, ChakraProvider wrappers
  - `frontend/src/App.tsx` - Remove auth context, simplify to render Dashboard

- **DELETED FILES**:
  - `frontend/src/pages/Login.tsx` - Authentication page (not needed)
  - `frontend/src/contexts/AuthContext.tsx` - Auth context (per Epic 1 Story 1.2)
  - Any other auth-related components from template

### Learnings from Previous Story (3-2-add-health-endpoint)

**From Story 3-2 Completion Notes:**

- ✅ **Docker rebuild required for new files** - Volume mounts only sync existing files
  - **Action for this story**: After creating new frontend files, rebuild frontend container
  - Command: `docker compose build frontend && docker compose up -d frontend`

- ✅ **Integration testing patterns** - Use FastAPI TestClient for backend, React Testing Library for frontend
  - **Action for this story**: Manual testing sufficient for MVP (automated tests in Epic 9)
  - Verify: Dashboard loads, React Query DevTools visible, no console errors

- ✅ **Structured logging with context fields** - Backend uses structured logging (endpoint, status, response_time_ms)
  - **Action for this story**: Frontend logging via browser console in development
  - Production: Future Epic 9 work (Sentry integration for error tracking)

- ✅ **Code quality standards** - All code passed ruff (backend) and biome (frontend) linting
  - **Action for this story**: Run `npm run lint` before committing
  - Ensure TypeScript compilation passes: `tsc --noEmit`

**Frontend-Specific Patterns from Template:**

- **Vite HMR**: Changes to `.tsx` files trigger instant browser refresh (no manual reload needed)
- **TypeScript strict mode**: Enabled in `tsconfig.json`, ensures type safety
- **Biome linter**: Frontend linting/formatting (configured in `biome.json`)
- **npm scripts**: `npm run dev` (dev server), `npm run build` (production build), `npm run lint` (linting)

**Integration with Story 3.1 (Games API Endpoint):**

- Backend CORS configured to allow `http://localhost:5173` origin
- Frontend will call `GET /api/games/today` in Story 3.4 (next story)
- This story prepares infrastructure: React Query client, API URL configuration
- Testing in this story: Verify dashboard loads, but no API calls yet (placeholder content)

### Code Examples from Tech Spec

**React Query Configuration** (from Tech Spec [APIs and Interfaces](../tech-spec-epic-3.md#apis-and-interfaces)):

```typescript
// frontend/src/main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ChakraProvider } from '@chakra-ui/react';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 900000,  // 15 minutes = 900000ms
      retry: 3,           // Retry failed requests 3 times
      refetchOnWindowFocus: false,  // Don't refetch when window regains focus
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ReactQueryDevtools initialIsOpen={false} />
      <ChakraProvider>
        <App />
      </ChakraProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
```

**Dashboard Component** (from Tech Spec [Services and Modules](../tech-spec-epic-3.md#services-and-modules)):

```typescript
// frontend/src/pages/Dashboard.tsx
import { Container, Heading, Box, Text } from '@chakra-ui/react';

/**
 * Main dashboard page for GamePulse.
 * Displays NCAA Men's Basketball games with excitement scores.
 */
export default function Dashboard() {
  return (
    <Container maxW="container.xl" py={8}>
      <Heading as="h1" size="2xl" textAlign="center" mb={8}>
        GamePulse
      </Heading>
      <Box>
        <Text fontSize="lg" color="gray.500" textAlign="center">
          Loading games...
        </Text>
        {/* GameList component will be added in Story 3.4 */}
      </Box>
    </Container>
  );
}
```

**Environment Configuration** (from Tech Spec [Detailed Design](../tech-spec-epic-3.md#detailed-design)):

```typescript
// frontend/src/config.ts
/**
 * Environment-based configuration.
 * Reads API base URL from Vite environment variables.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Type-safe access to environment variables
declare global {
  interface ImportMetaEnv {
    readonly VITE_API_URL: string;
  }
}
```

```bash
# frontend/.env.development
VITE_API_URL=http://localhost:8000

# frontend/.env.production
VITE_API_URL=https://api.gamepulse.top
```

**Simplified App.tsx** (removing auth from template):

```typescript
// frontend/src/App.tsx
import Dashboard from './pages/Dashboard';

function App() {
  return <Dashboard />;
}

export default App;
```

### References

**Tech Spec Sections:**

- [Services and Modules](../tech-spec-epic-3.md#services-and-modules) - Frontend module structure, Dashboard component spec
- [Dependencies and Integrations](../tech-spec-epic-3.md#dependencies-and-integrations) - React Query, Chakra UI versions
- [System Architecture Alignment](../tech-spec-epic-3.md#system-architecture-alignment) - Frontend stack, design constraints
- [Security](../tech-spec-epic-3.md#security) - CORS configuration, environment variables
- [Performance](../tech-spec-epic-3.md#performance) - Bundle size targets, initial load time
- [Acceptance Criteria](../tech-spec-epic-3.md#acceptance-criteria-authoritative) - AC-3.5 (partial: dashboard structure), AC-3.9 (type safety)

**PRD Requirements:**

- [FR-7.1](../PRD.md#fr-7-frontend-dashboard) - Frontend display requirements
- [FR-7.2](../PRD.md#fr-7-frontend-dashboard) - Frontend-backend integration
- [NFR-1.2](../PRD.md#nfr-1-performance) - Frontend initial load <2 seconds
- [NFR-3.1](../PRD.md#nfr-3-security) - Public access (no authentication)

**Architecture Document:**

- [Project Structure](../architecture.md#project-structure) - Frontend folder organization
- [Frontend State](../architecture.md#decision-summary) - React Query for server state management
- [Technology Stack](../architecture.md#decision-summary) - React 18, Chakra UI, Vite versions

**Previous Story:**

- [Story 3.2](./3-2-add-health-endpoint.md#dev-agent-record) - Docker rebuild patterns, integration testing, code quality standards

**External Documentation:**

- [TanStack Query Docs](https://tanstack.com/query/latest/docs/framework/react/overview) - React Query configuration
- [Chakra UI Docs](https://www.chakra-ui.com/getting-started) - Component usage, responsive design
- [Vite Environment Variables](https://vite.dev/guide/env-and-mode.html) - VITE_* variable configuration

---

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-3-initialize-react-dashboard.context.xml) - Generated 2025-11-14

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Change Log

**2025-11-14:** Story 3.3 created (drafted status)
- Defined comprehensive acceptance criteria from Epic 3 Tech Spec
- Extracted requirements from PRD FR-7 and NFR-1.2
- Documented architecture patterns: React Query, Chakra UI, environment config
- Incorporated learnings from Story 3.2 (Docker rebuild, testing patterns)
- Ready for dev agent implementation
