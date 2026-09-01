# SSL/TLS Problems Runbook

## Overview
SSL/TLS failures cause HTTPS connections to fail with certificate errors. They affect web services, APIs, database connections, and internal microservice communication.

## Common Causes
- Certificate expired
- Certificate hostname mismatch (CN/SAN doesn't match domain)
- Incomplete certificate chain (missing intermediate)
- Self-signed certificate not trusted by client
- TLS version mismatch (client requires TLS 1.2+, server only offers 1.0)
- Certificate private key mismatch
- Let's Encrypt renewal failure (certbot cron not running)

## Diagnostic Steps

### Step 1: Check certificate expiry
```bash
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null \
  | openssl x509 -noout -dates -subject -issuer
```
**Expected:** `notAfter` should be in the future.

### Step 2: Check full certificate chain
```bash
openssl s_client -connect <host>:443 -showcerts 2>/dev/null | grep -E "(subject|issuer|Verify)"
```
**Expected:** Chain ends with a trusted root CA. `Verify return code: 0 (ok)`

### Step 3: Check certificate hostname
```bash
openssl s_client -connect <host>:443 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName
```
**Expected:** SAN includes the hostname being accessed.

### Step 4: Test from curl (simulates browser)
```bash
curl -v https://<host>/health 2>&1 | grep -E "(SSL|TLS|certificate|error|OK)"
curl -k https://<host>/health  # Ignore cert errors (diagnostic only)
```

### Step 5: Check TLS version support
```bash
nmap --script ssl-enum-ciphers -p 443 <host>
openssl s_client -connect <host>:443 -tls1_2 2>&1 | grep "Protocol"
openssl s_client -connect <host>:443 -tls1_3 2>&1 | grep "Protocol"
```

### Step 6: Check Let's Encrypt certificate renewal
```bash
certbot certificates
certbot renew --dry-run
systemctl status certbot.timer
journalctl -u certbot --since "7 days ago" | tail -50
```

### Step 7: Check certificate in Kubernetes secret
```bash
kubectl get secret <tls-secret> -n <namespace> -o yaml | \
  grep tls.crt | awk '{print $2}' | base64 -d | \
  openssl x509 -noout -dates -subject
```

## Resolution

### Renew Let's Encrypt Certificate
```bash
certbot renew --force-renewal
systemctl reload nginx   # or apache2
# REQUIRES APPROVAL in production
```

### Fix Incomplete Chain (Nginx)
```nginx
ssl_certificate /etc/letsencrypt/live/<domain>/fullchain.pem;  # Not cert.pem
ssl_certificate_key /etc/letsencrypt/live/<domain>/privkey.pem;
```

### Fix Kubernetes TLS Secret
```bash
kubectl create secret tls <secret-name> \
  --cert=fullchain.pem \
  --key=privkey.pem \
  -n <namespace> \
  --dry-run=client -o yaml | kubectl apply -f -
# REQUIRES APPROVAL
```

### Fix AWS ACM Certificate
```bash
# Request new certificate
aws acm request-certificate \
  --domain-name <domain> \
  --validation-method DNS \
  --subject-alternative-names "www.<domain>"
# Then add CNAME validation records to DNS
# REQUIRES APPROVAL
```

### Configure TLS Minimum Version (Nginx)
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
```

## Rollback
- Certificate rollback: restore previous certificate from backup or re-issue.
- Config rollback: `git revert` Nginx/Apache config and `systemctl reload`.

## Related Issues
- `dns-problems.md` — DNS must resolve before TLS handshake
- `database-connectivity.md` — DB SSL cert issues
- `kubernetes-crashloopbackoff.md` — cert mount failures
