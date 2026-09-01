# Kubernetes ImagePullBackOff / ErrImagePull Runbook

## Overview
`ImagePullBackOff` and `ErrImagePull` mean Kubernetes cannot pull the container image from the registry. The pod stays in this state until the image becomes available.

## Common Causes
- Image name or tag is wrong / does not exist
- Registry is private and imagePullSecret is missing or incorrect
- Registry is unreachable (network, firewall, DNS)
- Image was deleted from the registry
- Using `:latest` in a registry that does not have a `latest` tag
- Docker Hub rate limiting (anonymous pulls limited to 100/6h)
- Wrong registry URL (e.g. `docker.io` vs `ghcr.io` vs private ECR/ACR/GCR)

## Diagnostic Steps

### Step 1: Check pod events
```bash
kubectl describe pod <pod-name> -n <namespace> | tail -30
```
**Expected:** `Failed to pull image "registry/image:tag": ...` with specific error.

### Step 2: Verify the image exists
```bash
# Docker Hub
docker manifest inspect <image>:<tag>

# AWS ECR
aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>

# Google GCR
gcloud container images list-tags gcr.io/<project>/<image>

# GitHub GHCR
curl -H "Authorization: Bearer <token>" \
  https://ghcr.io/v2/<owner>/<image>/tags/list
```

### Step 3: Check imagePullSecrets
```bash
kubectl get pod <pod-name> -n <namespace> -o yaml | grep -A5 imagePullSecrets
kubectl get secret -n <namespace> | grep registry
kubectl describe secret <pull-secret-name> -n <namespace>
```

### Step 4: Test registry authentication
```bash
# Create a temporary pod to test pull
kubectl run test-pull --image=<registry/image:tag> --restart=Never -n <namespace>
kubectl describe pod test-pull -n <namespace>
kubectl delete pod test-pull -n <namespace>
```

### Step 5: Check node's Docker credentials
```bash
# On the node (read-only check)
cat /var/lib/kubelet/config.json | python3 -m json.tool
```

### Step 6: Check Docker Hub rate limit
```bash
# Check remaining pulls (anonymous)
curl -s https://hub.docker.com/v2/ratelimitpreview/test | head -5
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s --head -H "Authorization: Bearer $TOKEN" https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest | grep -i ratelimit
```

## Resolution

### Fix Wrong Image Name or Tag
```bash
# Update deployment image
kubectl set image deployment/<name> <container>=<correct-image>:<correct-tag> -n <namespace>
# REQUIRES APPROVAL in production
```

### Fix Missing imagePullSecret (Docker Hub)
```bash
kubectl create secret docker-registry regcred \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n <namespace>
```
Then add to deployment spec:
```yaml
spec:
  imagePullSecrets:
    - name: regcred
```

### Fix AWS ECR Authentication
```bash
# Create ECR pull secret
aws ecr get-login-password --region <region> | \
  kubectl create secret docker-registry ecr-secret \
  --docker-server=<account>.dkr.ecr.<region>.amazonaws.com \
  --docker-username=AWS \
  --docker-password-stdin \
  -n <namespace>
```

### Fix Docker Hub Rate Limiting
- Authenticate with Docker Hub credentials (500 pulls/6h for free, unlimited for paid)
- Use a private mirror or caching proxy
- Switch to a less rate-limited registry (GHCR, ECR, GCR)

## Rollback
```bash
kubectl rollout undo deployment/<name> -n <namespace>
```

## Related Issues
- `kubernetes-crashloopbackoff.md` — image pulled but container crashes
- `kubernetes-pending-pods.md` — pod never scheduled
