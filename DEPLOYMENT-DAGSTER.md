# Dagster Deployment Guide - Story 2.4

## 🚨 **CRITICAL: Manual Steps Required Before/After CI/CD**

This document outlines all manual configuration needed to deploy Dagster orchestration to production.

---

## 📋 **Pre-Deployment Checklist (BEFORE pushing to main)**

### **Step 1: Update Production .env File**

**Action:** SSH to EC2 and add Dagster environment variables to `/opt/gamepulse/.env`

```bash
# SSH to production server
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<ELASTIC_IP>

# Edit production .env
cd /opt/gamepulse
nano .env
```

**Add the following variables:**

```bash
# ============================================
# DAGSTER ORCHESTRATION (NEW)
# ============================================

# Dagster metadata storage (PostgreSQL - separate database)
# IMPORTANT: Uses separate 'dagster' database to avoid conflicts with application data
DAGSTER_POSTGRES_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:${POSTGRES_PORT}/dagster
DAGSTER_POSTGRES_USER=postgres
DAGSTER_POSTGRES_PASSWORD=<same-as-POSTGRES_PASSWORD>
DAGSTER_POSTGRES_DB=dagster
DAGSTER_POSTGRES_HOSTNAME=db
DAGSTER_POSTGRES_PORT=5432

# Dagster runtime
DAGSTER_HOME=/tmp/dagster_home

# NOTE: The 'dagster' database and schema will be automatically created
# by the prestart.sh script on first deployment.
```

**Validation:**
```bash
# Verify all variables are set
grep "DAGSTER" .env
```

---

### **Step 2: Update Traefik Configuration (Dagster UI Subdomain)**

**Action:** Configure Traefik routing for `dagster.gamepulse.top`

**Option A: Via Docker Compose Labels (Recommended)**

Already configured in `docker-compose.yml` for dagster-webserver service:

```yaml
dagster-webserver:
  labels:
    - traefik.enable=true
    - traefik.http.routers.dagster-webserver.rule=Host(`dagster.${DOMAIN?Variable not set}`)
    - traefik.http.routers.dagster-webserver.entrypoints=websecure
    - traefik.http.routers.dagster-webserver.tls=true
    - traefik.http.routers.dagster-webserver.tls.certresolver=le
    - traefik.http.services.dagster-webserver.loadbalancer.server.port=3000
```

**Option B: Verify DNS (if using subdomain)**

```bash
# Ensure DNS A record points to Elastic IP
dig dagster.gamepulse.top

# Expected output:
# dagster.gamepulse.top. 300 IN A <ELASTIC_IP>
```

If DNS not configured:
1. Go to domain registrar (e.g., Namecheap, Route53)
2. Add A record: `dagster` → `<ELASTIC_IP>`
3. Wait 5-10 minutes for DNS propagation

---

### **Step 3: Update GitHub Secrets (Dagster Database Configuration)**

**Action:** Configure separate Dagster database in GitHub Secrets to avoid Alembic conflicts

1. Navigate to: `https://github.com/PhilipTrauner/gamepulse/settings/secrets/actions`
2. Add new secret:
   - Name: `DAGSTER_POSTGRES_DB`
   - Value: `dagster`

**Why Separate Database:**
- Prevents conflicts between Alembic migrations (application) and Dagster schema
- Isolates Dagster metadata from application data
- Allows independent backup/restore strategies

**Note:** The `dagster` database will be automatically created and initialized by `prestart.sh` on first deployment.

---

## 🚀 **Deployment Process**

### **Phase 1: Pre-Push (Local)**

✅ **Completed:**
- [x] Code committed to `main` branch
- [x] Pre-commit hooks passed (ruff, mypy)
- [x] Manual testing completed locally

**Next Action:**
```bash
git push origin main
```

---

### **Phase 2: CI/CD Pipeline (Automated)**

**GitHub Actions will automatically:**

1. **Lint & Type Check** (parallel)
   - Backend: `ruff check`, `ruff format`, `mypy`
   - Frontend: `biome`
   - ✅ Expected: PASS (already validated locally)

