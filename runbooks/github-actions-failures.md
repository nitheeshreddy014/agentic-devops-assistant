# GitHub Actions Failures Runbook

## Overview
GitHub Actions workflow failures prevent CI/CD pipelines from building, testing, or deploying code. Failures range from YAML syntax errors to runner resource issues.

## Common Causes
- Secret not configured in repository / environment settings
- Action pinned to mutable tag or unavailable version
- Runner out of disk space or memory
- Workflow YAML syntax error
- Permission token insufficient for operation
- Environment protection rule blocking deployment
- Dependency installation failure (npm, pip, Maven)

## Diagnostic Steps

### Step 1: View failed run logs
```bash
gh run view <run-id> --log-failed
gh run list --limit 10 --workflow <workflow-name>
```

### Step 2: Check workflow YAML syntax
```bash
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/<name>.yml'))"
# Or use actionlint
actionlint .github/workflows/<name>.yml
```

### Step 3: Verify secrets exist
```bash
gh secret list
gh secret list --env <environment-name>
```

### Step 4: Check job permissions
```yaml
# In the workflow file — look for:
permissions:
  contents: read
  packages: write
  id-token: write   # Required for OIDC
```

### Step 5: Check runner disk space
```yaml
# Add this step to the failing job:
- name: Check disk
  run: df -h && du -sh /home/runner/work
```

### Step 6: Re-run with debug logging
```bash
gh run rerun <run-id> --debug
# Or set secrets: ACTIONS_RUNNER_DEBUG=true, ACTIONS_STEP_DEBUG=true
```

## Resolution

### Fix Missing Secret
```bash
gh secret set MY_SECRET --body "secret-value"
gh secret set DEPLOY_KEY < ~/.ssh/id_rsa
```

### Fix Action Version
```yaml
# Pin to specific commit SHA (most secure)
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

# Or pin to immutable tag
- uses: actions/setup-node@v4.1.0
```

### Fix Permissions
```yaml
jobs:
  deploy:
    permissions:
      contents: read
      id-token: write      # OIDC for cloud auth
      packages: write      # For GHCR pushes
```

### Fix Disk Space on Runner
```yaml
- name: Free disk space
  run: |
    sudo rm -rf /usr/share/dotnet
    sudo rm -rf /usr/local/lib/android
    df -h
```

### Fix Flaky Test Step
```yaml
- name: Run tests
  uses: nick-fields/retry@v3
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: npm test
```

## Rollback
```bash
# Re-run last successful deployment
gh run rerun <last-successful-run-id>

# Or trigger workflow manually on previous tag
gh workflow run deploy.yml --ref v1.2.3
```

## Related Issues
- `jenkins-failures.md`
- `docker-build-failures.md`
- `ssl-tls-problems.md`
