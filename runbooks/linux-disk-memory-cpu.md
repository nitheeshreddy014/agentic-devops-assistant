# Linux Disk, Memory and CPU Runbook

## Overview
Resource exhaustion on Linux hosts causes cascading failures: full disks prevent writes, OOM kills processes, and CPU saturation degrades all services.

## Common Causes — Disk
- Log rotation not configured — logs fill /var/log
- Container layers accumulating in /var/lib/docker
- Core dumps written to disk
- Inode exhaustion (many small files, no disk-space issue shown by df)
- Incomplete package downloads filling /tmp or /var/cache

## Common Causes — Memory
- Memory leak in application
- JVM heap set too high
- Too many processes forked (fork bomb or misconfigured worker count)
- Kernel slab cache growth

## Common Causes — CPU
- Runaway process (infinite loop, deadlock spinning)
- High I/O wait caused by slow disk
- Crypto mining malware
- Misconfigured cron job running continuously

## Diagnostic Steps — Disk

### Step 1: Check disk usage
```bash
df -h
df -h --output=source,fstype,size,used,avail,pcent,target | grep -v tmpfs
```

### Step 2: Find large directories
```bash
du -sh /* 2>/dev/null | sort -rh | head -20
du -sh /var/* | sort -rh | head -10
du -sh /home/* | sort -rh | head -10
```

### Step 3: Find large files
```bash
find / -xdev -type f -size +100M 2>/dev/null | xargs ls -lh | sort -k5 -rh | head -20
```

### Step 4: Check inode usage
```bash
df -i
# High inode usage with low block usage = many tiny files
find / -xdev -printf '%h\n' 2>/dev/null | sort | uniq -c | sort -rn | head -10
```

## Diagnostic Steps — Memory

### Step 5: Check memory usage
```bash
free -m
cat /proc/meminfo | grep -E "(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree)"
```

### Step 6: Find memory-heavy processes
```bash
ps aux --sort=-%mem | head -20
# Or use smem for accurate RSS
smem -r -s rss | head -20
```

### Step 7: Check OOM events
```bash
dmesg | grep -i "killed process"
journalctl -k | grep -i "out of memory" | tail -20
```

## Diagnostic Steps — CPU

### Step 8: Check CPU usage
```bash
top -bn1 | head -25
mpstat 1 5  # Per-CPU stats
```

### Step 9: Find CPU-heavy processes
```bash
ps aux --sort=-%cpu | head -20
```

### Step 10: Check I/O wait
```bash
iostat -x 1 5
iotop -a -o    # Shows only processes with active I/O
```

## Resolution

### Free Disk — Log Cleanup
```bash
# Truncate (not delete) log files safely
> /var/log/syslog          # Truncate without breaking file handle
journalctl --vacuum-size=500M
journalctl --vacuum-time=7d
docker system prune -f     # Clean Docker — REQUIRES APPROVAL on shared hosts
```

### Free Disk — Find and Remove Core Dumps
```bash
find / -name "core.*" -type f 2>/dev/null | head -20
find / -name "core" -type f 2>/dev/null | head -20
# Remove after confirming:
# rm /path/to/core  — REQUIRES APPROVAL
```

### Fix Memory Leak — Restart Process
```bash
# Graceful restart
systemctl restart <service>   # REQUIRES APPROVAL in production

# If process is unresponsive:
kill -TERM <pid>  # Give it 30s to shut down gracefully
# Then: kill -KILL <pid> — LAST RESORT, REQUIRES APPROVAL
```

### Fix High CPU — Identify and Throttle
```bash
# Nice the process to reduce priority (non-destructive)
renice +10 -p <pid>

# Set CPU limit with cgroups
systemd-run --scope -p CPUQuota=50% --pid <pid> sleep inf
```

## Rollback
- Disk cleanup is permanent — verify before deleting.
- Process restart rollback: use `systemctl rollback` or redeploy previous version.

## Related Issues
- `kubernetes-crashloopbackoff.md` — OOMKilled pods
- `database-connectivity.md` — disk-full affects WAL/logs
- `docker-build-failures.md` — disk-full stops builds
