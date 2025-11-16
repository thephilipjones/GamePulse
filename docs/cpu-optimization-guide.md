# CPU Optimization Guide for t2.micro

**Current State:** ~16% CPU usage at rest
**Target:** <10% CPU usage
**Instance Type:** AWS t2.micro (1 vCPU, 1GB RAM)
**Last Updated:** 2025-11-14

## Executive Summary

This guide provides a roadmap to reduce CPU usage from 16% to below 10% on the t2.micro instance. The optimizations are divided into two phases with an expected total CPU reduction of 8-13%.

**Critical Context:** Story 3.6 will increase Dagster polling from every 15 minutes to every 1 minute (15x increase in frequency). These optimizations should be implemented **before** deploying Story 3.6 to avoid CPU budget overruns.

---

## Current Stack & CPU Contributors

**Services Running:**
- FastAPI backend (1 worker, production mode)
- React frontend (nginx static server)
- PostgreSQL with TimescaleDB extension
- Dagster webserver + daemon (data orchestration)
- Traefik reverse proxy
- Adminer database UI

**Known CPU Optimizations Already Applied:**
- ✅ Backend runs without `--reload` flag (removed WatchFiles auto-reloader)
- ✅ Healthchecks reduced from 10s to 30-60s intervals
- ✅ Single FastAPI worker (optimized for single vCPU)
- ✅ PostgreSQL memory tuning for 1GB RAM
- ✅ Traefik access logs disabled

---

## Phase 1: Quick Wins (Expected: -5-8% CPU)

### 1. Reduce Dagster Daemon Polling Overhead (-3-5% CPU)

**Problem:** Dagster daemon polls database every 5-10 seconds checking for scheduled runs, sensors, and pending executions. This is wasteful when schedules run every 15 minutes.

**Solution:** Create optimized Dagster configuration file.

**Implementation:**

```bash
# Create dagster.yaml if it doesn't exist
mkdir -p backend/dagster_home
cat > backend/dagster_home/dagster.yaml <<'EOF'
# Dagster instance configuration
run_coordinator:
  module: dagster.core.run_coordinator
  class: QueuedRunCoordinator
  config:
    max_concurrent_runs: 1
    dequeue_interval_seconds: 30  # Increased from default 5s
    tag_concurrency_limits:
      - key: "database"
        value: "main"
        limit: 1

# Daemon polling configuration
daemon:
  heartbeat_interval_seconds: 60  # Default is 30s
  run_monitoring_interval_seconds: 60  # Default is 30s

# Storage configuration (uses environment variable DAGSTER_POSTGRES_URL)
storage:
  postgres:
    postgres_url:
      env: DAGSTER_POSTGRES_URL
EOF
```

**Update docker-compose.yml to mount config:**

```yaml
dagster-daemon:
  volumes:
    - ./backend/dagster_home:/tmp/dagster_home:ro  # Ensure this line exists
```

**Validation:**

```bash
# After deployment, check logs to verify config is loaded
docker compose logs dagster-daemon | grep -i "config\|interval"

# Should see references to 30s and 60s intervals
```

**Trade-off:** Schedule execution may be delayed by 30-60 seconds (acceptable for sports data refresh).

---

### 2. Disable Adminer in Production (-1-2% CPU)

**Problem:** Adminer container runs 24/7 but is only needed for occasional database debugging. Currently set to `replicas: 0` in production, but container still defined and consuming resources.

**Solution:** Use Docker Compose profiles to completely exclude Adminer from production.

**Implementation:**

```yaml
# docker-compose.yml - Add profile to adminer service
adminer:
  image: adminer
  profiles: ["dev"]  # ADD: Only start in development mode
  restart: always
  ports:
    - "8080:8080"
  networks:
    - default
  depends_on:
    - db
```

**Remove from docker-compose.prod.yml:**

```yaml
# docker-compose.prod.yml - DELETE the entire adminer section
# adminer:
#   deploy:
#     replicas: 0
```

