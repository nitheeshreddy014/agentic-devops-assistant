# Terraform State Locks Runbook

## Overview
Terraform locks the state file before every `plan` and `apply` to prevent concurrent modifications. A stale lock blocks all operations until it is released.

## Common Causes
- A previous `terraform apply` was killed (Ctrl+C, CI timeout, crash)
- Two CI/CD pipelines ran `apply` simultaneously
- Network failure during apply left lock in DynamoDB / storage
- Developer forgot to run `terraform unlock`

## Diagnostic Steps

### Step 1: Identify the lock
```bash
terraform plan 2>&1 | grep -A10 "Error acquiring the state lock"
```
**Expected:** Shows Lock ID, Who, Created timestamp, Path.

### Step 2: Check DynamoDB lock table (AWS S3 backend)
```bash
aws dynamodb scan --table-name <lock-table> \
  --filter-expression "attribute_exists(LockID)" \
  --output table
```

### Step 3: Verify no active apply is running
```bash
# In CI/CD — check running pipelines in GitHub Actions / Jenkins / GitLab
# On local machines:
ps aux | grep terraform
# Check Terraform Cloud / Enterprise for active runs
```

### Step 4: Check who holds the lock
```bash
# The lock info shows: Operation, Who (hostname/user), Created
terraform plan 2>&1 | grep -E "(Who|Created|Operation|Info)"
```

## Resolution

### Force-unlock (ONLY after confirming no active apply)
```bash
terraform force-unlock <LOCK_ID>
# REQUIRES APPROVAL — confirm no apply is running first
```

### Remove stale DynamoDB lock manually
```bash
aws dynamodb delete-item \
  --table-name <lock-table> \
  --key '{"LockID": {"S": "<path/to/state.tfstate-md5>"}}'
# REQUIRES APPROVAL
```

### Prevent Concurrent Runs in CI/CD
```yaml
# GitHub Actions — serialise runs with concurrency
concurrency:
  group: terraform-${{ github.ref }}
  cancel-in-progress: false   # Never cancel — wait instead
```

## Rollback
- Force-unlock is reversible — the state itself is not modified.
- If an apply was partially applied, check state with `terraform state list` and `terraform plan` to assess drift.

## Related Issues
- `terraform-init-failures.md` — init failures before locking
- `terraform-auth-errors.md` — credential errors during apply
