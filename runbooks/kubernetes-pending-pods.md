# Kubernetes Pending Pods Runbook

## Overview
A pod stays in `Pending` state when the Kubernetes scheduler cannot find a suitable node to place it on.

## Common Causes
- Insufficient CPU or memory on all available nodes
- Node selector / affinity rules that no node satisfies
- Taints on nodes without matching tolerations
- PersistentVolumeClaim (PVC) not bound
- Resource quota exceeded in the namespace
- No nodes available at all (cluster scaled to zero)

## Diagnostic Steps

### Step 1: Describe the pending pod
```bash
kubectl describe pod <pod-name> -n <namespace> | grep -A20 "Events:"
```
**Expected:** Scheduler messages like `0/3 nodes are available: 3 Insufficient memory`.

### Step 2: Check node capacity
```bash
kubectl top nodes
kubectl describe nodes | grep -A10 "Allocated resources"
```

### Step 3: Check resource requests vs available
```bash
kubectl get pods -n <namespace> -o json | python3 -c "
import sys, json
pods = json.load(sys.stdin)['items']
for p in pods:
  for c in p['spec'].get('containers', []):
    req = c.get('resources', {}).get('requests', {})
    print(p['metadata']['name'], req)
"
```

### Step 4: Check node taints
```bash
kubectl get nodes -o json | python3 -c "
import sys, json
nodes = json.load(sys.stdin)['items']
for n in nodes:
  taints = n['spec'].get('taints', [])
  if taints: print(n['metadata']['name'], taints)
"
```

### Step 5: Check namespace resource quota
```bash
kubectl describe quota -n <namespace>
kubectl describe limitrange -n <namespace>
```

### Step 6: Check PVC status
```bash
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc-name> -n <namespace>
```

## Resolution

### Fix Insufficient Resources — Scale Up Nodes
```bash
# AWS EKS — increase node group
aws eks update-nodegroup-config \
  --cluster-name <cluster> \
  --nodegroup-name <nodegroup> \
  --scaling-config desiredSize=<n> \
  # REQUIRES APPROVAL

# GKE — resize node pool
gcloud container clusters resize <cluster> \
  --node-pool <pool> --num-nodes <n>
  # REQUIRES APPROVAL
```

### Fix Taint/Toleration Mismatch
```yaml
# Add toleration to pod spec
tolerations:
  - key: "node-role.kubernetes.io/infra"
    operator: "Exists"
    effect: "NoSchedule"
```

### Fix PVC Not Bound
```bash
kubectl get storageclass   # Check default StorageClass exists
kubectl describe pvc <name> -n <namespace>
# If no StorageClass: create one or set a default
kubectl patch storageclass <name> -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### Fix Resource Quota Exceeded
```bash
kubectl edit quota <quota-name> -n <namespace>
# Increase limits — REQUIRES APPROVAL
```

## Rollback
```bash
# Revert node count change
kubectl rollout undo deployment/<name> -n <namespace>
```

## Related Issues
- `kubernetes-crashloopbackoff.md` — pod starts but crashes
- `linux-disk-memory-cpu.md` — node resource exhaustion
