# Terraform Init Failures Runbook

## Overview
`terraform init` initialises the working directory: downloads providers, configures backend, and installs modules. Failures here prevent any further Terraform operations.

## Common Causes
- Backend bucket / storage account does not exist or is inaccessible
- Credentials missing or expired (S3, GCS, Azure Blob, Consul)
- Wrong provider source or version constraint
- Network connectivity to Terraform registry or backend
- Corrupted `.terraform` directory or lock file
- Module source URL is unreachable or private

## Diagnostic Steps

### Step 1: Run init with detailed output
```bash
terraform init -upgrade 2>&1 | head -60
```
**Expected:** Identifies the exact step that failed.

### Step 2: Check backend config
```bash
cat backend.tf   # or the -backend-config files
terraform init -backend=false  # skip backend to test provider download only
```

### Step 3: Verify credentials
```bash
# AWS
aws sts get-caller-identity
aws s3 ls s3://<state-bucket>/

# Azure
az account show
az storage account show --name <storage_account>

# GCP
gcloud auth application-default print-access-token
gsutil ls gs://<state-bucket>/
```

### Step 4: Check provider registry reachability
```bash
curl -s https://registry.terraform.io/v1/providers/hashicorp/aws/versions | head -5
```

### Step 5: Inspect lock file
```bash
cat .terraform.lock.hcl
```
**Expected:** Provider hashes should match the platform.

### Step 6: Check module sources
```bash
grep -r "source" modules/ *.tf | grep -v "^Binary"
```

## Resolution

### Fix Backend Access
```bash
# Create missing S3 bucket
aws s3 mb s3://<bucket-name> --region <region>
aws s3api put-bucket-versioning --bucket <bucket-name> \
  --versioning-configuration Status=Enabled

# Create DynamoDB lock table
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### Fix Provider Version Conflict
```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"   # Use compatible version range
    }
  }
}
```
```bash
terraform init -upgrade   # re-download providers
```

### Fix Corrupted .terraform
```bash
rm -rf .terraform .terraform.lock.hcl
terraform init
```

## Rollback
- `terraform init` is non-destructive and idempotent — re-run freely.
- No infrastructure changes are made by `init`.

## Related Issues
- `terraform-state-locks.md` — state locking problems
- `terraform-auth-errors.md` — authentication failures
