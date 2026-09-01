# AWS IAM and Networking Runbook

## Overview
AWS IAM and networking issues cause `AccessDenied` errors, connectivity failures between services, and resources that appear running but cannot communicate.

## Common Causes
- IAM policy missing required action or resource ARN
- Security group missing inbound/outbound rule
- Route table missing route to internet gateway or NAT
- VPC endpoint missing for private subnet access to AWS services
- NACLs (stateless) blocking return traffic
- Private subnet instances missing NAT Gateway for outbound internet

## Diagnostic Steps

### Step 1: Verify IAM identity
```bash
aws sts get-caller-identity
aws iam list-attached-user-policies --user-name <user>
aws iam list-attached-role-policies --role-name <role>
```

### Step 2: Simulate IAM policy
```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<account>:role/<role> \
  --action-names <action> \
  --resource-arns <resource-arn>
```
**Expected:** `allowed` or `implicitDeny`/`explicitDeny` with the blocking policy.

### Step 3: Check security groups
```bash
aws ec2 describe-security-groups \
  --filters "Name=group-id,Values=<sg-id>" \
  --query "SecurityGroups[0].IpPermissions"
```

### Step 4: Check route tables
```bash
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=<subnet-id>"
```

### Step 5: Check NACLs
```bash
aws ec2 describe-network-acls \
  --filters "Name=association.subnet-id,Values=<subnet-id>"
```

### Step 6: Test connectivity from inside VPC
```bash
# From EC2 instance in the same VPC
curl -v --connect-timeout 5 http://<target-ip>:<port>
telnet <target-ip> <port>
```

### Step 7: Check VPC Flow Logs
```bash
aws logs filter-log-events \
  --log-group-name <vpc-flow-log-group> \
  --filter-pattern "REJECT" \
  --start-time $(date -d '-1 hour' +%s000)
```

## Resolution

### Fix Missing IAM Permission
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject","s3:PutObject"],
    "Resource": "arn:aws:s3:::<bucket>/*"
  }]
}
```
```bash
aws iam put-role-policy --role-name <role> \
  --policy-name <name> --policy-document file://policy.json
# REQUIRES APPROVAL
```

### Fix Security Group — Add Inbound Rule
```bash
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp --port 443 \
  --cidr 10.0.0.0/8
# REQUIRES APPROVAL
```

### Fix Route Table — Add NAT Route
```bash
aws ec2 create-route \
  --route-table-id <rtb-id> \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id <nat-id>
# REQUIRES APPROVAL
```

## Rollback
```bash
# Revert security group rule
aws ec2 revoke-security-group-ingress --group-id <sg-id> \
  --protocol tcp --port 443 --cidr 10.0.0.0/8

# Remove route
aws ec2 delete-route --route-table-id <rtb-id> \
  --destination-cidr-block 0.0.0.0/0
```

## Related Issues
- `terraform-auth-errors.md`
- `dns-problems.md`
- `api-timeouts.md`
