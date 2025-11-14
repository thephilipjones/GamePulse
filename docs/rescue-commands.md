# EC2 Emergency Recovery Commands

**Purpose**: Emergency procedures for recovering an overloaded t2.micro EC2 instance when Docker services consume excessive CPU/memory.

**When to Use**: Use these commands when:
- CPU usage is >90% sustained (credit bankruptcy)
- SSH is slow or unresponsive
- Docker containers are unresponsive
- System is thrashing (high swap usage)

---

## ⚠️ WARNING

These commands are **destructive** and will:
- Stop all running Docker containers
- Interrupt active user sessions
- Cause temporary service downtime

Only use during emergencies when normal operations are impossible.

---

## Recovery Procedure

### Step 1: Stop Docker Services

Stops the Docker daemon and socket to immediately release CPU/memory resources.

```bash
sudo systemctl stop docker.socket docker.service
```

**Expected Result**: CPU should drop from 90%+ to <20% within 30 seconds.

---

### Step 2: Verify Docker is Stopped

Confirm Docker daemon and socket are fully stopped.

```bash
sudo systemctl status docker docker.socket
```

**Expected Output**:
```
● docker.service - Docker Application Container Engine
   Loaded: loaded
   Active: inactive (dead) since ...

● docker.socket - Docker Socket for the API
   Loaded: loaded
   Active: inactive (dead) since ...
```

---

### Step 3: Restart Docker and Kill Runaway Containers

Restarts Docker daemon, then immediately kills all running containers to prevent resource spike.

```bash
sudo systemctl start docker && sudo docker kill $(sudo docker ps -q)
```

**Expected Result**:
- Docker daemon starts
- All containers forcefully terminated
- CPU remains low (<20%)

**Note**: This kills ALL containers. After recovery, restart needed services:

```bash
cd /opt/gamepulse
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Post-Recovery Checklist

After executing recovery commands:

- [ ] Verify CPU usage normalized (<20%): `top`
- [ ] Check swap usage reduced: `free -h`
- [ ] Restart GamePulse services: `docker compose up -d`
- [ ] Verify services healthy: `docker compose ps`
- [ ] Check application health: `curl http://localhost:8000/api/v1/utils/health-check/`
- [ ] Review logs for root cause: `docker compose logs --tail=100`

---

## Root Cause Analysis

**Common causes of EC2 overload:**

1. **Development mode in production** (Story 2-4 issue)
   - Symptom: 28% CPU at rest, WatchFiles polling
   - Fix: Use `docker compose -f docker-compose.yml -f docker-compose.prod.yml` (exclude override)
   - See: `CLAUDE.md` "Issue: High CPU usage / Credit Bankruptcy on t2.micro"

2. **Dagster daemon infinite retry loop** (Story 2-3b issue)
   - Symptom: dagster-daemon and ssm-worker consuming 100% CPU
   - Fix: Initialize Dagster database schema (`dagster instance migrate`)
   - See: `CLAUDE.md` "Issue: Dagster services won't start"

3. **Memory exhaustion triggering swap thrashing**
   - Symptom: High swap usage, system freezing
   - Fix: 4GB swap configured, but may need container memory limits
   - See: `CLAUDE.md` "Issue: Out of Memory (OOM) errors"

4. **Too many concurrent builds/tests**
   - Symptom: CPU spike during CI/CD deployment
   - Fix: Stagger deployments, use remote ECR builds

---

## Prevention

**Proactive measures to avoid emergencies:**

- ✅ Always use production compose files: `-f docker-compose.yml -f docker-compose.prod.yml`
- ✅ Verify Dagster database initialized before starting daemon
- ✅ Monitor CPU credit balance (CloudWatch alarm recommended)
- ✅ Set Docker container memory limits for t2.micro (1GB total RAM)
- ✅ Use remote ECR builds instead of building on EC2

---

## Related Documentation

- [CLAUDE.md - Troubleshooting Section](../CLAUDE.md#troubleshooting)
- [Issue: High CPU usage on t2.micro](../CLAUDE.md#issue-high-cpu-usage--credit-bankruptcy-on-t2micro-28-resting-cpu)
- [Issue: Dagster services won't start](../CLAUDE.md#issue-dagster-services-wont-start-or-in-restart-loop)

---

**Last Updated**: 2025-11-13
**Tested On**: Ubuntu 24.04 LTS, t2.micro EC2 instance