2. **Test** (parallel)
   - Backend: `pytest -v` with PostgreSQL service
   - Frontend: Skipped (no tests configured)
   - ✅ Expected: PASS (new code tested locally)

3. **Generate Client** (TypeScript from OpenAPI)
   - Auto-regenerates if schema changed
   - Auto-commits if changes detected
   - ⚠️ Expected: **NO CHANGES** (no API changes in this story)

4. **Build** (Docker images)
   - Builds backend image with Dagster dependencies
   - Pushes to ECR Public
   - ⚠️ Expected: **~3-5 minutes** (new dependencies: dagster, asyncpg)

5. **Deploy** (to EC2 via SSM)
   - Connects via AWS Systems Manager Session
   - Pulls latest code from GitHub
   - Pulls Docker images from ECR
   - Runs `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
   - ⚠️ Expected: **Dagster services will be created and started**

6. **Smoke Test**
   - Health check: `curl https://api.gamepulse.top/api/v1/utils/health-check/`
   - ✅ Expected: PASS (backend unchanged)

**Monitor Progress:**
```bash
# Watch GitHub Actions workflow
open https://github.com/PhilipTrauner/gamepulse/actions
```

---

### **Phase 3: Post-Deployment Verification (MANUAL)**

**⏰ Wait for CI/CD to complete (~8-12 minutes)**

Once workflow shows ✅ **SUCCESS**, perform these validation steps:

#### **Step 1: Verify Dagster Services Running**

```bash
# SSH to production
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<ELASTIC_IP>

# Check Docker containers
cd /opt/gamepulse
docker compose ps | grep dagster

# Expected output:
# gamepulse-dagster-webserver-1   running   0.0.0.0:3000->3000/tcp
# gamepulse-dagster-daemon-1      running
```

#### **Step 2: Verify Dagster UI Accessible**

```bash
# Option 1: Via production domain (if DNS configured)
curl -I https://dagster.gamepulse.top

# Expected: HTTP/2 200
# Expected: Location header with Dagster UI

# Option 2: Via localhost (from EC2)
curl -I http://localhost:3000

# Expected: HTTP/1.1 200
# Expected: Content-Type: text/html
```

**Browser Test:**
1. Open: `https://dagster.gamepulse.top` (or `http://<ELASTIC_IP>:3000`)
2. ✅ Dagster UI loads
3. ✅ Navigate to **Assets** tab → See `ncaa_games` asset
4. ✅ Navigate to **Schedules** tab → See `ncaa_games_schedule` (Running)

#### **Step 3: Verify Schedule Active**

```bash
# Check Dagster daemon logs
docker compose logs dagster-daemon --tail 50 | grep -E "schedule|SchedulerDaemon"

# Expected logs (within 2-3 minutes):
# dagster.daemon - INFO - Instance is configured with [...'SchedulerDaemon'...]
# dagster.daemon.SchedulerDaemon - INFO - Checking for new runs for schedule: ncaa_games_schedule
```

#### **Step 4: Trigger Manual Materialization (Critical Test)**

**Via Dagster UI:**
1. Navigate to **Assets** → `ncaa_games`
2. Click **"Materialize"** button
3. Watch run progress in real-time
4. ✅ Expected: Run completes with status **SUCCESS**
5. ✅ Expected: Metadata shows `games_processed: <number>`

**Via CLI (alternative):**
```bash
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions ncaa_games

# Watch logs
docker compose logs -f dagster-daemon | grep ncaa_games
```

**Expected Log Events:**
```
ncaa_games_asset_started
ncaa_api_fetch_started
ncaa_api_fetch_completed: games_count=<number>
teams_synced: {'teams_discovered': X, 'teams_updated': Y, 'teams_unchanged': Z}
game_transformed: game_id=ncaam_...
ncaa_games_asset_completed: games_processed=<number>, games_inserted=<number>, games_updated=<number>
```

