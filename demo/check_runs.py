#!/usr/bin/env python3
"""Mechanical checks of demo runs: cost, tools, subagents, MCP writes, changed files.

Usage: python check_runs.py WORK [scenario ...]
Content quality (did the analyst find the planted patterns?) is judged against EXPECTED.md.
"""
import collections
import glob
import json
import os
import subprocess
import sys

WRITE_TOOLS = ("write_query", "create_table", "append_insight")
ANALYSIS = {"an-learn", "an-improve", "an-verify", "projdoc", "hesber", "debt", "review", "sql", "design"}


def scan(work, name):
    tools = collections.Counter()
    agents = collections.Counter()
    mcp_writes = []
    cost = 0.0
    turns = 0
    for path in sorted(glob.glob(os.path.join(work, "_logs", f"{name}.*.jsonl"))):
        last_result = None
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "result":
                    last_result = msg  # a turn may log more than one result line; the last one counts
                    continue
                if msg.get("type") != "assistant":
                    continue
                for block in msg.get("message", {}).get("content", []):
                    if block.get("type") != "tool_use":
                        continue
                    tool = block.get("name", "")
                    tools[tool] += 1
                    inp = block.get("input", {})
                    if tool in ("Task", "Agent"):
                        agents[inp.get("subagent_type", "?")] += 1
                    if tool.endswith(WRITE_TOOLS):
                        mcp_writes.append(tool)
        if last_result:
            cost += last_result.get("total_cost_usd") or 0
            turns += last_result.get("num_turns") or 0
    project = os.path.join(work, name)
    changed = subprocess.run(["git", "status", "--short"], cwd=project, capture_output=True,
                             text=True).stdout.split("\n") if os.path.isdir(project) else []
    changed = [c for c in changed if c.strip()]
    knowledge = os.path.join(project, ".claude", "tl-memory", "KNOWLEDGE.md")
    return {"cost": cost, "turns": turns, "tools": tools, "agents": agents,
            "mcp_writes": mcp_writes, "changed": changed,
            "knowledge": sum(1 for line in open(knowledge, encoding="utf-8") if line.startswith("| ") and "---" not in line) - 1
            if os.path.exists(knowledge) else None,
            "agents_md": os.path.exists(os.path.join(project, "AGENTS.md"))}


def main(argv):
    work = argv[1]
    names = argv[2:] or sorted({os.path.basename(p).split(".")[0]
                                for p in glob.glob(os.path.join(work, "_logs", "*.jsonl"))})
    total = 0.0
    for name in names:
        r = scan(work, name)
        total += r["cost"]
        mcp = sum(v for k, v in r["tools"].items() if k.startswith("mcp__"))
        print(f"== {name}: ${r['cost']:.2f}, {r['turns']} turns, MCP calls {mcp}, "
              f"subagents {dict(r['agents']) or '-'}")
        print(f"   MCP writes: {r['mcp_writes'] or 'none'}")
        print(f"   changed files: {r['changed'] or 'none'}")
        print(f"   KNOWLEDGE.md rows: {r['knowledge'] if r['knowledge'] is not None else 'no file'} · "
              f"AGENTS.md: {'yes' if r['agents_md'] else 'no'}")
    print(f"TOTAL ${total:.2f}")


if __name__ == "__main__":
    main(sys.argv)
