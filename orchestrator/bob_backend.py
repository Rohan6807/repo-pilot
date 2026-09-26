"""
Real Bob Shell backend — use this during the hackathon in place of the
rule-based agents in orchestrator/agents/*.py once you have live Bob access.

This wraps Bob Shell's non-interactive mode: it sends the agent's role
definition (from bob-agents/*.md) as context, along with the diff/repo
content, and expects back JSON matching bob-agents/output-schema.md.

Swap point: each rule-based agent's `run()` returns a Python list of dicts.
This module's `run_bob_agent()` returns the same shape, so report_builder.py
and run.py don't need to change no matter which backend produced the data —
that's what makes it safe to build/demo against the rule-based version all
day and flip to real Bob only when you want to prove live usage on camera.

Adjust the exact Bob Shell CLI invocation below to match whatever your
installed Bob Shell version expects (check `bob shell --help`); the shape
here follows the non-interactive usage pattern from the hackathon guide.
"""
import json
import subprocess


def run_bob_agent(mode_file, prompt, repo_root):
    """
    mode_file: path to a bob-agents/*.md role definition
    prompt: the specific task instruction, e.g. "Analyze the diff between
            master and feature/bulk-update"
    repo_root: working directory for Bob Shell to operate in
    """
    with open(mode_file, encoding="utf-8") as fh:
        role_definition = fh.read()

    full_prompt = f"{role_definition}\n\n---\n\nTASK:\n{prompt}"

    result = subprocess.run(
        ["bob", "shell", "-p", full_prompt, "--cwd", repo_root, "--output", "json"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Bob Shell failed: {result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # Bob sometimes wraps JSON in prose despite instructions — this is
        # exactly the kind of context-hygiene issue the cost-control notes
        # warn about. Log the raw output for debugging rather than silently
        # dropping findings.
        print("WARNING: could not parse Bob output as JSON:\n", result.stdout)
        return []
