# Terraform Authentication Errors Runbook

## Overview
Authentication errors occur when Terraform cannot authenticate with a cloud provider or backend storage. Every provider requires valid credentials before any API call.

## Common Causes
- Expired or missing AWS/Azure/GCP credentials
- Wrong IAM role or insufficient permissions
- MFA token required but not provided
- Service principal / workload identity misconfigured
- Environment variables not set or overridden by conflicting config

## Diagnostic Steps

### Step 1: Verify credentials are present
```bash
# AWS
aws sts get-caller-identity
echo $AWS_ACCESS_KEY_ID | cut -c1-4   # First 4 chars only

# Azure
az account show
az ad signed-in-user show

# GCP
gcloud auth list
gcloud auth application-default print-access-token | cut -c1-10
```

### Step 2: Check provider config
```bash
grep -r "provider" *.tf providers.tf
cat ~/.aws/credentials   # Never log full file
```

### Step 3: Check Terraform environment variables
```bash
env | grep -E "^(AWS_|ARM_|GOOGLE_|TF_)" | sed 's/=.*/=***REDACTED***/'
```

### Step 4: Test specific permissions
```bash
# AWS — test the exact action Terraform needs
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<role> \
  --action-names ec2:DescribeInstances s3:GetObject \
  --resource-arns "*"
```

## Resolution

### Fix AWS Credentials
```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...   # For STS assumed roles

# Option 2: Assume a role
aws sts assume-role --role-arn arn:aws:iam::<account>:role/<role> \
  --role-session-name terraform-session
```

### Fix Azure Service Principal
```bash
export ARM_CLIENT_ID="..."
export ARM_CLIENT_SECRET="..."
export ARM_SUBSCRIPTION_ID="..."
export ARM_TENANT_ID="..."
```

### Fix GCP Application Default Credentials
```bash
gcloud auth application-default login
# Or for CI/CD:
export GOOGLE_CREDENTIALS=$(cat service-account.json)
```

### Fix Insufficient Permissions
```hcl
# Add required IAM permissions to the role/policy
# Example: Terraform needs these for EKS management
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["eks:*","ec2:*","iam:PassRole"],
    "Resource": "*"
  }]
}
```

## Rollback
- Credential fixes are non-destructive. No infrastructure changes occur during authentication.

## Related Issues
- `terraform-init-failures.md`
- `terraform-state-locks.md`
- `aws-iam-networking.md`
