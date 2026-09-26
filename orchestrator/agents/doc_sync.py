"""
Rule-based reference implementation of `doc-sync-agent`.
Swap for orchestrator/bob_backend.py + bob-agents/doc-sync-agent.md during
the hackathon for real Bob-driven analysis.
"""
import os
import re
import json

from .. import diffparse, gitutil

ROUTE_LINE = re.compile(r'@(?:bp|app)\.(route|get|post|put|delete|patch)\(["\']([^"\']+)["\']')
DICT_KEY = re.compile(r'"(\w+)"\s*:')


def run(repo_root, base_branch, feature_branch, sample_project_path="sample-project"):
    diff_text = gitutil.diff(repo_root, base_branch, feature_branch, sample_project_path)
    files = diffparse.parse(diff_text)

    readme_path = os.path.join(repo_root, sample_project_path, "README.md")
    readme = _read(readme_path)

    changed_paths = {f["file"] for f in files}
    changelog_touched = any(p.endswith("CHANGELOG.md") for p in changed_paths)

    findings = []

    # 1. New/changed routes not mentioned in README
    for f in files:
        for lineno, text in diffparse.added_lines(f):
            m = ROUTE_LINE.search(text)
            if m and m.group(2) not in readme:
                findings.append({
                    "file": "README.md",
                    "line": None,
                    "severity": "warning",
                    "category": "doc_drift",
                    "description": f"Endpoint {m.group(1).upper()} {m.group(2)} is not documented in README.md's endpoint table.",
                    "suggested_fix": "Add a row to the endpoint table describing method, path, and body.",
                })

    # 2. Field renames not reflected in README's example payload
    for f in files:
        for hunk in f["hunks"]:
            removed_keys = {k for _, t in hunk["removed"] for k in DICT_KEY.findall(t)}
            added_keys = {k for _, t in hunk["added"] for k in DICT_KEY.findall(t)}
            stale_in_readme = (removed_keys - added_keys) & set(DICT_KEY.findall(readme))
            for key in stale_in_readme:
                findings.append({
                    "file": "README.md",
                    "line": None,
                    "severity": "warning",
                    "category": "doc_drift",
                    "description": f"README's response contract example still shows '{key}', which this PR removed/renamed in code.",
                    "suggested_fix": "Update the JSON example in README.md's 'Response contract' section.",
                })

    # 3. No CHANGELOG entry despite behavior changes
    if files and not changelog_touched:
        findings.append({
            "file": "CHANGELOG.md",
            "line": None,
            "severity": "blocker",
            "category": "doc_drift",
            "description": "This PR changes API behavior but CHANGELOG.md was not updated.",
            "suggested_fix": "Add an entry describing the breaking change and bump the version.",
        })

    return findings


def _read(path):
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    import sys
    repo_root, base, feature = sys.argv[1], sys.argv[2], sys.argv[3]
    print(json.dumps(run(repo_root, base, feature), indent=2))
