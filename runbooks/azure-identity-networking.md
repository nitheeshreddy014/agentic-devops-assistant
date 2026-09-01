# Azure Identity and Networking Runbook

## Overview
Azure identity (RBAC, service principals, managed identities) and networking (NSG, VNet peering, Private Endpoints) issues cause `AuthorizationFailed`, connectivity failures, and resource access errors.

## Common Causes
- Missing RBAC role assignment on the resource or resource group
- Service principal secret expired
- Managed identity not enabled or not assigned the right role
- NSG rule blocking traffic
- VNet peering not established or misconfigured
- Private Endpoint DNS not resolving correctly

## Diagnostic Steps

### Step 1: Check current identity
```bash
az account show
az ad signed-in-user show
az account get-access-token --query accessToken -o tsv | cut -c1-10
```

### Step 2: Check RBAC assignments
```bash
az role assignment list --assignee <object-id-or-upn> --output table
az role assignment list --scope /subscriptions/<sub>/resourceGroups/<rg> --output table
```

### Step 3: Check service principal
```bash
az ad sp show --id <app-id>
az ad sp credential list --id <app-id>   # Check expiry dates
```

### Step 4: Check NSG rules
```bash
az network nsg show -n <nsg-name> -g <rg> --query "securityRules" -o table
az network nsg list -g <rg> -o table
```

### Step 5: Check effective security rules on NIC
```bash
az network nic show-effective-nsg --name <nic-name> -g <rg>
```

### Step 6: Test VNet connectivity
```bash
az network watcher test-connectivity \
  --source-resource <vm-id> \
  --dest-address <target-ip> \
  --dest-port <port>
```

### Step 7: Check Private Endpoint DNS
```bash
az network private-endpoint show -n <pe-name> -g <rg>
az network private-dns zone list -g <rg> -o table
nslookup <storage-account>.blob.core.windows.net
```

## Resolution

### Fix Missing RBAC
```bash
az role assignment create \
  --assignee <object-id> \
  --role "Contributor" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>
# REQUIRES APPROVAL
```

### Fix Expired Service Principal Secret
```bash
az ad sp credential reset --id <app-id> \
  --years 1 --append
# Update the secret in Key Vault / CI/CD environment
# REQUIRES APPROVAL
```

### Fix NSG — Allow Traffic
```bash
az network nsg rule create \
  --nsg-name <nsg> -g <rg> \
  --name AllowHTTPS --priority 100 \
  --protocol Tcp --direction Inbound \
  --source-address-prefixes 10.0.0.0/8 \
  --destination-port-ranges 443 --access Allow
# REQUIRES APPROVAL
```

### Enable Managed Identity
```bash
az vm identity assign -n <vm> -g <rg>
az role assignment create \
  --assignee <system-assigned-identity-id> \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<account>
# REQUIRES APPROVAL
```

## Rollback
```bash
az role assignment delete --assignee <object-id> \
  --role "Contributor" --scope <scope>
az network nsg rule delete --nsg-name <nsg> -g <rg> --name AllowHTTPS
```

## Related Issues
- `terraform-auth-errors.md`
- `ssl-tls-problems.md`
- `dns-problems.md`
