"""MCP-compatible tool: diagnostic checklists per issue category."""
from __future__ import annotations
from typing import Any, Dict, List

_CHECKLISTS: Dict[str, List[Dict[str, Any]]] = {
    "kubernetes": [
        {"step": 1, "purpose": "Check pod status", "command": "kubectl get pods -n <namespace> -o wide", "risk": "low"},
        {"step": 2, "purpose": "Describe failing pod", "command": "kubectl describe pod <pod-name> -n <namespace>", "risk": "low"},
        {"step": 3, "purpose": "Read current logs", "command": "kubectl logs <pod-name> -n <namespace> --tail=100", "risk": "low"},
        {"step": 4, "purpose": "Read previous container logs", "command": "kubectl logs <pod-name> -n <namespace> --previous --tail=100", "risk": "low"},
        {"step": 5, "purpose": "Check node resource availability", "command": "kubectl top nodes", "risk": "low"},
        {"step": 6, "purpose": "Check pod resource usage", "command": "kubectl top pods -n <namespace>", "risk": "low"},
        {"step": 7, "purpose": "Check events in namespace", "command": "kubectl get events -n <namespace> --sort-by=.lastTimestamp", "risk": "low"},
        {"step": 8, "purpose": "Inspect deployment", "command": "kubectl describe deployment <name> -n <namespace>", "risk": "low"},
        {"step": 9, "purpose": "Check ConfigMaps", "command": "kubectl get configmap -n <namespace>", "risk": "low"},
        {"step": 10, "purpose": "Check Secrets (names only)", "command": "kubectl get secrets -n <namespace>", "risk": "low"},
    ],
    "terraform": [
        {"step": 1, "purpose": "Validate configuration", "command": "terraform validate", "risk": "low"},
        {"step": 2, "purpose": "Show plan", "command": "terraform plan -out=tfplan", "risk": "low"},
        {"step": 3, "purpose": "Show current state", "command": "terraform state list", "risk": "low"},
        {"step": 4, "purpose": "Show specific resource state", "command": "terraform state show <resource>", "risk": "low"},
        {"step": 5, "purpose": "Check backend config", "command": "terraform init -backend=false 2>&1 | head -30", "risk": "low"},
        {"step": 6, "purpose": "Show lock info", "command": "terraform force-unlock -help", "risk": "low"},
        {"step": 7, "purpose": "Verify credentials", "command": "aws sts get-caller-identity", "risk": "low"},
        {"step": 8, "purpose": "Check provider versions", "command": "terraform version", "risk": "low"},
    ],
    "docker": [
        {"step": 1, "purpose": "List running containers", "command": "docker ps -a", "risk": "low"},
        {"step": 2, "purpose": "View container logs", "command": "docker logs <container-id> --tail=100", "risk": "low"},
        {"step": 3, "purpose": "Inspect container config", "command": "docker inspect <container-id>", "risk": "low"},
        {"step": 4, "purpose": "Check resource usage", "command": "docker stats --no-stream", "risk": "low"},
        {"step": 5, "purpose": "Check image layers", "command": "docker history <image>", "risk": "low"},
        {"step": 6, "purpose": "Check Docker info", "command": "docker info", "risk": "low"},
        {"step": 7, "purpose": "Check networks", "command": "docker network ls", "risk": "low"},
        {"step": 8, "purpose": "Check volumes", "command": "docker volume ls", "risk": "low"},
    ],
    "aws": [
        {"step": 1, "purpose": "Verify identity", "command": "aws sts get-caller-identity", "risk": "low"},
        {"step": 2, "purpose": "Check IAM policies for user/role", "command": "aws iam get-user && aws iam list-attached-user-policies --user-name <name>", "risk": "low"},
        {"step": 3, "purpose": "List EC2 instances", "command": "aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,State.Name,PublicIpAddress]' --output table", "risk": "low"},
        {"step": 4, "purpose": "Check CloudWatch logs", "command": "aws logs tail <log-group> --since 1h", "risk": "low"},
        {"step": 5, "purpose": "Check security groups", "command": "aws ec2 describe-security-groups --query 'SecurityGroups[?GroupName==`<name>`]'", "risk": "low"},
        {"step": 6, "purpose": "Check VPC configuration", "command": "aws ec2 describe-vpcs", "risk": "low"},
        {"step": 7, "purpose": "Check ELB health", "command": "aws elbv2 describe-target-health --target-group-arn <arn>", "risk": "low"},
    ],
    "azure": [
        {"step": 1, "purpose": "Check identity", "command": "az account show", "risk": "low"},
        {"step": 2, "purpose": "List resource groups", "command": "az group list -o table", "risk": "low"},
        {"step": 3, "purpose": "Check VM status", "command": "az vm list -d -o table", "risk": "low"},
        {"step": 4, "purpose": "View activity log", "command": "az monitor activity-log list --max-events 20", "risk": "low"},
        {"step": 5, "purpose": "Check AKS cluster", "command": "az aks show -n <cluster> -g <rg> --query 'provisioningState'", "risk": "low"},
    ],
    "database": [
        {"step": 1, "purpose": "Check active connections", "command": "SELECT count(*) FROM pg_stat_activity;  -- PostgreSQL", "risk": "low"},
        {"step": 2, "purpose": "Check connection limits", "command": "SHOW max_connections;  -- PostgreSQL", "risk": "low"},
        {"step": 3, "purpose": "Check slow queries", "command": "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;", "risk": "low"},
        {"step": 4, "purpose": "Check locks", "command": "SELECT * FROM pg_locks WHERE NOT granted;", "risk": "low"},
        {"step": 5, "purpose": "Check disk usage", "command": "SELECT pg_database_size(current_database());", "risk": "low"},
        {"step": 6, "purpose": "Check replication lag", "command": "SELECT * FROM pg_stat_replication;", "risk": "low"},
    ],
    "networking": [
        {"step": 1, "purpose": "Test connectivity", "command": "ping -c 4 <host>", "risk": "low"},
        {"step": 2, "purpose": "Trace route", "command": "traceroute <host>", "risk": "low"},
        {"step": 3, "purpose": "DNS lookup", "command": "dig <hostname> +short", "risk": "low"},
        {"step": 4, "purpose": "Check DNS from multiple resolvers", "command": "dig @8.8.8.8 <hostname> && dig @1.1.1.1 <hostname>", "risk": "low"},
        {"step": 5, "purpose": "Check port reachability", "command": "nc -zv <host> <port>", "risk": "low"},
        {"step": 6, "purpose": "Check listening ports", "command": "ss -tlnp", "risk": "low"},
        {"step": 7, "purpose": "Check firewall rules", "command": "iptables -L -n --line-numbers", "risk": "low"},
    ],
    "linux": [
        {"step": 1, "purpose": "Check disk usage", "command": "df -h", "risk": "low"},
        {"step": 2, "purpose": "Find large files", "command": "du -sh /* 2>/dev/null | sort -rh | head -20", "risk": "low"},
        {"step": 3, "purpose": "Check memory usage", "command": "free -m", "risk": "low"},
        {"step": 4, "purpose": "Check CPU and load", "command": "top -bn1 | head -20", "risk": "low"},
        {"step": 5, "purpose": "Check running processes", "command": "ps aux --sort=-%mem | head -20", "risk": "low"},
        {"step": 6, "purpose": "Check system logs", "command": "journalctl -xe --since '1 hour ago' | tail -100", "risk": "low"},
        {"step": 7, "purpose": "Check OOM kills", "command": "dmesg | grep -i 'killed process'", "risk": "low"},
        {"step": 8, "purpose": "Check inode usage", "command": "df -i", "risk": "low"},
    ],
    "ssl_tls": [
        {"step": 1, "purpose": "Check certificate expiry", "command": "echo | openssl s_client -connect <host>:443 2>/dev/null | openssl x509 -noout -dates", "risk": "low"},
        {"step": 2, "purpose": "Check certificate chain", "command": "openssl s_client -connect <host>:443 -showcerts 2>/dev/null | head -60", "risk": "low"},
        {"step": 3, "purpose": "Verify certificate hostname", "command": "openssl s_client -connect <host>:443 2>/dev/null | openssl x509 -noout -subject -subj_hash", "risk": "low"},
        {"step": 4, "purpose": "Test TLS versions supported", "command": "nmap --script ssl-enum-ciphers -p 443 <host>", "risk": "low"},
    ],
    "api": [
        {"step": 1, "purpose": "Check endpoint health", "command": "curl -s -o /dev/null -w '%{http_code}' https://<host>/health", "risk": "low"},
        {"step": 2, "purpose": "Check response time", "command": "curl -s -w '\\nTotal: %{time_total}s\\n' -o /dev/null https://<host>/api/endpoint", "risk": "low"},
        {"step": 3, "purpose": "Check headers", "command": "curl -I https://<host>/api/endpoint", "risk": "low"},
        {"step": 4, "purpose": "Check DNS resolution", "command": "dig <host> +short", "risk": "low"},
        {"step": 5, "purpose": "Trace TCP connection", "command": "curl -v --connect-timeout 10 https://<host>/api/endpoint 2>&1 | head -40", "risk": "low"},
    ],
    "dns": [
        {"step": 1, "purpose": "Query DNS record", "command": "dig <hostname> A +short", "risk": "low"},
        {"step": 2, "purpose": "Check all record types", "command": "dig <hostname> ANY +noall +answer", "risk": "low"},
        {"step": 3, "purpose": "Query authoritative nameservers", "command": "dig <hostname> NS +short", "risk": "low"},
        {"step": 4, "purpose": "Check from public DNS", "command": "dig @8.8.8.8 <hostname> +short", "risk": "low"},
        {"step": 5, "purpose": "Reverse DNS lookup", "command": "dig -x <ip-address> +short", "risk": "low"},
        {"step": 6, "purpose": "Check TTL", "command": "dig <hostname> +ttlid", "risk": "low"},
    ],
    "jenkins": [
        {"step": 1, "purpose": "Check Jenkins service status", "command": "systemctl status jenkins", "risk": "low"},
        {"step": 2, "purpose": "View Jenkins logs", "command": "journalctl -u jenkins --since '1 hour ago' | tail -100", "risk": "low"},
        {"step": 3, "purpose": "Check disk space for workspace", "command": "df -h /var/lib/jenkins", "risk": "low"},
        {"step": 4, "purpose": "Check Java version", "command": "java -version 2>&1", "risk": "low"},
        {"step": 5, "purpose": "Check agent connectivity", "command": "curl -s http://jenkins-host:8080/api/json | python3 -m json.tool | head -20", "risk": "low"},
    ],
    "github_actions": [
        {"step": 1, "purpose": "View workflow run logs via CLI", "command": "gh run view <run-id> --log", "risk": "low"},
        {"step": 2, "purpose": "List recent workflow runs", "command": "gh run list --limit 10", "risk": "low"},
        {"step": 3, "purpose": "Check workflow file syntax", "command": "cat .github/workflows/<name>.yml | python3 -c 'import sys,yaml; yaml.safe_load(sys.stdin)'", "risk": "low"},
        {"step": 4, "purpose": "Verify secrets are set", "command": "gh secret list", "risk": "low"},
    ],
}

_FALLBACK_CHECKLIST = [
    {"step": 1, "purpose": "Check system logs", "command": "journalctl -xe --since '1 hour ago' | tail -100", "risk": "low"},
    {"step": 2, "purpose": "Check disk usage", "command": "df -h", "risk": "low"},
    {"step": 3, "purpose": "Check memory", "command": "free -m", "risk": "low"},
    {"step": 4, "purpose": "Check running processes", "command": "ps aux --sort=-%cpu | head -20", "risk": "low"},
    {"step": 5, "purpose": "Check network connectivity", "command": "ping -c 3 8.8.8.8", "risk": "low"},
]


def get_checklist(issue_category: str) -> List[Dict[str, Any]]:
    """Return a diagnostic checklist for the given issue category."""
    key = issue_category.lower().replace("-", "_").replace(" ", "_")
    return _CHECKLISTS.get(key, _FALLBACK_CHECKLIST)


def get_all_categories() -> List[str]:
    return list(_CHECKLISTS.keys())
