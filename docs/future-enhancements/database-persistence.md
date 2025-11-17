# Database Persistence & Backup Strategy

## Current State

**Architecture:**
- PostgreSQL 16 with TimescaleDB extension running in Docker container on EC2
- Data stored in Docker volume: `app-db-data` → `/var/lib/docker/volumes/gamepulse_app-db-data/_data`
- Volume location: EC2 root EBS volume (30GB gp3)

**Data Persistence Status:**
- ✅ **Safe during EC2 stop/start** - Docker volume persists on EBS
- ⚠️ **At risk during EC2 termination** - Data lost if instance is terminated
- ⚠️ **At risk during EBS failure** - No redundancy, no automated backups
- ❌ **No automated backups configured** - Manual recovery only

**Risk Assessment:**
- **Low risk:** Accidentally stopping instance (data persists)
- **Medium risk:** EBS volume corruption or failure (rare but possible)
- **High risk:** Accidentally terminating instance instead of stopping
- **High risk:** Region-wide AWS outage (no multi-region redundancy)

## Future Enhancement Options

### Option 1: Automated S3 Backups (Recommended - FREE)

**Best for:** Portfolio projects, low budget, learning

**Implementation:**
1. Daily `pg_dump` to compressed SQL file
2. Upload to S3 bucket with lifecycle policies
3. Automated via cron job or Dagster scheduled asset

**Cost:**
- S3 Standard: ~$0.023/GB/month
- Estimated: ~$0.50/month for typical usage
- First 5GB of S3 storage is free (12 months for new AWS accounts)

**Pros:**
- ✅ Extremely cheap (nearly free)
- ✅ Simple to implement
- ✅ Portable backups (restore anywhere)
- ✅ No infrastructure changes required
- ✅ Lifecycle policies for automatic cleanup (e.g., keep 30 days)

**Cons:**
- ⚠️ Manual restore required
- ⚠️ Backup frequency limited by cron schedule (e.g., daily)
- ⚠️ Not point-in-time recovery (only restore to snapshot time)

**Implementation Steps:**
```bash
# 1. Create S3 bucket via Terraform
# Add to terraform/modules/storage/main.tf

# 2. Create backup script
# backend/scripts/backup-postgres-to-s3.sh

# 3. Add Dagster scheduled asset or cron job
# Asset: backup_postgres_to_s3 (runs daily at 2 AM)

# 4. Configure retention policy
# S3 lifecycle: Delete backups older than 30 days
```

**Restore Process:**
```bash
# Download backup from S3
aws s3 cp s3://gamepulse-backups/postgres/backup-2025-11-16.sql.gz /tmp/

# Restore to PostgreSQL
gunzip /tmp/backup-2025-11-16.sql.gz
docker compose exec -T db psql -U postgres -d app < /tmp/backup-2025-11-16.sql
```

**Related Files:**
- `backend/scripts/backup-postgres-to-s3.sh` (to be created)
- `backend/app/assets/backup_postgres.py` (Dagster asset - to be created)
- `terraform/modules/storage/s3_backups.tf` (to be created)

---

### Option 2: EBS Snapshots via AWS Backup (FREE Tier)

**Best for:** Simple automated backups with AWS-native tools

**Implementation:**
- AWS Backup plan with daily EBS snapshots
- Retention: 7 days (configurable)
- Automated via AWS Backup service

**Cost:**
- AWS Backup Free Tier: 10GB backup storage/month (first 12 months)
- After free tier: ~$0.05/GB/month for EBS snapshots
- Estimated: ~$1.50/month for 30GB volume

**Pros:**
- ✅ Fully automated (set and forget)
- ✅ Point-in-time snapshots of entire system
- ✅ Easy restore (create new EBS volume from snapshot)
- ✅ Incremental backups (only stores changes)

**Cons:**
- ⚠️ Backs up entire EBS volume, not just database (inefficient)
- ⚠️ Requires instance downtime to attach restored volume
- ⚠️ More expensive than S3 long-term

**Implementation Steps:**
```bash
# Add to terraform/modules/compute/backup.tf
# - AWS Backup vault
# - Backup plan (daily snapshots, 7-day retention)
# - IAM role for AWS Backup
```

