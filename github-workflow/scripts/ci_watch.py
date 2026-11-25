#!/usr/bin/env python3
"""Bounded GitHub Actions check watcher for a PR using gh CLI."""

import argparse
import json
import subprocess
import sys
import time
from urllib.parse import urlparse
import re


def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def parse_pr(url):
    u = urlparse(url)
    m = re.fullmatch(r"/([^/]+)/([^/]+)/pull/([0-9]+)", u.path)
    if u.scheme != "https" or u.netloc != "github.com" or not m:
        raise ValueError("Expected https://github.com/OWNER/REPO/pull/NUMBER")
    owner, repo, number = m.groups()
    return f"{owner}/{repo}", number


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pr_url")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    if args.timeout < 1 or args.timeout > 7200:
        ap.error("--timeout must be between 1 and 7200 seconds")
    if args.interval < 3 or args.interval > 300:
        ap.error("--interval must be between 3 and 300 seconds")

    repo, number = parse_pr(args.pr_url)
    deadline = time.monotonic() + args.timeout

    while True:
        rc, out, err = run([
            "gh", "pr", "checks", number, "--repo", repo,
            "--json", "name,state,link,workflow"
        ])
        if rc != 0:
            print(json.dumps({"status": "unknown", "detail": err or out}, indent=2))
            return 2

        try:
            checks = json.loads(out)
        except json.JSONDecodeError:
            print(json.dumps({"status": "unknown", "detail": out}, indent=2))
            return 2

        states = [str(c.get("state", "")).upper() for c in checks]
        pending = any(s in {"PENDING", "QUEUED", "IN_PROGRESS", "REQUESTED", "WAITING"} for s in states)
        failed = any(s in {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"} for s in states)

        if failed:
            print(json.dumps({"status": "failed", "checks": checks}, indent=2))
            return 1
        if checks and not pending:
            print(json.dumps({"status": "passed", "checks": checks}, indent=2))
            return 0
        if not checks:
            # No checks may mean not configured or not yet reported; do not call it passed.
            if time.monotonic() >= deadline:
                print(json.dumps({"status": "no_checks_or_not_reported", "checks": []}, indent=2))
                return 3
        if time.monotonic() >= deadline:
            print(json.dumps({"status": "timeout", "checks": checks}, indent=2))
            return 3
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
