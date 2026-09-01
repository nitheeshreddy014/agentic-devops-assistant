# Jenkins Build Failures Runbook

## Overview
Jenkins build failures range from infrastructure-level problems (disk, memory, connectivity) to pipeline-level issues (misconfigured steps, credential failures, plugin incompatibilities).

## Common Causes
- Insufficient disk on Jenkins master or agent
- Out-of-memory (Java heap exhaustion)
- Credential not found or expired
- Agent offline or disconnected
- Plugin version conflict
- SCM checkout failure (git auth, wrong branch)
- Build tool not installed on agent (Maven, Gradle, Node)

## Diagnostic Steps

### Step 1: Check Jenkins service status
```bash
systemctl status jenkins
journalctl -u jenkins --since "1 hour ago" | tail -100
```

### Step 2: Check disk space
```bash
df -h /var/lib/jenkins
df -h /tmp
du -sh /var/lib/jenkins/workspace/* | sort -rh | head -10
```

### Step 3: Check Java heap (Jenkins master)
```bash
ps aux | grep jenkins
# Look for -Xmx value
cat /etc/default/jenkins | grep JAVA_ARGS
```

### Step 4: Review build console output
```
# In Jenkins UI: Build → Console Output
# CLI:
java -jar jenkins-cli.jar -s http://localhost:8080/ console <job> <build-number>
```

### Step 5: Check agent connectivity
```bash
# In Jenkins UI: Manage Jenkins → Nodes → <agent> → Log
# CLI check:
curl -s http://localhost:8080/computer/<agent>/api/json | python3 -m json.tool | grep -E '"offline|displayName"'
```

### Step 6: Check credentials
```
# Jenkins UI: Credentials → Global → Check each credential exists
# In Jenkinsfile: validate withCredentials block matches credential ID
```

## Resolution

### Fix Disk Space
```bash
# Clean old workspaces (non-destructive to builds)
find /var/lib/jenkins/workspace -maxdepth 1 -mtime +7 -exec rm -rf {} +

# Clean old builds via Jenkins CLI
java -jar jenkins-cli.jar -s http://localhost:8080/ delete-builds <job> 1-100
```

### Fix Java Heap
```bash
# Edit /etc/default/jenkins
JAVA_ARGS="-Djava.awt.headless=true -Xmx2g -Xms512m"
systemctl restart jenkins   # REQUIRES APPROVAL
```

### Fix Missing Agent Tool
```groovy
// Jenkinsfile — use tool directive
tools {
    maven 'Maven-3.9'
    nodejs 'Node-20'
}
```

### Fix Credential Issue
```groovy
// Jenkinsfile — correct credential binding
withCredentials([
    usernamePassword(
        credentialsId: 'my-dockerhub-cred',
        usernameVariable: 'DOCKER_USER',
        passwordVariable: 'DOCKER_PASS'
    )
]) {
    sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
}
```

## Rollback
- Jenkins builds are not infrastructure changes — re-run the previous successful build.
- Use "Replay" on a previous build to re-execute with identical parameters.

## Related Issues
- `linux-disk-memory-cpu.md`
- `github-actions-failures.md`
- `ssl-tls-problems.md`
