# TimescaleDB Best Practices for GamePulse

## Critical Requirement: Partitioning Column in Primary Key

**Issue encountered 3+ times during implementation:**

When creating a TimescaleDB hypertable, the partitioning column (typically `created_at`) **MUST** be included in the primary key.

### Error Message
```
psycopg.DatabaseError: cannot create a unique index without the column "created_at" (used in partitioning)
HINT: If you're creating a hypertable on a table with a primary key, ensure the partitioning column is part of the primary or composite key.
```

### Solution Pattern

**❌ WRONG:**
```python
class MyTable(SQLModel, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("platform", "post_id"),  # Missing created_at!
    )
    platform: str
    post_id: str
    created_at: datetime  # Partitioning column
```

**✅ CORRECT:**
```python
class MyTable(SQLModel, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("platform", "post_id", "created_at"),  # Include partitioning column
    )
    platform: str
    post_id: str
    created_at: datetime  # Partitioning column
```

### Migration Pattern

```python
# Step 1: Create table with composite PK including partitioning column
sa.PrimaryKeyConstraint("platform", "post_id", "created_at", name="my_table_pkey")

# Step 2: Convert to hypertable
op.execute("""
    SELECT create_hypertable(
        'my_table',
        'created_at',  -- This column MUST be in the PK
        chunk_time_interval => INTERVAL '1 day',
        if_not_exists => TRUE
    );
""")
```

### Affected Tables
1. `raw_bluesky_posts`: PK (post_uri, created_at)
2. `stg_social_posts`: PK (platform, post_id, created_at)

### References
- Story 4-2: raw_bluesky_posts table creation
- Story 4-4: stg_social_posts table creation
- TimescaleDB docs: https://docs.timescale.com/use-timescale/latest/hypertables/
