"""
Rule-based reference implementation of the `test-gap-agent`.
Swap for orchestrator/bob_backend.py + bob-agents/test-gap-agent.md during
the hackathon for real Bob-driven analysis.
"""
import os
import re
import json

from .. import diffparse, gitutil

ROUTE_LINE = re.compile(r'@(?:bp|app)\.(route|get|post|put|delete|patch)\(["\']([^"\']+)["\']')
DEF_LINE = re.compile(r"^\s*def (\w+)\(")


def run(repo_root, base_branch, feature_branch, sample_project_path="sample-project"):
    diff_text = gitutil.diff(repo_root, base_branch, feature_branch, sample_project_path)
    files = diffparse.parse(diff_text)

    tests_dir = os.path.join(repo_root, sample_project_path, "tests")
    test_source = _read_all(tests_dir)

    findings = []
    stubs_written = []

    for f in files:
        added = diffparse.added_lines(f)
        new_routes = _find_new_routes(added)
        for path, method, lineno in new_routes:
            if path not in test_source:
                findings.append({
                    "file": f["file"],
                    "line": lineno,
                    "severity": "blocker",
                    "category": "test_gap",
                    "description": f"New endpoint {method.upper()} {path} has zero test coverage.",
                    "suggested_fix": f"See suggested-tests/test_{_slug(path)}.py for a starter stub.",
                })
                stub_path = _write_stub(repo_root, path, method)
                stubs_written.append(stub_path)

    return findings, stubs_written


def _find_new_routes(added_lines):
    results = []
    pending_lineno = None
    for lineno, text in added_lines:
        m = ROUTE_LINE.search(text)
        if m:
            pending_lineno = lineno
            method, path = m.group(1), m.group(2)
            results.append((path, method, pending_lineno))
    return results


def _read_all(directory):
    combined = ""
    if not os.path.isdir(directory):
        return combined
    for name in os.listdir(directory):
        if name.endswith(".py"):
            with open(os.path.join(directory, name), encoding="utf-8") as fh:
                combined += fh.read()
    return combined


def _slug(path):
    return re.sub(r"\W+", "_", path).strip("_")


def _write_stub(repo_root, path, method):
    out_dir = os.path.join(repo_root, "suggested-tests")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"test_{_slug(path)}.py"
    out_path = os.path.join(out_dir, filename)
    content = f'''"""
Auto-generated stub by test-gap-agent for the untested endpoint:
  {method.upper()} {path}

Fill in the TODOs with real expected values before merging.
"""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sample-project"))

from app import create_app, db  # noqa: E402


class {_slug(path).title().replace('_', '')}Test(unittest.TestCase):
    def setUp(self):
        db.reset()
        self.client = create_app().test_client()

    def test_{_slug(path)}_happy_path(self):
        # TODO(human): fill in a real request body for this endpoint.
        resp = self.client.{method}("{path}", json={{}})
        self.assertIn(resp.status_code, (200, 201))  # TODO(human): confirm exact code


if __name__ == "__main__":
    unittest.main()
'''
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return out_path


if __name__ == "__main__":
    import sys
    repo_root, base, feature = sys.argv[1], sys.argv[2], sys.argv[3]
    findings, stubs = run(repo_root, base, feature)
    print(json.dumps({"findings": findings, "stubs_written": stubs}, indent=2))