**Deployment Commands:**

```bash
# Development: Start with Adminer
docker compose --profile dev up -d

# Production: Adminer completely excluded
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Validation:**

```bash
# Verify Adminer is NOT running in production
docker compose ps | grep adminer
# Should return nothing
```

---

### 3. Relax Healthcheck Frequencies (-1% CPU)

**Problem:** Healthchecks spawn processes and make HTTP/DB connections every 60-120 seconds. With `restart: always` policy, failures trigger restarts regardless of check frequency.

**Solution:** Increase healthcheck intervals to 2-3 minutes.

**Implementation:**

Update `docker-compose.prod.yml`:

```yaml
services:
  backend:
    healthcheck:
      test: curl --fail http://localhost:8000/api/v1/health || exit 1
      interval: 120s  # Increased from 60s
      timeout: 10s
      retries: 3
      start_period: 30s

  db:
    healthcheck:
      test: pg_isready -U ${POSTGRES_USER:-postgres} || exit 1
      interval: 120s  # Increased from 60s
      timeout: 10s
      retries: 3
      start_period: 30s

  dagster-daemon:
    healthcheck:
      test: dagster instance info || exit 1
      interval: 180s  # Increased from 120s
      timeout: 20s
      retries: 3
      start_period: 60s

  dagster-webserver:
    healthcheck:
      test: curl --fail http://localhost:3000 || exit 1
      interval: 180s  # Increased from 120s
      timeout: 20s
      retries: 3
      start_period: 60s

  frontend:
    healthcheck:
      test: curl --fail http://localhost:80 || exit 1
      interval: 120s  # Increased from 60s
      timeout: 10s
      retries: 3
      start_period: 30s
```

**Validation:**

```bash
# Check healthcheck status
docker compose ps --format json | jq '.[].Health'
```

**Trade-off:** Unhealthy containers detected 60-120 seconds later (still acceptable for non-critical services).

---

## Phase 2: Service Optimization (Expected: -3-5% CPU)

### 4. Optimize Nginx for Single vCPU (-1-2% CPU)

**Problem:** Nginx using default configuration likely runs multiple worker processes and collects access logs, consuming unnecessary CPU.

**Solution:** Create optimized nginx configuration for t2.micro.

**Implementation:**

Create `frontend/nginx-prod.conf`:

```nginx
user nginx;
worker_processes 1;  # Single vCPU - no need for multiple workers
worker_rlimit_nofile 1024;

