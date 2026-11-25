#!/usr/bin/env python3
"""Read-only environment and repository preflight checks."""

import argparse
import json
import shutil
import subprocess
import sys
from urllib.parse import urlparse
import re


def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def parse_issue_url(url):
    u = urlparse(url)
    m = re.fullmatch(r"/([^/]+)/([^/]+)/issues/([0-9]+)", u.path)
    if u.scheme != "https" or u.netloc != "github.com" or not m:
        raise ValueError("URL esperada: https://github.com/OWNER/REPO/issues/NUMBER")
    return m.groups()


def normalize_remote(remote):
    remote = remote.strip()
    if remote.endswith(".git"):
        remote = remote[:-4]
    if remote.startswith("git@github.com:"):
        return "https://github.com/" + remote[len("git@github.com:"):]
    if remote.startswith("ssh://git@github.com/"):
        return "https://github.com/" + remote[len("ssh://git@github.com/"):]
    return remote.rstrip("/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_url", nargs="?")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="Não falha por working tree suja; apenas informa")
    args = ap.parse_args()

    report = {"checks": [], "ok": True}

    def check(name, ok, detail):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            report["ok"] = False

    for binary in ("git", "gh"):
        check(f"{binary} installed", shutil.which(binary) is not None,
              shutil.which(binary) or "not found")

    if shutil.which("git"):
        rc, out, err = run(["git", "rev-parse", "--show-toplevel"])
        check("inside git repository", rc == 0, out or err)
        if rc == 0:
            rc2, remote, err2 = run(["git", "remote", "get-url", "origin"])
            check("origin remote configured", rc2 == 0, remote or err2)
            rc3, status, err3 = run(["git", "status", "--porcelain"])
            dirty = bool(status)
            check("working tree clean" if not args.allow_dirty else "working tree status",
                  (not dirty) or args.allow_dirty,
                  "clean" if not dirty else "dirty; preserve all existing changes")
            rc4, branch, err4 = run(["git", "branch", "--show-current"])
            check("current branch readable", rc4 == 0, branch or err4)

    if shutil.which("gh"):
        rc, out, err = run(["gh", "auth", "status"])
        check("GitHub CLI authenticated", rc == 0, out or err)

    if args.issue_url:
        try:
            owner, repo, number = parse_issue_url(args.issue_url)
            check("issue URL valid", True, f"{owner}/{repo}#{number}")
            if shutil.which("gh"):
                rc, out, err = run([
                    "gh", "issue", "view", number, "--repo", f"{owner}/{repo}",
                    "--json", "number,title,state,url"
                ])
                check("issue accessible", rc == 0,
                      out or err)
                if rc == 0:
                    try:
                        report["issue"] = json.loads(out)
                    except json.JSONDecodeError:
                        check("issue JSON valid", False, out)
        except ValueError as exc:
            check("issue URL valid", False, str(exc))

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
