# API Timeouts Runbook

## Overview
API timeouts occur when a client cannot get a response within the configured timeout window. They can originate at the client, load balancer, or server side.

## Common Causes
- Slow database query blocking the request thread
- Downstream service dependency timing out (cascade)
- Connection pool exhausted — requests queue and expire
- CPU-bound processing blocking the event loop
- Memory pressure causing GC pauses
- Network packet loss between client and server
- Too-short client-side timeout misconfiguration

## Diagnostic Steps

### Step 1: Measure response time
```bash
curl -s -w "\nTotal: %{time_total}s\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\n" \
  -o /dev/null https://<host>/api/endpoint
```

### Step 2: Check error rate and latency in logs
```bash
# Nginx
grep " 504 " /var/log/nginx/access.log | tail -20
awk '{print $7, $10}' /var/log/nginx/access.log | sort -k2 -rn | head -20

# AWS ALB — check target response time
aws logs filter-log-events \
  --log-group-name <alb-log-group> \
  --filter-pattern '"target_processing_time" >"1"' | head -20
```

### Step 3: Check server resource usage
```bash
top -bn1 | head -20
free -m
ss -s   # Socket statistics — check TIME_WAIT accumulation
```

### Step 4: Check database slow queries
```sql
-- PostgreSQL
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;

-- MySQL
SHOW FULL PROCESSLIST;
SELECT * FROM information_schema.PROCESSLIST WHERE TIME > 5;
```

### Step 5: Check connection pool
```bash
# For PostgreSQL — active connections
psql -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# For application pool (e.g. Django, Rails)
grep -i "pool" /app/config/*.yaml
```

### Step 6: Check downstream services
```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}" https://<downstream-service>/health
```

## Resolution

### Fix Slow DB Query
```sql
-- Add index for the slow query
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
-- EXPLAIN ANALYZE to verify
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;
```

### Fix Connection Pool Exhaustion
```python
# Django settings
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'pool_size': 20, 'max_overflow': 30},
    }
}
```

### Fix Client Timeout Too Short
```python
# Python requests
response = requests.get(url, timeout=(3.05, 30))  # (connect, read)
```

### Fix ALB Idle Timeout
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <arn> \
  --attributes Key=idle_timeout.timeout_seconds,Value=120
# REQUIRES APPROVAL
```

## Rollback
- Timeout value changes are reversible — restore previous timeout value.
- Index creation with `CONCURRENTLY` is non-blocking and can be dropped if it causes issues.

## Related Issues
- `database-connectivity.md`
- `dns-problems.md`
- `linux-disk-memory-cpu.md`