error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 512;  # Reduced from default 1024
    use epoll;  # Linux-optimized event model
    multi_accept off;  # Single connection per accept (lower CPU)
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 30;  # Reduced from default 65
    keepalive_requests 50;  # Limit requests per connection

    # Disable access logging (huge CPU saver, Traefik already logs)
    access_log off;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    include /etc/nginx/conf.d/*.conf;
}
```

Update `frontend/Dockerfile`:

```dockerfile
# Stage 1: Build
FROM node:lts AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:1
COPY --from=build-stage /app/dist/ /usr/share/nginx/html
COPY ./nginx-prod.conf /etc/nginx/nginx.conf  # ADD: Use optimized config
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Validation:**

```bash
# Check nginx worker processes after deployment
docker compose exec frontend ps aux | grep nginx
# Should see only 1 worker process

# Verify access logs disabled
docker compose exec frontend ls -la /var/log/nginx/
# access.log should be missing or empty
```

---

### 5. Add PostgreSQL CPU Tuning (-1-2% CPU)

**Problem:** PostgreSQL defaults assume multi-core CPU and enable parallel query execution, which adds overhead on single-vCPU systems.

**Solution:** Disable parallel queries and optimize for single-core execution.

**Implementation:**

Update `docker-compose.prod.yml`:

```yaml
db:
  command:
    - "postgres"
    # Existing memory settings (keep these)
    - "-c"
    - "shared_buffers=128MB"
    - "-c"
    - "max_connections=20"
    - "-c"
    - "work_mem=4MB"
    - "-c"
    - "effective_cache_size=512MB"
    - "-c"
    - "maintenance_work_mem=64MB"

    # ADD: CPU optimization settings
    - "-c"
    - "max_parallel_workers=1"  # Single vCPU - no parallel queries
    - "-c"
    - "max_parallel_workers_per_gather=0"  # Disable parallel query execution
    - "-c"
    - "max_worker_processes=4"  # Reduce from default 8
    - "-c"
    - "effective_io_concurrency=100"  # Reduce from default 200
    - "-c"
    - "checkpoint_completion_target=0.9"  # Spread checkpoints over time
    - "-c"
    - "wal_buffers=4MB"  # Reduce WAL overhead
    - "-c"
    - "min_wal_size=512MB"  # Reduce checkpoint frequency
    - "-c"
    - "max_wal_size=1GB"
```

**Validation:**

```bash
# Check PostgreSQL settings after deployment
docker compose exec db psql -U postgres -c "SHOW max_parallel_workers;"
docker compose exec db psql -U postgres -c "SHOW max_parallel_workers_per_gather;"
# Both should show configured values
```

**Reference:** PostgreSQL tuning based on [PGTune](https://pgtune.leopard.in.ua/) recommendations for 1GB RAM systems.

---

### 6. Optimize Traefik Polling (-1% CPU)

**Problem:** Traefik polls Docker API frequently to detect container changes and performs header validation on every request.

**Solution:** Reduce polling frequency and skip unnecessary validation.

**Implementation:**

Update `docker-compose.prod.yml`:

```yaml
proxy:
  command:
    # ... existing config ...
    - --log.level=ERROR
    - --accesslog=false
    - --providers.docker=true
    - --providers.docker.exposedbydefault=false

    # ADD: CPU optimization flags
    - --providers.docker.watch=true
    - --providers.docker.pollTimeout=5s  # Reduce from default 15s
    - --entryPoints.http.forwardedHeaders.insecure=true  # Skip header validation
    - --entryPoints.https.forwardedHeaders.insecure=true
    - --global.sendAnonymousUsage=false  # Disable telemetry

    # ... rest of config ...
```

**Validation:**

```bash
# Check Traefik logs for polling activity
docker compose logs proxy | grep -i "poll\|provider"

# Should see reduced polling messages
```

---

## Story 3.6 Deployment Strategy

### Critical Context

Story 3.6 changes Dagster schedule from:
- **Current:** Every 15 minutes (`*/15 * * * *`)
- **Proposed:** Every 1 minute (`*/1 * * * *`)

This is a **15x increase in polling frequency** that will add an estimated +5-10% CPU load.

### Staged Rollout Approach

**Option A: Deploy with 5-minute Polling (Recommended)**

Start with a compromise that provides 3x improvement without the full 15x impact:

```python
# backend/app/dagster_definitions.py
ncaa_games_schedule = ScheduleDefinition(
    name="ncaa_games_schedule",
    cron_schedule="*/5 * * * *",  # Every 5 minutes (compromise)
    target=ncaa_games_asset_job,
)
```

**Validation:**
- Monitor CPU for 48 hours
- If CPU stays <12%: Proceed to 1-minute polling
- If CPU >12%: Stay at 5-minute polling (still 3x improvement)

**Option B: Deploy with 1-minute Polling (Only if Phase 1+2 Complete)**

Only consider this if:
1. Phase 1 optimizations deployed and CPU <10% for 48+ hours
2. Phase 2 optimizations deployed and CPU <8% for 48+ hours
3. You have headroom for +5-10% increase

**Monitoring:**

```bash
# Before Story 3.6 deployment
ssh ubuntu@<instance-ip>
top -bn1 | head -15
# Record baseline CPU

# After deployment, monitor every minute for 1 hour
for i in {1..60}; do
  echo "$(date): $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')" >> cpu_monitor.log
  sleep 60