#### **Step 5: Verify Database Ingestion**

```bash
# Check fact_game table
docker compose exec db psql -U postgres -d app -c "SELECT COUNT(*) as total_games FROM fact_game;"

# Expected: total_games > 0 (number depends on today's NCAA schedule)

# Sample games
docker compose exec db psql -U postgres -d app -c "
SELECT g.game_id, ht.team_name as home, at.team_name as away,
       g.home_score, g.away_score, g.rivalry_factor, g.game_status
FROM fact_game g
JOIN dim_team ht ON g.home_team_key = ht.team_key
JOIN dim_team at ON g.away_team_key = at.team_key
LIMIT 5;
"

# Expected: Real game data with team names, scores, rivalry factors
```

#### **Step 6: Verify Schedule Execution (Wait 15 minutes)**

**Purpose:** Confirm automatic materialization triggers on schedule

```bash
# Wait until next 15-minute mark (e.g., if now is 14:07, wait until 14:15)
date

# Check Dagster UI → Runs tab
# ✅ Expected: New run with "Scheduled" tag appears
# ✅ Expected: Run completes successfully

# Check database for updated games
docker compose exec db psql -U postgres -d app -c "
SELECT COUNT(*) as total_runs,
       MAX(updated_at) as last_update
FROM fact_game
WHERE DATE(updated_at) = CURRENT_DATE;
"

# Expected: last_update timestamp within last few minutes
```

---

## ✅ **Success Criteria Checklist**

Mark each item as complete:

- [ ] Production `.env` updated with Dagster variables
- [ ] DNS configured for `dagster.gamepulse.top` (if using subdomain)
- [ ] GitHub Actions workflow completed successfully
- [ ] Dagster webserver container running on port 3000
- [ ] Dagster daemon container running
- [ ] Dagster UI accessible via browser
- [ ] `ncaa_games` asset visible in asset catalog
- [ ] `ncaa_games_schedule` active with cron `*/15 * * * *`
- [ ] Manual materialization completes successfully
- [ ] Database contains games from NCAA API
- [ ] Team sync working (teams in `dim_team` table)
- [ ] Rivalry detection working (rivalry_factor = 1.0 or 1.2)
- [ ] Automatic schedule execution verified (after 15 min wait)
- [ ] CloudWatch logs show no errors (optional)

---

## 🚨 **Troubleshooting Guide**

### **Issue 1: Dagster containers fail to start**

**Symptom:** `docker compose ps` shows dagster-webserver or dagster-daemon as "Exited"

**Diagnosis:**
```bash
docker compose logs dagster-webserver --tail 50
docker compose logs dagster-daemon --tail 50
```

**Common Causes:**
1. **Missing environment variables**
   - Check: `docker compose config | grep DAGSTER`
   - Fix: Update `.env` file with all DAGSTER_* variables

2. **Database connection failed**
   - Check: `docker compose logs db | grep "ready to accept connections"`
   - Fix: Ensure PostgreSQL container is healthy before starting Dagster

3. **Dagster database not initialized**
   - Symptom: Connection errors, `relation "runs" does not exist`, or services in restart loop
   - Cause: The `dagster` database exists but schema hasn't been initialized
   - **Fix:** Manually run initialization:
     ```bash
     # Create database if missing
     docker compose exec db psql -U postgres -c "CREATE DATABASE dagster;"

     # Initialize Dagster schema
     docker compose exec dagster-daemon dagster instance migrate

     # Restart services
     docker compose restart dagster-daemon dagster-webserver
     ```
   - **Prevention:** This should be handled automatically by `prestart.sh` in future deployments

4. **High CPU usage from retry loops**
   - Symptom: `ssm-worker` or Dagster processes consuming high CPU
   - Cause: Services repeatedly failing to connect to uninitialized database
   - **Fix:** Follow step 3 above to initialize the database, CPU should normalize within 1-2 minutes

**Recovery:**
```bash
# Restart Dagster services
docker compose restart dagster-webserver dagster-daemon

# Full reset if needed
docker compose down
docker compose up -d
```

