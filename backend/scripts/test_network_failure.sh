#!/bin/bash
# Manual test script for Story 2-5: Network Failure Retry Validation
#
# Tests:
# - AC6: Network failure scenario (Docker network disconnect)
# - AC8: Dagster UI retry timeline verification
#
# Prerequisites:
# - Docker Compose running (docker compose up -d)
# - Dagster UI accessible at http://localhost:3000
# - NCAA API endpoint reachable
#
# Usage:
#   bash backend/scripts/test_network_failure.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Story 2-5: Network Failure Retry Test${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Step 1: Verify Prerequisites
echo -e "${YELLOW}Step 1: Verifying prerequisites...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running. Please start Docker.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check if docker compose services are up
if ! docker compose ps | grep -q "dagster-daemon"; then
    echo -e "${RED}✗ Dagster services not running. Please run: docker compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dagster services are running${NC}"

# Check if Dagster UI is accessible
if ! curl -s http://localhost:3000 > /dev/null; then
    echo -e "${RED}✗ Dagster UI not accessible at http://localhost:3000${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dagster UI is accessible${NC}\n"

# Step 2: Get baseline state
echo -e "${YELLOW}Step 2: Recording baseline state...${NC}"
CONTAINER_NAME="gamepulse-dagster-daemon-1"
NETWORK_NAME=$(docker inspect "$CONTAINER_NAME" --format='{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}' | head -1)

echo -e "Dagster container: ${BLUE}$CONTAINER_NAME${NC}"
echo -e "Docker network: ${BLUE}$NETWORK_NAME${NC}\n"

# Step 3: Trigger manual materialization
echo -e "${YELLOW}Step 3: Triggering manual asset materialization...${NC}"
echo -e "${BLUE}Please perform the following in Dagster UI:${NC}"
echo -e "1. Open http://localhost:3000 in your browser"
echo -e "2. Navigate to Assets → ncaa_games"
echo -e "3. Click 'Materialize' button"
echo -e "4. Wait for successful completion (should take ~5 seconds)\n"

read -p "Press Enter when baseline materialization is complete..."
echo ""

# Step 4: Simulate network failure (disconnect)
echo -e "${YELLOW}Step 4: Simulating network failure...${NC}"
echo -e "${RED}Disconnecting Dagster container from network${NC}"

docker network disconnect "$NETWORK_NAME" "$CONTAINER_NAME"
echo -e "${GREEN}✓ Network disconnected${NC}\n"

# Step 5: Verify daemon stays running
echo -e "${YELLOW}Step 5: Verifying daemon resilience...${NC}"
sleep 3  # Give daemon time to detect network failure

if docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}✓ Dagster daemon is still running (AC6: no crash)${NC}"
else
    echo -e "${RED}✗ Dagster daemon crashed! This is a test failure.${NC}"
    # Reconnect network before exiting
    docker network connect "$NETWORK_NAME" "$CONTAINER_NAME"
    exit 1
fi
echo ""

# Step 6: Trigger materialization during network outage
echo -e "${YELLOW}Step 6: Triggering materialization during network outage...${NC}"
echo -e "${BLUE}Please perform the following in Dagster UI:${NC}"
echo -e "1. Navigate to Assets → ncaa_games"
echo -e "2. Click 'Materialize' button"
echo -e "3. Observe retry behavior in Runs tab\n"

echo -e "${BLUE}Expected behavior:${NC}"
echo -e "- Asset should attempt materialization"
echo -e "- HTTP request will fail (network disconnected)"
echo -e "- Retry policy should trigger 3 attempts"
echo -e "- Each retry should have exponential backoff (2s, 4s, 8s)"
echo -e "- After ~30s total (3 retries × ~10s each), run should fail"
echo -e "- Dagster daemon should remain running (no crash)\n"

read -p "Press Enter when you see the failed run in Dagster UI..."
echo ""