done

# Calculate average
awk '{sum+=$2; count++} END {print "Average CPU:", sum/count "%"}' cpu_monitor.log
```

---

## Measurement & Validation

### Baseline Measurement (Before Optimization)

```bash
# SSH to EC2 instance
ssh ubuntu@<instance-ip>

# Check current CPU usage
top -bn1 | head -15
# Note: Look for "Cpu(s): XX.X%us" line

# Monitor over 1 hour to establish baseline
top -d 60 -n 60 -b | grep "Cpu(s)" > baseline_cpu.log

# Calculate average
awk '/Cpu/ {
  gsub("%us.*", "", $2);
  sum+=$2;
  count++
} END {
  print "Average CPU:", sum/count "%"
}' baseline_cpu.log
```

**Expected baseline:** ~16% CPU

### After Phase 1 Deployment

```bash
# Wait 30 minutes for system to stabilize
sleep 1800

# Monitor for 1 hour
top -d 60 -n 60 -b | grep "Cpu(s)" > phase1_cpu.log

# Calculate average and compare to baseline
awk '/Cpu/ {
  gsub("%us.*", "", $2);
  sum+=$2;
  count++
} END {
  print "Phase 1 Average CPU:", sum/count "%"
}' phase1_cpu.log
```

**Target:** <10% CPU sustained

### After Phase 2 Deployment

Repeat the same monitoring process.

**Target:** <8% CPU sustained

### Success Criteria

| Phase | Target CPU | If Target Missed | Next Steps |
|-------|-----------|------------------|------------|
| Phase 1 Complete | <10% | Rollback or troubleshoot | Fix before proceeding |
| Phase 2 Complete | <8% | Acceptable if <10% | Proceed with caution |
| Story 3.6 (5-min) | <12% | Rollback Story 3.6 | Stay at 15-min polling |
| Story 3.6 (1-min) | <15% | Rollback to 5-min | 5-min is acceptable |

---

## Rollback Procedures

### If CPU Exceeds Thresholds

**Immediate Rollback:**

```bash
# SSH to instance
ssh ubuntu@<instance-ip>
cd /opt/gamepulse

# Option 1: Revert last git commit
git log --oneline -n 5
git revert <bad-commit-sha>
git push origin main

# Option 2: Reset to known good commit (more aggressive)
git reset --hard <good-commit-sha>
git push origin main --force

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

**Fallback for Story 3.6:**

```bash
# Edit schedule back to 15 minutes
nano backend/app/dagster_definitions.py
# Change: cron_schedule="*/1 * * * *"
# To:     cron_schedule="*/15 * * * *"

# Commit and push
git add backend/app/dagster_definitions.py
git commit -m "Rollback Story 3.6: Revert to 15-minute polling due to CPU constraints"
git push origin main
```

### Emergency Options

If optimizations don't achieve <10% target:

1. **Disable Dagster entirely** (temporary)
   ```bash
   docker compose stop dagster-daemon dagster-webserver
   ```

2. **Consider instance upgrade**
   - **t3.small:** 2 vCPU, 2GB RAM, ~$15/month (50% more expensive)
   - **t3a.small:** 2 vCPU, 2GB RAM, ~$13.50/month (AMD, 10% cheaper)
   - **t4g.small:** 2 vCPU, 2GB RAM, ~$12/month (ARM, requires image rebuild)

---

## Implementation Checklist

### Pre-Implementation

- [ ] Establish baseline CPU metrics (1-hour average)
- [ ] Document current service configurations
- [ ] Verify swap space is configured (should show 4GB)
  ```bash
  swapon --show
  free -h
  ```
- [ ] Create git branch for optimizations
  ```bash
  git checkout -b cpu-optimization
  ```

### Phase 1: Quick Wins