**Restore Process:**
1. Create new EBS volume from snapshot
2. Stop EC2 instance
3. Detach old root volume
4. Attach new volume from snapshot
5. Start instance

---

### Option 3: Separate EBS Volume for Database (FREE)

**Best for:** Isolating database data from system data

**Implementation:**
- Provision separate EBS volume (e.g., 20GB gp3)
- Mount at `/mnt/postgres-data`
- Update Docker Compose to use mounted volume

**Cost:**
- Included in EC2 free tier (30GB total EBS storage)
- After free tier: ~$0.08/GB/month for gp3
- Estimated: ~$1.60/month for 20GB

**Pros:**
- ✅ Can detach/reattach volume to new instances
- ✅ Snapshots only back up database (more efficient)
- ✅ Better isolation (system upgrades don't affect data)
- ✅ Same cost as current setup (within free tier)

**Cons:**
- ⚠️ Requires Terraform infrastructure changes
- ⚠️ Requires Docker Compose volume mapping changes
- ⚠️ Manual snapshot/restore process (unless combined with AWS Backup)

**Implementation Steps:**
```bash
# 1. Add EBS volume to Terraform
# terraform/modules/compute/ebs_volume.tf

# 2. Mount volume in user_data.sh
# Format, mount at /mnt/postgres-data

# 3. Update Docker Compose volume binding
# volumes:
#   - /mnt/postgres-data:/var/lib/postgresql/data/pgdata
```

**Migration Process:**
1. Create new EBS volume
2. Stop PostgreSQL container
3. Copy data from Docker volume to new EBS volume
4. Update docker-compose.yml volume binding
5. Restart container

---

### Option 4: AWS RDS for PostgreSQL (FREE for 12 months, then ~$15-20/month)

**Best for:** Production workloads, managed service benefits

**Eligibility:** Only if AWS account is <12 months old

**Implementation:**
- Provision db.t4g.micro RDS instance (ARM-based, cheapest)
- Enable automated backups (7-30 days retention)
- Update backend to connect to RDS endpoint

**Cost:**
- **Free Tier (12 months):** db.t3.micro or db.t4g.micro, 20GB storage
- **After free tier:** ~$15-20/month for db.t4g.micro
- **Annual cost:** ~$180-240/year

**Pros:**
- ✅ Fully managed (automated backups, patches, monitoring)
- ✅ Automated failover (Multi-AZ if enabled)
- ✅ Point-in-time recovery (PITR)
- ✅ Better isolation from EC2 instance
- ✅ CloudWatch metrics and alarms

**Cons:**
- ❌ Not free long-term ($180-240/year)
- ❌ Overkill for portfolio project
- ⚠️ May not support TimescaleDB extension (RDS for PostgreSQL has limited extensions)
- ⚠️ Network latency between EC2 and RDS (minimal, but exists)

**Implementation Steps:**
```bash
# 1. Add RDS module to Terraform
# terraform/modules/rds/main.tf

# 2. Update backend environment variables
# POSTGRES_SERVER=<rds-endpoint>
# POSTGRES_PORT=5432

# 3. Migrate data from Docker PostgreSQL to RDS
# pg_dump from Docker, pg_restore to RDS

# 4. Remove PostgreSQL container from docker-compose.yml
```

**TimescaleDB Compatibility:**
- ⚠️ AWS RDS does NOT support TimescaleDB extension
- Alternative: Use AWS Timestream (time-series database) or migrate to vanilla PostgreSQL

---

### Option 5: External Managed PostgreSQL (FREE forever)

**Best for:** Zero infrastructure management, free forever

**Providers:**

#### **Supabase Free Tier**
- 500MB database storage
- Unlimited API requests
- Automated daily backups (7-day retention)
- PostgreSQL 15 with extensions (including pgvector, but NOT TimescaleDB)
- Pauses after 1 week of inactivity (auto-resumes on first request)
- Free SSL, connection pooling

**Pros:**
- ✅ Completely free forever
- ✅ Managed backups included
- ✅ Better uptime than self-hosted
- ✅ Built-in auth, realtime, storage (if needed)

**Cons:**
- ⚠️ 500MB storage limit (may be tight for long-term accumulation)
- ❌ No TimescaleDB extension
- ⚠️ Pauses after 1 week inactivity (1-2 second cold start)
- ⚠️ Third-party dependency (vendor lock-in)

#### **Neon Free Tier**
- 512MB storage per database (3GB total across all projects)
- Serverless PostgreSQL (scales to zero)
- Automatic branching (Git-like for databases)
- 5 projects, 10 branches per project

**Pros:**
- ✅ Free forever
- ✅ Git-like branching (useful for testing migrations)
- ✅ Serverless (no idle cost)

**Cons:**
- ⚠️ 512MB storage limit per database
- ❌ No TimescaleDB extension
- ⚠️ Cold starts (~1-2 seconds)

**Implementation Steps:**
```bash
# 1. Sign up for Supabase or Neon
# 2. Create PostgreSQL database
# 3. Update backend environment variables
#    POSTGRES_SERVER=<supabase-host>
#    POSTGRES_PORT=5432
#    POSTGRES_USER=postgres
#    POSTGRES_PASSWORD=<generated-password>
# 4. Migrate data (pg_dump/restore)
# 5. Remove PostgreSQL container from docker-compose.yml
```

**TimescaleDB Migration:**
- Convert hypertables to regular tables (lose time-series optimizations)
- Or: Keep Docker PostgreSQL on EC2 for TimescaleDB features

---

## Comparison Matrix

| Option                     | Cost/Month | Setup Effort | Maintenance | TimescaleDB | Restore Time | Best For                  |
|----------------------------|------------|--------------|-------------|-------------|--------------|---------------------------|
| **S3 Backups**             | ~$0.50     | Low          | Low         | ✅ Yes      | ~10 min      | Portfolio, learning       |
| **EBS Snapshots**          | ~$1.50     | Very Low     | Very Low    | ✅ Yes      | ~20 min      | Simple automation         |
| **Separate EBS Volume**    | $0         | Medium       | Low         | ✅ Yes      | ~15 min      | Isolation, flexibility    |
| **AWS RDS**                | $15-20     | Medium       | Very Low    | ❌ No       | ~5 min       | Production, managed       |
| **Supabase/Neon**          | $0         | Low          | Very Low    | ❌ No       | Instant      | Zero-cost, hobby projects |

---

## Recommended Implementation Path

### **Phase 1 (Now): Implement S3 Backups**
- Zero cost increase
- Simple bash script + Dagster scheduled asset
- Covers 80% of disaster recovery scenarios

### **Phase 2 (Optional): Add EBS Snapshots**
- One-time Terraform configuration
- Provides system-level recovery option
- Useful if entire instance needs to be restored

### **Phase 3 (If scaling up): Consider RDS or Supabase**
- Only if:
  - Budget allows ($180-240/year for RDS)
  - Need managed service benefits
  - Willing to migrate away from TimescaleDB

---

## Action Items

- [ ] **Epic 9 (Future):** Implement S3 backup automation
  - [ ] Story 9-1: Create S3 bucket for backups (Terraform)
  - [ ] Story 9-2: Create `backup_postgres_to_s3` Dagster asset
  - [ ] Story 9-3: Configure S3 lifecycle policies (30-day retention)
  - [ ] Story 9-4: Test restore process and document in runbook

- [ ] **Epic 10 (Future):** Implement EBS snapshot automation
  - [ ] Story 10-1: Create AWS Backup plan (Terraform)
  - [ ] Story 10-2: Configure backup vault and retention
  - [ ] Story 10-3: Test restore process from snapshot

---

## Related Documentation

- [CLAUDE.md - Infrastructure & Deployment](../CLAUDE.md#infrastructure--deployment)
- [Database Migrations](../CLAUDE.md#database--migrations)
- [Disaster Recovery Runbook](./runbooks/disaster-recovery.md) (to be created)

---

## References

- [AWS Backup Pricing](https://aws.amazon.com/backup/pricing/)
- [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [AWS RDS Free Tier](https://aws.amazon.com/rds/free/)
- [Supabase Free Tier](https://supabase.com/pricing)
- [Neon Free Tier](https://neon.tech/pricing)
- [TimescaleDB on AWS](https://docs.timescale.com/self-hosted/latest/install/installation-docker/)
