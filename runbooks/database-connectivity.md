# Database Connectivity Runbook

## Overview
Database connectivity failures prevent applications from reading or writing data. They can be caused by configuration errors, network issues, resource exhaustion, or authentication failures.

## Common Causes
- Wrong host, port, database name, or credentials in connection string
- Connection pool exhausted — too many concurrent connections
- Database server overloaded or crashed
- Network/firewall blocking the database port (5432, 3306, 27017)
- SSL/TLS required but client not configured for it
- Too many idle connections consuming pg_max_connections

## Diagnostic Steps

### Step 1: Test raw TCP connectivity
```bash
nc -zv <db-host> <port>   # e.g. port 5432 for PostgreSQL
telnet <db-host> <port>
```

### Step 2: Check DNS resolution for DB host
```bash
dig <db-host> +short
nslookup <db-host>
```

### Step 3: Check active connections (PostgreSQL)
```sql
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;
```

### Step 4: Check max connections setting
```sql
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;
```

### Step 5: Check for long-running queries / locks
```sql
SELECT pid, now() - pg_stat_activity.query_start AS duration,
       query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
  AND state != 'idle'
ORDER BY duration DESC;
```

### Step 6: Check application connection pool config
```bash
grep -rE "(POOL_SIZE|MAX_CONNECTIONS|DATABASE_URL)" /app/config/ .env
```

### Step 7: Check database logs
```bash
# PostgreSQL
tail -100 /var/log/postgresql/postgresql-*.log
journalctl -u postgresql --since "1 hour ago" | tail -100

# MySQL
tail -100 /var/log/mysql/error.log
```

## Resolution

### Fix Connection Pool Exhaustion
```python
# Django
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 0,   # Use connection pooler (PgBouncer) instead
    }
}
```

### Use PgBouncer (connection pooler)
```ini
# pgbouncer.ini
[databases]
mydb = host=localhost port=5432 dbname=mydb

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
```

### Kill Idle Connections
```sql
-- Terminate idle connections older than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < now() - interval '10 minutes'
  AND pid != pg_backend_pid();
-- REQUIRES APPROVAL
```

### Fix Authentication
```bash
# Test authentication explicitly
psql "postgresql://<user>:<password>@<host>:<port>/<dbname>?sslmode=require"
```

### Fix Firewall (AWS RDS)
```bash
aws ec2 authorize-security-group-ingress \
  --group-id <rds-sg-id> \
  --protocol tcp --port 5432 \
  --source-group <app-sg-id>
# REQUIRES APPROVAL
```

## Rollback
- Connection pool config changes: revert to previous settings and restart application.
- Security group changes: revoke the added rule.

## Related Issues
- `ssl-tls-problems.md` — DB SSL certificate issues
- `dns-problems.md` — DB host resolution failure
- `linux-disk-memory-cpu.md` — DB disk full (WAL overflow)
