#!/usr/bin/env python3
"""Lint architecture docs (run from repo root).

Checks
  1. Mermaid flowchart/graph edges in docs/02-architecture/**/*.md have a label
     (A -->|label| B, A -- label --> B); sequenceDiagram messages have text (A->>B: text).
     erDiagram and other diagram types are skipped.
  2. ADRs in docs/02-architecture/adr/: file name ADR-NNNN-<slug>.md matches title,
     numbers unique and without gaps, required headings from `${CLAUDE_PLUGIN_ROOT}/templates/adr.md,
     status line valid (proposed | accepted | superseded by ADR-xxxx | deprecated),
     "superseded by" points to an existing ADR.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/skills/architecture-design/scripts/check_arch_docs.py" [--warn-only]
Exit 1 when problems are found (0 with --warn-only).
"""
import re
import sys
from pathlib import Path

ARCH = Path("docs/02-architecture")
ADR_DIR = ARCH / "adr"
REQUIRED = ["Bối cảnh", "Các phương án đã cân nhắc", "Quyết định", "Hệ quả"]
STATUS = re.compile(r"^(proposed|accepted|deprecated|superseded by (ADR-\d{4}))\b", re.I)
FLOW_EDGE = re.compile(r"(-{2,3}>|={2,3}>|-\.->|--[ox]|<-->)")
LABELLED = re.compile(r"(-{2,3}>|={2,3}>|-\.->|<-->)\s*\|[^|]+\|")
TEXT_EDGE = re.compile(r"--\s+[^->|][^>]*?\s+-{1,2}>|==\s+[^=]+==>|-\.\s+[^.]+\.->")
SEQ_MSG = re.compile(r"^\s*[\w\"' ]+?\s*(-{1,2}>>|-{1,2}\)|-{1,2}x|-{1,2}>)\s*[+-]?[\w\"' ]+?\s*(:\s*(.*))?$")

problems = []


def report(path, line, msg):
    problems.append(f"{path}:{line}: {msg}")


def check_mermaid(path):
    kind, in_block = None, False
    for no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if line.startswith("```mermaid"):
            in_block, kind = True, None
            continue
        if in_block and line.startswith("```"):
            in_block = False
            continue
        if not in_block or not line or line.startswith("%%"):
            continue
        if kind is None:
            kind = line.split()[0]
            continue
        if kind in ("flowchart", "graph"):
            if line.startswith(("subgraph", "end", "classDef", "class ", "style ", "linkStyle", "click ")):
                continue
            edges = len(FLOW_EDGE.findall(line))
            labelled = len(LABELLED.findall(line)) + len(TEXT_EDGE.findall(line))
            if edges > labelled:
                report(path, no, f"{edges - labelled} unlabelled edge(s): {line[:90]}")
        elif kind == "sequenceDiagram":
            m = SEQ_MSG.match(line)
            if m and not (m.group(3) or "").strip():
                report(path, no, f"sequence message without text: {line[:90]}")


def check_adrs():
    files = sorted(ADR_DIR.glob("ADR-*.md"))
    numbers = {}
    for f in files:
        m = re.match(r"ADR-(\d{4})-[a-z0-9-]+\.md$", f.name)
        if not m:
            report(f, 1, "file name must be ADR-NNNN-<kebab-slug>.md")
            continue
        num = m.group(1)
        if num in numbers:
            report(f, 1, f"duplicate number {num} (also {numbers[num].name})")
        numbers[num] = f
    nums = sorted(int(n) for n in numbers)
    for a, b in zip(nums, nums[1:]):
        if b != a + 1:
            report(ADR_DIR, 0, f"numbering gap between ADR-{a:04d} and ADR-{b:04d}")
    for num, f in numbers.items():
        lines = f.read_text(encoding="utf-8").splitlines()
        if not lines or not lines[0].startswith(f"# ADR-{num}:"):
            report(f, 1, f"title must start with '# ADR-{num}:'")
        heads = [l[3:].strip() for l in lines if l.startswith("## ")]
        for req in REQUIRED:
            if not any(h.startswith(req) for h in heads):
                report(f, 0, f"missing heading '## {req}'")
        status = next((l for l in lines[:15] if "Trạng thái:" in l), None)
        if not status:
            report(f, 0, "missing '- **Trạng thái:** ...' line")
            continue
        value = status.split("Trạng thái:", 1)[1].replace("**", "").strip()
        sm = STATUS.match(value)
        if not sm:
            report(f, lines.index(status) + 1, f"invalid status '{value[:40]}'")
        elif sm.group(2) and sm.group(2)[4:] not in numbers:
            report(f, lines.index(status) + 1, f"superseded by missing {sm.group(2)}")


def main():
    if not ARCH.exists():
        print(f"Not found: {ARCH} (run from repo root)")
        return 2
    for md in sorted(ARCH.rglob("*.md")):
        check_mermaid(md)
    if ADR_DIR.exists():
        check_adrs()
    for p in problems:
        print(p)
    print(f"\n{len(problems)} problem(s).")
    return 1 if problems and "--warn-only" not in sys.argv else 0


if __name__ == "__main__":
    sys.exit(main())
