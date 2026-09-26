"""
Rule-based reference implementation of `compliance-agent`.
Swap for orchestrator/bob_backend.py + bob-agents/compliance-agent.md
(with checklist.md fed in via document understanding) during the hackathon.
"""
import os
import re
import json

from .. import diffparse, gitutil

ENV_READ = re.compile(r"os\.(?:environ(?:\.get)?|getenv)\(['\"](\w+)['\"]")
SECRET_LITERAL = re.compile(r"(?i)(api_key|password|secret|token)\s*=\s*['\"][^'\"]+['\"]")
CHECKLIST_ITEM = re.compile(r"^\s*-\s*\[ \]\s*(.+)$")


def run(repo_root, base_branch, feature_branch, sample_project_path="sample-project"):
    checklist_items = _parse_checklist(os.path.join(repo_root, "checklist.md"))

    src_dir = os.path.join(repo_root, sample_project_path)
    all_source = _read_all_py(os.path.join(src_dir, "app"))
    readme = _read(os.path.join(src_dir, "README.md"))
    env_example = _read(os.path.join(src_dir, ".env.example"))
    changelog = _read(os.path.join(src_dir, "CHANGELOG.md"))

    diff_text = gitutil.diff(repo_root, base_branch, feature_branch, sample_project_path)
    changelog_diff_added = "+" in "".join(
        l for l in diff_text.splitlines() if "CHANGELOG.md" in diff_text
    )

    env_vars_in_code = set(ENV_READ.findall(all_source))
    env_vars_documented = set(re.findall(r"^(\w+)\s*=", env_example, re.MULTILINE))
    undocumented_env_vars = env_vars_in_code - env_vars_documented

    findings = []
    onboarding_relevant = {}

    # --- Onboarding-relevant checks ---
    if undocumented_env_vars:
        for var in undocumented_env_vars:
            findings.append({
                "file": ".env.example",
                "line": None,
                "severity": "blocker",
                "category": "compliance",
                "description": f"Checklist item 'environment variables documented' = FAIL. "
                                f"'{var}' is read from the environment but missing from .env.example.",
                "suggested_fix": f"Add {var}=<default or example value> to .env.example with a comment.",
            })
        onboarding_relevant["env_vars_documented"] = "FAIL"
    else:
        onboarding_relevant["env_vars_documented"] = "PASS"

    setup_documented = "pip install" in readme
    onboarding_relevant["setup_documented"] = "PASS" if setup_documented else "FAIL"
    if not setup_documented:
        findings.append({
            "file": "README.md", "line": None, "severity": "warning",
            "category": "compliance",
            "description": "Checklist item 'setup steps documented' = FAIL. No install instructions found in README.md.",
            "suggested_fix": "Add a Setup section with install and run steps.",
        })

    test_cmd_documented = "unittest" in readme or "pytest" in readme
    onboarding_relevant["test_command_documented"] = "PASS" if test_cmd_documented else "FAIL"
    if not test_cmd_documented:
        findings.append({
            "file": "README.md", "line": None, "severity": "warning",
            "category": "compliance",
            "description": "Checklist item 'test command documented' = FAIL.",
            "suggested_fix": "Add the exact test command to README.md.",
        })

    # --- Release-relevant checks ---
    secret_hits = SECRET_LITERAL.findall(all_source)
    if secret_hits:
        findings.append({
            "file": "app/", "line": None, "severity": "blocker",
            "category": "compliance",
            "description": f"Checklist item 'no hardcoded secrets' = FAIL. Found literal(s) matching: {set(secret_hits)}.",
            "suggested_fix": "Move to environment variables and add to .env.example (without real values).",
        })
    else:
        findings.append({
            "file": "app/", "line": None, "severity": "info",
            "category": "compliance",
            "description": "Checklist item 'no hardcoded secrets' = PASS. No literal secret patterns found.",
            "suggested_fix": None,
        })

    findings.append({
        "file": "CHANGELOG.md", "line": None,
        "severity": "info" if changelog_diff_added else "warning",
        "category": "compliance",
        "description": (
            "Checklist item 'breaking changes documented with version bump' = "
            + ("PASS" if changelog_diff_added else "UNCLEAR/FAIL — CHANGELOG.md was not touched by this diff.")
        ),
        "suggested_fix": None if changelog_diff_added else "Add a CHANGELOG entry for this PR.",
    })

    for unverifiable in ["Security review completed", "Rollback plan documented", "Migrations are reversible"]:
        findings.append({
            "file": None, "line": None, "severity": "info",
            "category": "compliance",
            "description": f"Checklist item '{unverifiable}' = UNCLEAR — cannot be verified from repo content alone. Needs human sign-off.",
            "suggested_fix": "Confirm manually before merge.",
        })

    _write_json(os.path.join(repo_root, "setup-checklist.json"), onboarding_relevant)
    return findings


def _parse_checklist(path):
    items = []
    for line in _read(path).splitlines():
        m = CHECKLIST_ITEM.match(line)
        if m:
            items.append(m.group(1))
    return items


def _read(path):
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _read_all_py(directory):
    combined = ""
    if not os.path.isdir(directory):
        return combined
    for root, _, names in os.walk(directory):
        for name in names:
            if name.endswith(".py"):
                combined += _read(os.path.join(root, name))
    return combined


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


if __name__ == "__main__":
    import sys
    repo_root, base, feature = sys.argv[1], sys.argv[2], sys.argv[3]
    print(json.dumps(run(repo_root, base, feature), indent=2))
