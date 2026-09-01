"""MCP-compatible tool: Kubernetes YAML analysis."""
from __future__ import annotations

import re
from typing import Any, Dict, List

try:
    import yaml  # pyyaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


_TEXT_FINDINGS: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"imagePullPolicy:\s*Never", re.I),
     "warning", "imagePullPolicy: Never — image must pre-exist on node",
     "Use IfNotPresent or Always for production."),
    (re.compile(r"imagePullPolicy:\s*Always", re.I),
     "warning", "imagePullPolicy: Always — pulls on every restart (slower)",
     "Use IfNotPresent unless you rely on mutable tags like :latest."),
    (re.compile(r"image:\s*\S+:latest", re.I),
     "warning", "Mutable :latest tag — not reproducible",
     "Pin image to a specific digest or immutable tag."),
    (re.compile(r"restartPolicy:\s*Never", re.I),
     "warning", "restartPolicy: Never — pod will not restart on failure",
     "Use Always or OnFailure for workload pods."),
    (re.compile(r"privileged:\s*true", re.I),
     "error", "Container running in privileged mode — full host access",
     "Remove privileged: true unless absolutely required."),
    (re.compile(r"allowPrivilegeEscalation:\s*true", re.I),
     "error", "allowPrivilegeEscalation: true — security risk",
     "Set allowPrivilegeEscalation: false in securityContext."),
    (re.compile(r"runAsRoot:\s*true|runAsUser:\s*0\b", re.I),
     "warning", "Container running as root (UID 0)",
     "Set runAsUser to a non-zero UID in securityContext."),
    (re.compile(r"hostNetwork:\s*true", re.I),
     "warning", "hostNetwork: true — container shares host network namespace",
     "Avoid hostNetwork unless explicitly required."),
    (re.compile(r"hostPID:\s*true", re.I),
     "warning", "hostPID: true — container can see host processes",
     "Remove hostPID unless required."),
    (re.compile(r"resources:\s*\{\}", re.I),
     "warning", "Empty resources block — no CPU/memory limits set",
     "Set resources.limits and resources.requests for all containers."),
    (re.compile(r"requests:|limits:", re.I),
     "info", "Resource requests/limits found",
     "Verify values are appropriate for workload."),
    (re.compile(r"livenessProbe:", re.I),
     "info", "Liveness probe configured",
     "Verify probe endpoint and thresholds."),
    (re.compile(r"readinessProbe:", re.I),
     "info", "Readiness probe configured",
     "Verify probe endpoint is correct."),
    (re.compile(r"replicas:\s*1\b", re.I),
     "warning", "Single replica — no high availability",
     "Set replicas >= 2 for production workloads."),
    (re.compile(r"terminationGracePeriodSeconds:\s*0\b", re.I),
     "error", "Zero termination grace period — immediate SIGKILL",
     "Set terminationGracePeriodSeconds to allow graceful shutdown."),
    (re.compile(r"nodeSelector:|tolerations:|affinity:", re.I),
     "info", "Node scheduling constraints detected",
     "Verify nodes satisfy constraints, else pods stay Pending."),
    (re.compile(r"PersistentVolumeClaim|volumeClaimTemplates:", re.I),
     "info", "Persistent storage claim detected",
     "Verify StorageClass exists and has sufficient capacity."),
    (re.compile(r"env:\s*\n.*value:\s*['\"]?(password|secret|key|token)['\"]?", re.I | re.DOTALL),
     "error", "Possible secret in plain-text env var",
     "Use Kubernetes Secret and secretKeyRef instead of plain values."),
    (re.compile(r"Pending|CrashLoopBackOff|OOMKilled|ImagePullBackOff|Error|Evicted", re.I),
     "error", "Pod failure state detected in description",
     "Investigate pod events: kubectl describe pod <name> -n <namespace>."),
]


def _safe_yaml_parse(text: str) -> list[dict]:
    """Parse YAML text and return list of documents."""
    if not _YAML_AVAILABLE:
        return []
    docs = []
    try:
        for doc in yaml.safe_load_all(text):
            if doc and isinstance(doc, dict):
                docs.append(doc)
    except yaml.YAMLError:
        pass
    return docs


def _extract_k8s_resources(docs: list[dict]) -> list[dict]:
    resources = []
    for doc in docs:
        kind = doc.get("kind", "Unknown")
        meta = doc.get("metadata", {}) or {}
        name = meta.get("name", "unnamed")
        namespace = meta.get("namespace", "default")
        resources.append({"kind": kind, "name": name, "namespace": namespace})
    return resources


def analyze_kubernetes(yaml_text: str) -> Dict[str, Any]:
    """
    MCP-compatible stateless tool: analyse Kubernetes YAML.
    Input is treated as plain text — NEVER executed.
    """
    if not yaml_text or not yaml_text.strip():
        return {"findings": [], "summary": "No Kubernetes YAML provided.", "severity": "low"}

    findings: List[Dict[str, Any]] = []
    lines = yaml_text.splitlines()

    # Text-pattern analysis
    seen: set[str] = set()
    for i, line in enumerate(lines):
        for pattern, ftype, desc, rec in _TEXT_FINDINGS:
            if ftype == "info":
                continue  # Skip info for cleaner output
            if pattern.search(line):
                key = f"{ftype}:{desc}"
                if key not in seen:
                    seen.add(key)
                    findings.append({
                        "finding_type": ftype,
                        "location": f"line {i + 1}: {line.strip()[:100]}",
                        "description": desc,
                        "recommendation": rec,
                    })
                break

    # YAML structural analysis
    docs = _safe_yaml_parse(yaml_text)
    resources = _extract_k8s_resources(docs)

    for doc in docs:
        kind = doc.get("kind", "")
        spec = doc.get("spec", {}) or {}

        # Check for missing resources
        if kind in ("Deployment", "StatefulSet", "DaemonSet"):
            tmpl = spec.get("template", {}) or {}
            pod_spec = tmpl.get("spec", {}) or {}
            containers = pod_spec.get("containers", []) or []
            for c in containers:
                if not c.get("resources"):
                    findings.append({
                        "finding_type": "warning",
                        "location": f"{kind}/{doc.get('metadata', {}).get('name', '?')}",
                        "description": f"Container '{c.get('name', '?')}' has no resource requests/limits",
                        "recommendation": "Set resources.requests and resources.limits.",
                    })
                if not c.get("livenessProbe"):
                    findings.append({
                        "finding_type": "warning",
                        "location": f"{kind}/{doc.get('metadata', {}).get('name', '?')}",
                        "description": f"Container '{c.get('name', '?')}' has no livenessProbe",
                        "recommendation": "Add a livenessProbe to enable automatic restart on hang.",
                    })

        # Check Service/Ingress
        if kind == "Service":
            svc_type = spec.get("type", "ClusterIP")
            if svc_type == "NodePort":
                findings.append({
                    "finding_type": "warning",
                    "location": f"Service/{doc.get('metadata', {}).get('name', '?')}",
                    "description": "NodePort service — exposes random port on all nodes",
                    "recommendation": "Prefer LoadBalancer or Ingress for external access.",
                })

    severity = "low"
    if any(f["finding_type"] == "error" for f in findings):
        severity = "high"
    elif any(f["finding_type"] == "warning" for f in findings):
        severity = "medium"

    summary = (
        f"Analysed {len(docs)} Kubernetes resource(s): "
        f"{', '.join(r['kind'] for r in resources[:8])}. "
        f"Found {len(findings)} issue(s). Severity: {severity}."
    )

    return {
        "findings": findings,
        "resources": resources,
        "summary": summary,
        "severity": severity,
    }
