# Kubernetes CrashLoopBackOff Runbook

## Overview
CrashLoopBackOff means a container repeatedly starts, crashes, and Kubernetes keeps restarting it with exponential back-off. The container is not healthy enough to stay running.

## Common Causes
- Application error or unhandled exception on startup
- Missing environment variables or secrets
- OOMKilled (container exceeds memory limit)
- Liveness probe misconfiguration killing healthy pods
- Missing dependency (database, API, config file)
- Wrong CMD/ENTRYPOINT in Dockerfile
- Permission denied on mounted volume or socket

## Diagnostic Steps

### Step 1: Check pod status
```bash
kubectl get pods -n <namespace> -o wide
kubectl get events -n <namespace> --sort-by=.lastTimestamp | tail -30
```
**Expected:** Pod status shows `CrashLoopBackOff`, events show restart count and reason.

### Step 2: Read current logs
```bash
kubectl logs <pod-name> -n <namespace> --tail=200
```
**Expected:** Application startup logs ending with the error that caused the crash.

### Step 3: Read previous container logs (most useful)
```bash
kubectl logs <pod-name> -n <namespace> --previous --tail=200
```
**Expected:** Last logs before the crash — look for exceptions, missing config, OOM messages.

### Step 4: Describe the pod
```bash
kubectl describe pod <pod-name> -n <namespace>
```
**Expected:** Check `Last State`, `Exit Code`, `OOMKilled`, `Events` section.
- Exit code 1 = application error
- Exit code 137 = OOMKilled (SIGKILL)
- Exit code 139 = segfault
- Exit code 143 = SIGTERM (graceful shutdown)

### Step 5: Check node resources
```bash
kubectl top nodes
kubectl top pods -n <namespace>
```
**Expected:** Memory/CPU usage. If memory is near limit → OOM issue.

### Step 6: Check resource limits
```bash
kubectl get deployment <name> -n <namespace> -o yaml | grep -A10 resources
```
**Expected:** See current CPU/memory requests and limits.

### Step 7: Check environment variables and secrets
```bash
kubectl describe pod <pod-name> -n <namespace> | grep -A30 "Environment:"
kubectl get secret -n <namespace>
```
**Expected:** Verify all required env vars are present and secrets exist.

## Resolution

### Fix OOMKilled (Exit 137)
```yaml
# Increase memory limits in deployment spec
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```
```bash
kubectl apply -f deployment.yaml
# OR patch directly (requires approval in production):
kubectl patch deployment <name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"memory":"512Mi"}}}]}}}}'
```

### Fix Missing Config / Env Vars
```bash
kubectl create secret generic <secret-name> \
  --from-literal=DB_PASSWORD=<value> -n <namespace>
# Then reference in deployment:
# envFrom:
#   - secretRef:
#       name: <secret-name>
```

### Fix Liveness Probe Too Aggressive
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30   # Give app time to start
  periodSeconds: 10
  failureThreshold: 3
```

### Fix Permission Issues
```bash
# Check what user the container runs as
kubectl exec <pod-name> -n <namespace> -- id
# Fix volume ownership via initContainer or fsGroup
```

## Rollback
```bash
kubectl rollout undo deployment/<name> -n <namespace>
kubectl rollout status deployment/<name> -n <namespace>
```

## Related Issues
- `kubernetes-imagepullbackoff.md` — if image cannot be pulled
- `kubernetes-pending-pods.md` — if pod never starts
- `linux-disk-memory-cpu.md` — for node-level resource exhaustion
