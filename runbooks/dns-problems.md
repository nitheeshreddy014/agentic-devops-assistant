# DNS Problems Runbook

## Overview
DNS failures prevent services from resolving hostnames, causing connection errors that appear as timeouts or "host not found" errors at every layer of the stack.

## Common Causes
- Missing or wrong DNS record (A, CNAME, MX, TXT)
- TTL too long — stale record after DNS change
- VPC DNS resolution disabled
- Split-horizon DNS returning wrong IP inside vs outside VPC
- DNS server unreachable (firewall, security group)
- DNSSEC validation failure
- Search domain misconfiguration on hosts

## Diagnostic Steps

### Step 1: Basic DNS lookup
```bash
dig <hostname> +short
dig <hostname> A
nslookup <hostname>
```
**Expected:** Returns one or more IP addresses. NXDOMAIN = record does not exist.

### Step 2: Query specific DNS servers
```bash
dig @8.8.8.8 <hostname> +short     # Google Public DNS
dig @1.1.1.1 <hostname> +short     # Cloudflare
dig @169.254.169.253 <hostname>    # AWS VPC DNS (inside VPC only)
```
**Expected:** Identify if the issue is DNS propagation or a specific resolver.

### Step 3: Check TTL and record age
```bash
dig <hostname> +ttlid
# Look for TTL value — high TTL = slow propagation
```

### Step 4: Check authoritative nameservers
```bash
dig <hostname> NS +short
dig @<authoritative-ns> <hostname>
```

### Step 5: Verify DNS record at registrar / DNS provider
```bash
# AWS Route 53
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --query "ResourceRecordSets[?Name=='<hostname>.']"

# Check if hosted zone is public or private
aws route53 get-hosted-zone --id <zone-id> | grep -i private
```

### Step 6: Check host resolver config
```bash
cat /etc/resolv.conf
cat /etc/hosts
systemd-resolve --status | grep DNS
```

### Step 7: Trace DNS resolution path
```bash
dig <hostname> +trace
```

## Resolution

### Fix Missing DNS Record (AWS Route 53)
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "<hostname>",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<ip>"}]
      }
    }]
  }'
# REQUIRES APPROVAL
```

### Fix Stale TTL Cache
```bash
# Flush local DNS cache
sudo systemd-resolve --flush-caches
sudo dscacheutil -flushcache  # macOS

# Reduce TTL proactively before making changes
# Set TTL to 60s, wait for old TTL to expire, then change, then restore TTL
```

### Fix VPC DNS Resolution (AWS)
```bash
aws ec2 modify-vpc-attribute \
  --vpc-id <vpc-id> \
  --enable-dns-support '{"Value": true}'
aws ec2 modify-vpc-attribute \
  --vpc-id <vpc-id> \
  --enable-dns-hostnames '{"Value": true}'
# REQUIRES APPROVAL
```

## Rollback
```bash
# Revert DNS record change
aws route53 change-resource-record-sets --hosted-zone-id <zone-id> \
  --change-batch '{"Changes": [{"Action": "DELETE", ...}]}'
```

## Related Issues
- `api-timeouts.md` — DNS failures look like timeouts
- `ssl-tls-problems.md` — certificate hostname must match DNS
- `aws-iam-networking.md`
