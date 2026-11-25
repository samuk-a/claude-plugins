#!/usr/bin/env python3
"""Safely mark one exact unchecked checklist item on a GitHub issue.

Uses gh CLI. Performs a refetch immediately before write and aborts if the
body changed. GitHub CLI issue edit does not expose an atomic CAS/ETag write,
so a very small race remains; see README.
"""

import argparse
import subprocess
import sys
import re
from urllib.parse import urlparse


def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"Command failed: {cmd[0]}")
    return p.stdout


def parse_url(url):
    u = urlparse(url)
    m = re.fullmatch(r"/([^/]+)/([^/]+)/issues/([0-9]+)", u.path)
    if u.scheme != "https" or u.netloc != "github.com" or not m:
        raise ValueError("Expected https://github.com/OWNER/REPO/issues/NUMBER")
    owner, repo, number = m.groups()
    return f"{owner}/{repo}", number


def fetch_body(repo, number):
    return run(["gh", "issue", "view", number, "--repo", repo,
                "--json", "body", "--jq", ".body"])


def mark_one(body, target):
    lines = body.splitlines()
    matches = []
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*[-*]\s+)\[ \](\s+)(.*)$", line)
        if m and m.group(3).strip() == target:
            matches.append((i, m))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one unchecked exact match for {target!r}; "
            f"found {len(matches)}. No update performed."
        )
    i, m = matches[0]
    lines[i] = f"{m.group(1)}[x]{m.group(2)}{m.group(3)}"
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_url")
    ap.add_argument("task_text")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo, number = parse_url(args.issue_url)
    original = fetch_body(repo, number)
    updated = mark_one(original, args.task_text.strip())

    if args.dry_run:
        sys.stdout.write(updated)
        return 0

    latest = fetch_body(repo, number)
    if latest != original:
        raise RuntimeError(
            "Issue body changed since it was read. Aborting to avoid overwriting "
            "another person's edits. Re-read the issue and retry."
        )

    run(["gh", "issue", "edit", number, "--repo", repo, "--body", updated])
    print(f"Marked complete: {args.task_text}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
