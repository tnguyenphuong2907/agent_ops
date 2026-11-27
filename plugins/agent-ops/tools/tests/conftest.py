"""Keep tool tests independent of whatever project the shell points at.

The fake project adds a `learning` topic so the configurable topic and analyst rules are exercised.
"""
import os
import tempfile
from pathlib import Path

_PROJECT = tempfile.mkdtemp(prefix="agent-ops-test-")
Path(_PROJECT, ".agent-ops.toml").write_text(
    '[inbox]\nanalyst_topics = ["learning"]\n[inbox.topics]\n'
    'scope = "Scope"\nsecurity = "Security"\ncost = "Cost"\narchitecture = "Architecture"\n'
    'data = "Data"\nlearning = "Learning"\nops = "Ops"\nux = "UX"\n',
    encoding="utf-8",
)
os.environ.pop("CLAUDE_PROJECT_DIR", None)
os.environ["AGENT_OPS_PROJECT_DIR"] = _PROJECT
