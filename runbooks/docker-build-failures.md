# Docker Build and Startup Failures Runbook

## Overview
Docker build failures occur during `docker build`. Startup failures happen when the container exits immediately after `docker run`. Both prevent the container from serving traffic.

## Common Causes
- Missing base image or wrong tag
- Package install failure (network, repo outage, wrong package name)
- COPY / ADD references a file not in build context
- Application crashes on startup (missing env var, port conflict, missing dependency)
- Wrong CMD / ENTRYPOINT
- Insufficient disk space on Docker host
- Permission denied on mounted file or socket

## Diagnostic Steps

### Step 1: Inspect last container exit
```bash
docker ps -a --filter "status=exited" | head -10
docker inspect <container-id> --format '{{.State.ExitCode}} {{.State.Error}}'
```

### Step 2: Read container logs
```bash
docker logs <container-id> --tail=200
docker logs <container-id> 2>&1 | grep -iE "(error|fatal|exception|panic)"
```

### Step 3: Run interactively to debug startup
```bash
docker run -it --entrypoint /bin/sh <image>:<tag>
# Then manually run the CMD to see the error
```

### Step 4: Check disk space on host
```bash
df -h /var/lib/docker
docker system df
```

### Step 5: Check build context size
```bash
du -sh .
cat .dockerignore
```

### Step 6: Rebuild with no cache
```bash
docker build --no-cache --progress=plain -t <image>:<tag> . 2>&1 | tee build.log
```

### Step 7: Check resource usage
```bash
docker stats --no-stream
```

## Resolution

### Fix Missing Dependency in Build
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    <package> \
    && rm -rf /var/lib/apt/lists/*
```

### Fix COPY Failure (file not in context)
```bash
# Check .dockerignore isn't excluding the file
grep <filename> .dockerignore

# Or explicitly add COPY before it's needed
COPY ./scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
```

### Fix Startup Crash (missing env var)
```bash
docker run -e DB_HOST=localhost -e DB_PORT=5432 <image>:<tag>
# Or use env file:
docker run --env-file .env <image>:<tag>
```

### Fix OOM at Runtime
```bash
docker run -m 512m --memory-swap 512m <image>:<tag>
```

### Clean Up Disk Space
```bash
docker system prune -f           # Remove stopped containers, dangling images
docker volume prune -f           # Remove unused volumes
docker image prune -a -f         # Remove all unused images
# REQUIRES APPROVAL in shared environments
```

## Rollback
```bash
docker tag <image>:<previous-tag> <image>:stable
docker run <image>:stable
```

## Related Issues
- `kubernetes-imagepullbackoff.md`
- `linux-disk-memory-cpu.md`
- `ssl-tls-problems.md`  (if pulling from HTTPS registry fails)