# Step 7: Verify retry timeline in Dagster UI
echo -e "${YELLOW}Step 7: Verifying retry timeline (AC8)...${NC}"
echo -e "${BLUE}Please perform the following in Dagster UI:${NC}"
echo -e "1. Navigate to Runs tab"
echo -e "2. Click on the most recent failed run"
echo -e "3. Expand the 'ncaa_games' asset execution timeline\n"

echo -e "${BLUE}Verify the following in the timeline:${NC}"
echo -e "- [ ] Run shows 'Failed' status (red)"
echo -e "- [ ] Timeline shows 3 retry attempts"
echo -e "- [ ] Each retry has exponential delay:"
echo -e "      - Retry 1 → ~2s delay"
echo -e "      - Retry 2 → ~4s delay"
echo -e "      - Retry 3 → ~8s delay"
echo -e "- [ ] Total duration is ~30 seconds"
echo -e "- [ ] Error logs show 'Connection error' or similar network failure\n"

read -p "Press Enter after verifying retry timeline..."
echo ""

# Step 8: Restore network connection
echo -e "${YELLOW}Step 8: Restoring network connection...${NC}"
echo -e "${GREEN}Reconnecting Dagster container to network${NC}"

docker network connect "$NETWORK_NAME" "$CONTAINER_NAME"
echo -e "${GREEN}✓ Network reconnected${NC}\n"

# Step 9: Verify automatic recovery
echo -e "${YELLOW}Step 9: Verifying automatic recovery...${NC}"
echo -e "${BLUE}Please wait 60 seconds for the next scheduled run (15-minute interval)${NC}"
echo -e "Or manually trigger another materialization:\n"

echo -e "${BLUE}Expected behavior:${NC}"
echo -e "- Next scheduled run (or manual trigger) should succeed"
echo -e "- Asset should fetch today's games successfully"
echo -e "- No retries needed (network is restored)"
echo -e "- Cached data from before failure should be preserved\n"

read -p "Press Enter to trigger recovery test materialization..."

echo -e "\n${BLUE}Please perform the following in Dagster UI:${NC}"
echo -e "1. Navigate to Assets → ncaa_games"
echo -e "2. Click 'Materialize' button"
echo -e "3. Verify successful completion (green status)\n"

read -p "Press Enter when recovery materialization succeeds..."
echo ""

# Step 10: Validate cached data retention (AC9)
echo -e "${YELLOW}Step 10: Validating cached data retention (AC9)...${NC}"

echo -e "${BLUE}Querying database for games count...${NC}"
GAMES_COUNT=$(docker compose exec -T db psql -U postgres -d app -c "SELECT COUNT(*) FROM fact_game;" | sed -n '3p' | tr -d ' ')

if [ -z "$GAMES_COUNT" ]; then
    echo -e "${YELLOW}⚠ Could not query database. Please manually verify:${NC}"
    echo -e "  docker compose exec db psql -U postgres -d app -c 'SELECT COUNT(*) FROM fact_game;'\n"
else
    echo -e "${GREEN}✓ fact_game table contains $GAMES_COUNT games${NC}"
    echo -e "${BLUE}Verify this matches the count before network failure${NC}\n"
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}✓ AC6: Daemon resilience verified${NC}"
echo -e "  - Dagster daemon stayed running during network failure"
echo -e "  - No process crashes or restarts\n"

echo -e "${YELLOW}Manual verification required:${NC}"
echo -e "  - [ ] AC8: Dagster UI retry timeline shows exponential backoff"
echo -e "  - [ ] AC8: Timeline displays 3 retry attempts"
echo -e "  - [ ] AC8: Total retry duration is ~30 seconds"
echo -e "  - [ ] AC9: Cached data retained after API failure"
echo -e "  - [ ] Automatic recovery after network restore\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Document findings in Story 2-5 (docs/stories/2-5-add-retry-logic.md)"
echo -e "2. Take screenshots of Dagster UI retry timeline (optional)"
echo -e "3. Mark AC6 and AC8 as verified in story file\n"

echo -e "${GREEN}Test complete!${NC}"
