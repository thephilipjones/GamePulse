# Docker Build Optimization: Replace PostgreSQL Client

## Overview

Further optimize backend Docker build performance by replacing `postgresql-client` system package with Python-based database readiness check.

## Current Status

**Implemented**: Phase 1 optimization - Exclude dev dependencies from production (`--no-dev` flag)
- **Savings**: ~40 seconds
- **Build time**: 3:21 → ~2:41

**Not Yet Implemented**: Phase 2 optimization - Replace PostgreSQL client

## Problem Statement

The backend Dockerfile currently installs `postgresql-client` system package to enable the `psql` command in `backend/scripts/prestart.sh` for database readiness checking.

**Cost breakdown**:
- 15-20 seconds: `apt-get update` downloads package indexes
- 25-30 seconds: Installing postgresql-client + 50+ dependencies (libpq5, libssl3, ICU libraries)
- **Total**: ~49 seconds (24% of build time)

## Proposed Solution

Replace system `psql` with Python-based database wait using existing `asyncpg` dependency.

### Implementation

#### Change 1: Remove postgresql-client from Dockerfile

**File**: `backend/Dockerfile` line 9

```dockerfile
# CURRENT:
RUN apt-get update && apt-get install -y postgresql-client curl && rm -rf /var/lib/apt/lists/*

# PROPOSED:
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
```

#### Change 2: Update prestart.sh to use Python

**File**: `backend/scripts/prestart.sh`

Replace the current PostgreSQL wait logic:

```bash
# CURRENT APPROACH (uses psql):
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_SERVER" \
      -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done
```

With Python-based approach using asyncpg:

```bash
# PROPOSED APPROACH (uses Python + asyncpg):
python3 << 'EOF'
import sys
import time
import asyncio

async def wait_for_db():
    from app.core.config import settings
    import asyncpg

    for i in range(60):  # Try for 60 seconds
        try:
            # Attempt connection using existing asyncpg dependency
            conn = await asyncpg.connect(
                host=settings.POSTGRES_SERVER,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                timeout=5.0
            )
            await conn.close()
            print("✅ PostgreSQL is ready!")
            return True
        except Exception as e:
            print(f"⏳ PostgreSQL unavailable ({i+1}/60) - {type(e).__name__}")
            await asyncio.sleep(1)

    print("❌ PostgreSQL failed to become ready after 60 seconds")
    return False

# Run async function
if not asyncio.run(wait_for_db()):
    sys.exit(1)
EOF
```

## Expected Impact

### Performance
- **Build time savings**: ~49 seconds
- **Combined with Phase 1**: 3:21 → ~1:52 (49% total reduction)
- **Image size reduction**: ~50MB smaller

### Benefits
- ✅ No system package installation overhead
- ✅ Smaller attack surface (fewer installed packages)
- ✅ True database readiness check (not just TCP port)
- ✅ Uses existing Python dependencies (no new additions)
- ✅ More maintainable (Python vs bash)

### Trade-offs
- ⚠️ Cannot use `psql` CLI for debugging inside production containers
  - Workaround: Install temporarily if needed: `docker exec backend apt-get update && apt-get install -y postgresql-client`
  - Alternative: Connect from local machine or use Adminer UI
- ⚠️ Slightly more code in prestart.sh (15 lines vs 5 lines)

## Alternative Approach: Netcat

If preferring simpler bash approach, use lightweight `netcat` for TCP-level check:

```dockerfile
# Dockerfile - netcat is lighter than postgresql-client:
RUN apt-get update && apt-get install -y curl netcat-openbsd && rm -rf /var/lib/apt/lists/*
```

```bash
# prestart.sh - TCP port check:
until nc -z "$POSTGRES_SERVER" "$POSTGRES_PORT"; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done
```

**Netcat trade-offs**:
- ✅ Simpler (1-line bash)
- ✅ Faster than postgresql-client (~35s saved vs 49s with Python)
- ⚠️ Still requires `apt-get update` overhead (15-20s)
- ⚠️ Only checks TCP connection, not database readiness
  - Race condition risk: Port open but PostgreSQL still initializing

## Recommendation

**Implement Python approach** for:
1. Maximum savings (49s vs 35s with netcat)
2. True database readiness verification
3. Zero new dependencies
4. Production-grade robustness

## Timeline

Priority: **Medium** (nice-to-have optimization, not critical)

Suggested implementation: When next revisiting Docker build performance or if build times become a bottleneck again.

## Related

- Phase 1 optimization implemented: `backend/Dockerfile` lines 32, 54 (`--no-dev` flags)
- Current build performance: Frontend 9s, Backend ~2:41 (after Phase 1)
