import os

SEVERITY_PENALTY = {"blocker": 25, "warning": 10, "info": 0}


def build_release_report(repo_root, all_findings, timings):
    score = 100
    for finding in all_findings:
        score -= SEVERITY_PENALTY.get(finding.get("severity", "info"), 0)
    score = max(score, 0)

    blockers = [f for f in all_findings if f.get("severity") == "blocker"]
    warnings = [f for f in all_findings if f.get("severity") == "warning"]
    infos = [f for f in all_findings if f.get("severity") == "info"]

    lines = [
        "# Release Readiness Report",
        "",
        f"## Score: {score} / 100",
        "",
        f"**{len(blockers)} blocker(s), {len(warnings)} warning(s), {len(infos)} info item(s)**",
        "",
        "## Agent execution timing (proof of parallel run)",
        "",
    ]
    for agent, (start, end) in timings.items():
        lines.append(f"- `{agent}`: started {start:.3f}s, finished {end:.3f}s (elapsed {end - start:.3f}s)")
    lines.append("")

    for title, items in [("🚫 Blockers (must fix before merge)", blockers),
                          ("⚠️ Warnings", warnings),
                          ("ℹ️ Info", infos)]:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("_None_")
        for f in items:
            loc = f"{f.get('file')}:{f.get('line')}" if f.get("file") else "(repo-level)"
            lines.append(f"- **[{f.get('category')}]** `{loc}` — {f.get('description')}")
            if f.get("suggested_fix"):
                lines.append(f"  - Fix: {f.get('suggested_fix')}")
        lines.append("")

    report = "\n".join(lines)
    out_path = os.path.join(repo_root, "release-report.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    return out_path, score
