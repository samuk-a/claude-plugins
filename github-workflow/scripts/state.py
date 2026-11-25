#!/usr/bin/env python3
"""Manage local resumable workflow state. Stores no credentials or secrets."""

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def parse_url(url):
    u = urlparse(url)
    m = re.fullmatch(r"/([^/]+)/([^/]+)/issues/([0-9]+)", u.path)
    if u.scheme != "https" or u.netloc != "github.com" or not m:
        raise ValueError("Expected https://github.com/OWNER/REPO/issues/NUMBER")
    owner, repo, number = m.groups()
    return owner, repo, number


def state_path(number):
    import subprocess
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "claude-workflow-state"],
        text=True, capture_output=True
    )
    if result.returncode:
        raise SystemExit("Run this command from inside a Git repository.")
    base = Path(result.stdout.strip())
    if not base.is_absolute():
        base = Path.cwd() / base
    return base / f"issue-{number}.json"


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init")
    init.add_argument("issue_url")
    init.add_argument("--branch", default="")
    update = sub.add_parser("update")
    update.add_argument("issue_url")
    update.add_argument("--stage", required=True)
    update.add_argument("--status", choices=["pending", "in_progress", "completed", "blocked"], required=True)
    update.add_argument("--note", default="")
    update.add_argument("--branch")
    update.add_argument("--commit")
    update.add_argument("--pr-url")
    show = sub.add_parser("show")
    show.add_argument("issue_url")
    args = ap.parse_args()

    owner, repo, number = parse_url(args.issue_url)
    path = state_path(number)

    if args.cmd == "init":
        if path.exists():
            print(path.read_text(encoding="utf-8"))
            return 0
        data = {
            "schema_version": 1,
            "issue_url": args.issue_url,
            "repository": f"{owner}/{repo}",
            "issue_number": int(number),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "branch": args.branch,
            "commit": None,
            "pr_url": None,
            "stages": {
                key: {"status": "pending", "note": ""}
                for key in ["preflight", "analysis", "branch", "implementation",
                            "checklist", "tests", "review", "commit", "push",
                            "pull_request", "ci"]
            }
        }
        atomic_write(path, data)
        print(path)
        return 0

    if not path.exists():
        raise SystemExit(f"No state file: {path}. Run init first.")
    data = json.loads(path.read_text(encoding="utf-8"))

    if args.cmd == "show":
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    if args.stage not in data["stages"]:
        raise SystemExit(f"Unknown stage: {args.stage}")
    data["stages"][args.stage]["status"] = args.status
    data["stages"][args.stage]["note"] = args.note
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if args.branch is not None:
        data["branch"] = args.branch
    if args.commit is not None:
        data["commit"] = args.commit
    if args.pr_url is not None:
        data["pr_url"] = args.pr_url
    atomic_write(path, data)
    print(path)
    return 0


if __name__ == "__main__":
    main()