- [ ] Create `backend/dagster_home/dagster.yaml` with optimized settings
- [ ] Add `profiles: ["dev"]` to adminer service
- [ ] Update healthcheck intervals in `docker-compose.prod.yml`
- [ ] Commit changes with descriptive message
- [ ] Deploy to production
- [ ] Monitor for 48 hours
- [ ] Validate CPU <10% sustained

### Phase 2: Service Optimization

- [ ] Create `frontend/nginx-prod.conf` with optimized settings
- [ ] Update `frontend/Dockerfile` to use new nginx config
- [ ] Add PostgreSQL CPU tuning flags to `docker-compose.prod.yml`
- [ ] Add Traefik optimization flags to `docker-compose.prod.yml`
- [ ] Commit changes with descriptive message
- [ ] Deploy to production
- [ ] Monitor for 48 hours
- [ ] Validate CPU <8% sustained

### Story 3.6 Preparation

- [ ] Confirm Phase 1+2 CPU targets met
- [ ] Decide on polling frequency (1-min vs 5-min)
- [ ] Update schedule in `backend/app/dagster_definitions.py`
- [ ] Deploy Story 3.6
- [ ] Monitor intensively for first 24 hours
- [ ] Validate CPU stays within budget

---

## Monitoring Commands Reference

```bash
# Real-time CPU monitoring (refresh every 5 seconds)
top -d 5

# CPU usage over time (1-hour log)
top -d 60 -n 60 -b | grep "Cpu(s)" > cpu_$(date +%Y%m%d_%H%M%S).log

# Per-container CPU usage (requires docker stats)
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Historical CloudWatch metrics (from local machine)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$(terraform output -raw instance_id) \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Check swap usage (should be low if CPU optimized)
free -h
cat /proc/swaps

# Identify top CPU-consuming processes
ps aux --sort=-%cpu | head -10

# Check Dagster daemon activity
docker compose logs dagster-daemon --tail 100 | grep -i "schedule\|run\|material"
```

---

## Additional Low-Impact Optimizations (Optional)

### Disable Docker Stats Collection

If Phase 1+2 don't achieve target, consider this additional optimization:

```bash
# Edit Docker daemon config
sudo nano /etc/docker/daemon.json

# Add:
{
  "metrics-addr": "127.0.0.1:9323",
  "experimental": false,
  "live-restore": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "disable-legacy-registry": true
}

# Restart Docker
sudo systemctl restart docker

# Restart all containers
cd /opt/gamepulse
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Expected impact:** -0.5% CPU
**Risk:** Medium (requires Docker restart)

---

## Summary Table

| Optimization | Expected CPU Reduction | Implementation Time | Risk | Priority |
|-------------|----------------------|-------------------|------|----------|
| Dagster daemon polling | 3-5% | 30 min | Low | **HIGH** |
| Disable Adminer | 1-2% | 15 min | Low | **HIGH** |
| Healthcheck frequency | 1% | 30 min | Low | **HIGH** |
| Nginx optimization | 1-2% | 1 hour | Low-Med | MEDIUM |
| PostgreSQL CPU tuning | 1-2% | 1 hour | Low-Med | MEDIUM |
| Traefik optimization | 1% | 30 min | Low | MEDIUM |
| Staged Story 3.6 rollout | Avoid +5-10% | N/A | Low | **HIGH** |
| Docker stats disable | 0.5% | 15 min | Med | LOW |
| **TOTAL POTENTIAL** | **8-13%** | **~5 hours** | - | - |

---

## References

- [PostgreSQL Tuning for Low-Memory Systems](https://pgtune.leopard.in.ua/)
- [Nginx Performance Optimization](https://www.nginx.com/blog/tuning-nginx/)
- [Dagster Deployment Configuration](https://docs.dagster.io/deployment/dagster-instance)
- [Docker Compose Healthcheck Best Practices](https://docs.docker.com/compose/compose-file/compose-file-v3/#healthcheck)
- [AWS EC2 T2 Unlimited and CPU Credits](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-unlimited-mode.html)

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-11-14 | Claude Code | Initial comprehensive optimization guide |
