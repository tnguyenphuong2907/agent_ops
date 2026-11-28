"""Print one section of a task, without reading the whole file.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/task_section.py" TASK-ID SECTION [--part N]
SECTION: a number (`4`; 7 and 8 come from log.md when it exists), `contract` (contract.md),
or part of a `##`/`###` heading of task.md or contract.md. Lines are numbered; long output is split
below the tool-output limit. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import close_task as ct  # noqa: E402
import ctx_pack  # noqa: E402


def find_sections(text: str, wanted: str) -> list[tuple[int, int]]:
    """(first, last) line numbers of the headings matching `wanted`, each with its subsections."""
    lines = text.splitlines()
    heads = [(i, len(m.group(1)), m.group(2)) for i, l in enumerate(lines, 1) if (m := re.match(r"(##+) (.*)", l))]
    found = []
    for n, (start, level, title) in enumerate(heads):
        if wanted.isdigit():
            hit = level == 2 and bool(re.match(rf"(?:{wanted}\.|[\d., ]*·\s*{wanted}\.)", title)
                                      or re.search(rf"(?:^|·\s*){wanted}\.", title))
        else:
            hit = wanted.casefold() in title.casefold()
        if hit and not (found and start <= found[-1][1]):
            end = next((s - 1 for s, lv, _ in heads[n + 1:] if lv <= level), len(lines))
            found.append((start, end))
    return found


def blocks(tdir: Path, wanted: str) -> list[str]:
    log_md, contract = tdir / "log.md", tdir / "contract.md"
    if wanted == "contract":
        files = [(contract, None)]
    elif wanted in ("7", "8") and log_md.is_file():
        files = [(log_md, wanted)]
    elif wanted.isdigit():
        files = [(tdir / "task.md", wanted)]
    else:
        files = [(tdir / "task.md", wanted), (contract, wanted)]
    out = []
    for path, key in files:
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        spans = [(1, len(lines))] if key is None else find_sections("\n".join(lines), key)
        for a, b in spans:
            body = "\n".join(f"{i}: {lines[i - 1]}" for i in range(a, b + 1))
            out.append(f"=== {path.name} dòng {a}–{b}\n{body}\n")
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="task_section.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_id")
    parser.add_argument("section")
    parser.add_argument("--part", type=int, default=1)
    args = parser.parse_args(argv)
    tdir = ct.find_task(args.task_id).parent
    found = blocks(tdir, args.section)
    if not found:
        print(f"Dừng: không thấy mục `{args.section}` của {args.task_id}.")
        return 1
    parts = ctx_pack.split_parts(found)
    if not 1 <= args.part <= len(parts):
        print(f"Dừng: chỉ có {len(parts)} phần.")
        return 2
    sys.stdout.write(parts[args.part - 1])
    if args.part < len(parts):
        print(f"\n=== phần {args.part}/{len(parts)}: chạy tiếp với --part {args.part + 1} (lệnh riêng, không gộp)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