---

### **Issue 2: Schedule not executing**

**Symptom:** No automatic runs appearing in Dagster UI after 15+ minutes

**Diagnosis:**
```bash
# Check daemon is running
docker compose ps dagster-daemon

# Check scheduler daemon logs
docker compose logs dagster-daemon | grep -i scheduler

# Check schedule status
docker compose logs dagster-daemon | grep ncaa_games_schedule
```

**Common Causes:**
1. **Schedule not started**
   - **Fix:** In Dagster UI → Schedules → Toggle schedule ON

2. **Daemon not processing schedules**
   - **Fix:** Restart daemon: `docker compose restart dagster-daemon`

3. **Timezone mismatch**
   - Schedule uses `America/New_York` timezone
   - Check current time in ET: `TZ=America/New_York date`

---

### **Issue 3: Manual materialization fails**

**Symptom:** Run status shows FAILURE in Dagster UI

**Diagnosis:**
```bash
# View run logs in Dagster UI
# Navigate to Runs → Select failed run → View logs

# Check daemon logs
docker compose logs dagster-daemon | grep -A 10 "ERROR\|Exception"
```

**Common Causes:**
1. **NCAA API timeout**
   - Symptom: `httpx.HTTPStatusError` or timeout errors
   - **Fix:** Retry policy will automatically retry 3 times
   - **Manual retry:** Click "Re-execute" in Dagster UI

2. **Database FK constraint failure**
   - Symptom: `ValueError: Home team not found in dim_team`
   - **Fix:** Ensure dimensional data seeded:
     ```bash
     docker compose exec backend alembic current
     # Should show: 7a8f23177a57 (seed_dimensional_data)
     ```

3. **Missing team_group_id for rivalry calculation**
   - Symptom: Rivalry detection returns 1.0 for all games
   - **Expected:** This is normal for non-conference games
   - **Validation:** Check team_group_id is populated:
     ```bash
     docker compose exec db psql -U postgres -d app -c "
     SELECT COUNT(*) as teams_with_conference
     FROM dim_team
     WHERE team_group_id IS NOT NULL;
     "
     # Expected: > 0 (should be ~350 for seeded teams)
     ```

---

### **Issue 4: Dagster UI not accessible via domain**

**Symptom:** `https://dagster.gamepulse.top` returns 404 or connection refused

**Diagnosis:**
```bash
# Check Traefik routing
docker compose logs proxy | grep dagster

# Check Traefik dashboard (if enabled)
curl http://localhost:8090/api/http/routers | jq '.[] | select(.name | contains("dagster"))'

# Check DNS resolution
dig dagster.gamepulse.top
```

**Common Causes:**
1. **DNS not configured**
   - **Fix:** Add A record: `dagster` → `<ELASTIC_IP>`

2. **Traefik labels not applied**
   - **Fix:** Restart proxy: `docker compose restart proxy`

3. **SSL certificate not provisioned**
   - **Wait:** 2-5 minutes for Let's Encrypt
   - **Check:** `docker compose logs proxy | grep dagster | grep certificate`

**Temporary Workaround:**
```bash
# Access via direct port (not HTTPS)
http://<ELASTIC_IP>:3000
```

---

## 📊 **Monitoring & Observability**

### **CloudWatch Logs (Optional)**

If CloudWatch logging is configured:

```bash
# View Dagster daemon logs
aws logs tail /gamepulse/dagster-daemon --follow

# View Dagster webserver logs
aws logs tail /gamepulse/dagster-webserver --follow

# Search for specific events
aws logs filter-pattern /gamepulse/dagster-daemon --filter-pattern "ncaa_games_asset"
```

### **Metrics to Monitor**

**Key Performance Indicators:**
- Schedule execution frequency: Every 15 minutes ✅
- Average materialization duration: ~1-3 seconds ✅
- Games processed per run: 40-60 games (varies by NCAA schedule)
- Asset success rate: Target 99%+ (with 3 retries)

