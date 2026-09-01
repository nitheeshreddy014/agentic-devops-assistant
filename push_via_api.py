import os, json, base64, urllib.request, urllib.error, sys
from pathlib import Path

TOKEN    = "YOUR_GITHUB_TOKEN_HERE"
OWNER    = "nitheeshreddy014"
REPO     = "agentic-devops-assistant"
BRANCH   = "main"
BASE_URL = "https://api.github.com/repos/" + OWNER + "/" + REPO

HEADERS = {
    "Authorization": "token " + TOKEN,
    "Accept":        "application/vnd.github.v3+json",
    "Content-Type":  "application/json",
}

SKIP_FILES = {".env", "server.log", "backend.log", "uvicorn_test.log",
              "push_via_api.py", "test_inv.py", "push_output.txt"}
SKIP_DIRS  = {".git", "__pycache__", ".next", "node_modules",
              ".venv", "venv", ".pytest_cache"}

def api(method, path, body=None):
    url  = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(method + " " + path + " " + str(e.code) + ": " + e.read().decode()[:200])

root = Path.cwd()

# --- Step 0: initialise empty repo via Contents API (only Contents API works on empty repos) ---
sys.stdout.write("[0/5] Initialising repo with README...\n"); sys.stdout.flush()
readme_b64 = base64.b64encode((root / "README.md").read_bytes()).decode()
init_req = urllib.request.Request(
    BASE_URL + "/contents/README.md",
    data=json.dumps({"message": "chore: init", "content": readme_b64, "branch": BRANCH}).encode(),
    headers=HEADERS, method="PUT")
try:
    with urllib.request.urlopen(init_req, timeout=30) as r:
        init_sha = json.loads(r.read())["commit"]["sha"]
        sys.stdout.write("      init sha: " + init_sha + "\n"); sys.stdout.flush()
except urllib.error.HTTPError as e:
    body = e.read().decode()
    if e.code == 422:
        sys.stdout.write("      already initialised\n"); sys.stdout.flush()
        init_sha = api("GET", "/git/refs/heads/" + BRANCH)["object"]["sha"]
    else:
        raise RuntimeError("init failed: " + str(e.code) + " " + body[:200])

# --- Step 1: collect files ---
sys.stdout.write("[1/5] Collecting files...\n"); sys.stdout.flush()
files = {}
for p in root.rglob("*"):
    if p.is_dir():
        continue
    parts = p.relative_to(root).parts
    if any(d in SKIP_DIRS for d in parts):
        continue
    if p.name in SKIP_FILES:
        continue
    rel = p.relative_to(root).as_posix()
    files[rel] = p
sys.stdout.write("      " + str(len(files)) + " files\n"); sys.stdout.flush()

# --- Step 2: create blobs ---
sys.stdout.write("[2/5] Uploading blobs...\n"); sys.stdout.flush()
tree_items = []
total = len(files)
for i, (rel, path) in enumerate(sorted(files.items()), 1):
    try:
        content_b64 = base64.b64encode(path.read_bytes()).decode()
        sha = api("POST", "/git/blobs", {"content": content_b64, "encoding": "base64"})["sha"]
        tree_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
        sys.stdout.write("      [" + str(i) + "/" + str(total) + "] " + rel + "\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write("      SKIP " + rel + ": " + str(e)[:80] + "\n")
        sys.stdout.flush()

# --- Step 3: create tree ---
sys.stdout.write("[3/5] Creating tree...\n"); sys.stdout.flush()
tree_sha = api("POST", "/git/trees", {"tree": tree_items})["sha"]
sys.stdout.write("      tree: " + tree_sha + "\n"); sys.stdout.flush()

# --- Step 4: create commit on top of init commit ---
sys.stdout.write("[4/5] Creating commit...\n"); sys.stdout.flush()
parent_sha = api("GET", "/git/refs/heads/" + BRANCH)["object"]["sha"]
commit_sha = api("POST", "/git/commits", {
    "message": "feat: add all project files\n\n- LangGraph 8-agent workflow\n- BM25 RAG 16 runbooks\n- FastAPI + Next.js\n- Vercel ready\n- Fixed firewall-blocked LLM fallback",
    "tree":    tree_sha,
    "parents": [parent_sha],
})["sha"]
sys.stdout.write("      commit: " + commit_sha + "\n"); sys.stdout.flush()

# --- Step 5: update branch ref ---
sys.stdout.write("[5/5] Updating branch ref...\n"); sys.stdout.flush()
api("PATCH", "/git/refs/heads/" + BRANCH, {"sha": commit_sha, "force": True})
sys.stdout.write("DONE: https://github.com/" + OWNER + "/" + REPO + "\n"); sys.stdout.flush()