**Alerting Recommendations (Future):**
- Alert if schedule misses 3+ consecutive executions
- Alert if materialization fails after all retries
- Alert if no games processed for 24+ hours (off-season expected)

---

## 🔄 **Rollback Procedure**

If Dagster deployment causes production issues:

### **Option 1: Disable Dagster Services (Keeps Code)**

```bash
# SSH to EC2
cd /opt/gamepulse

# Stop Dagster services only
docker compose stop dagster-webserver dagster-daemon

# Backend/Frontend continue running normally
docker compose ps
```

### **Option 2: Full Rollback (Revert Git)**

```bash
# SSH to EC2
cd /opt/gamepulse

# Find commit before Dagster
git log --oneline -n 5

# Revert to previous commit
git reset --hard <previous-commit-sha>

# Rebuild and restart
docker compose down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Verify rollback
docker compose ps | grep -v dagster
```

### **Option 3: Emergency Stop All Services**

```bash
docker compose down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 📝 **Post-Deployment Notes**

### **Performance Expectations**

**First Run:**
- Duration: ~2-5 seconds (53 games on Nov 12, 2025)
- Team sync: 106 teams discovered and upserted
- Database inserts: 54 games + 106 teams

**Subsequent Runs:**
- Duration: ~1-2 seconds (mostly UPDATEs)
- Team sync: 0 discovered, 106 unchanged
- Database updates: N games updated (live scores)

### **Data Freshness**

**Schedule:** Every 15 minutes
- Games ingested: Today's NCAA Men's Basketball games only
- Live score updates: Every 15 minutes during games
- Historical data: Not backfilled (start date = deployment date)

**Backfill Strategy (Future):**
```python
# To backfill historical games (future feature):
# Option 1: Modify ncaa_games asset to accept date parameter
# Option 2: Create separate backfill asset
# Option 3: Use Dagster's backfill UI for date-partitioned assets
```

### **Cost Considerations**

**AWS Resources:**
- EC2 instance: No additional cost (existing instance)
- Database: No additional cost (same PostgreSQL)
- Storage: ~1MB per day for game data
- Network: Minimal (NCAA API calls: 96/day = ~1KB each)

**Estimated Annual Cost:** $0 (fully self-hosted on existing infrastructure)

---

## 🎯 **Next Steps (Future Stories)**

After successful deployment, consider:

1. **Automated Tests** (Story 2-5 or 2-6)
   - Test asset materialization with mocked NCAA API
   - Test rivalry detection logic with sample data
   - Test retry policy behavior with simulated failures

2. **Alerting & Monitoring** (Epic 3 or 4)
   - Slack/email alerts for schedule failures
   - CloudWatch metrics for materialization duration
   - Dead letter queue for failed runs

3. **Separate Dagster Database** (Technical Debt)
   - Create `dagster` database to avoid Alembic version conflicts
   - Update docker-compose.yml with DAGSTER_POSTGRES_DB=dagster
   - Run Dagster migrations independently

4. **Additional Assets** (Epic 3+)
   - Reddit sentiment ingestion
   - Betting odds ingestion
   - Excitement score calculation
   - Data quality checks

---

## 📞 **Support & Resources**

**Documentation:**
- Dagster Docs: https://docs.dagster.io
- NCAA API: https://github.com/henrygd/ncaa-api
- Project README: /Users/Philip/dev/gamepulse/CLAUDE.md

**Logs & Debugging:**
```bash
# Dagster daemon
docker compose logs -f dagster-daemon

# Dagster webserver
docker compose logs -f dagster-webserver

# Database
docker compose logs -f db

# All services
docker compose logs -f
```

**Health Checks:**
```bash
# Dagster UI
curl -I http://localhost:3000

# Backend API
curl http://localhost:8000/api/v1/utils/health-check/

# Database
docker compose exec db pg_isready -U postgres
```

---

**Last Updated:** 2025-11-12
**Story:** 2-4 - Implement Polling Worker
**Status:** Ready for Production Deployment ✅
