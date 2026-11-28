"""Print the source excerpts one subtask needs, from the task's context pack, without a model.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/ctx_pack.py" SUBTASK-ID [--part N]
Reads the subtask file and `context.md` (table "Nguồn cần đọc": File | Dòng/mục | Vì sao | Ai).
Rows whose "Ai" names the subtask (`S02`, a range `S01–S05`, `mọi vai`, or empty) are printed with
line numbers. Acceptance-criteria lines are narrowed to those on the subtask's "Phụ trách:" line.
Output is split into parts below the tool-output limit. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import close_task as ct  # noqa: E402

PART_CHARS = 28_000
ALIAS = re.compile(r"`(\w+)`\s*=\s*(?:\[[^\]]*\]\()?`?([\w./-]+\.\w+)")
RANGE = re.compile(r"(?<![\w.-])(\d+)\s*[–-]\s*(\d+)(?![\w.])")
AC_LINE = re.compile(r"^\W*(?:\[[ x]\]\s*)?\**([A-Z]\w*)-AC(\d+)\b")
SUB_ID = re.compile(r"(E\d\d-T\d\d)-(S\d\d)")


# ---------- pure helpers (unit tested) ----------

def for_subtask(who: str, short: str) -> bool:
    """Does the "Ai" cell include subtask `short` (`S02`)? Cells naming only roles are included."""
    ranges = re.findall(r"S(\d\d)\s*(?:–|-|\.\.|…)\s*S(\d\d)", who)
    singles = re.findall(r"S(\d\d)", who)
    if not singles or "mọi vai" in who:
        return True
    n = int(short[1:])
    return any(int(a) <= n <= int(b) for a, b in ranges) or n in {int(s) for s in singles}


def owned_acs(subtask_text: str) -> set[tuple[str, int]]:
    """AC IDs on the "Phụ trách:" line; bare numbers after an ID share its prefix."""
    found: set[tuple[str, int]] = set()
    for line in subtask_text.splitlines():
        if "Phụ trách" not in line:
            continue
        plain = re.sub(r"\([^()]*\)", "", line.split("Phụ trách", 1)[1])
        prefix = None
        for m in re.finditer(r"([A-Z]\w*)-AC(\d+)|(?<![\w-])(\d+)(?![\w-])", plain):
            if m.group(1):
                prefix = m.group(1)
                found.add((prefix, int(m.group(2))))
            elif prefix:
                found.add((prefix, int(m.group(3))))
    return found


def source_rows(context: str, short: str) -> list[tuple[str, str, str]]:
    """(file cell, line/section cell, why) of the context rows meant for this subtask."""
    m = re.search(r"(?ms)^## Nguồn cần đọc[^\n]*\n(.*?)(?=^## |\Z)", context)
    rows = []
    for line in (m.group(1) if m else "").splitlines():
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 3 or cells[0] == "File":
            continue
        if len(cells) < 4 or for_subtask(cells[3], short):
            rows.append((cells[0], cells[1], cells[2]))
    return rows


def excerpt(lines: list[str], start: int, end: int, acs: set[tuple[str, int]]) -> list[str]:
    out, skipped = [], 0
    for num in range(max(start, 1), min(end, len(lines)) + 1):
        line = lines[num - 1]
        m = AC_LINE.match(line.lstrip("| "))
        if acs and m and (m.group(1), int(m.group(2))) not in acs:
            skipped += 1
            continue
        out.append(f"{num}: {line}")
    if skipped:
        out.append(f"(bỏ {skipped} dòng AC không thuộc subtask)")
    return out


def split_parts(blocks: list[str], limit: int = PART_CHARS) -> list[str]:
    """Group blocks into parts of at most `limit` characters, cutting oversized blocks at line ends."""
    parts, cur = [], ""
    for block in blocks:
        for line in block.splitlines(keepends=True):
            while len(line) > limit:
                if cur:
                    parts.append(cur)
                    cur = ""
                parts.append(line[:limit])
                line = line[limit:]
            if len(cur) + len(line) > limit:
                parts.append(cur)
                cur = ""
            cur += line
    if cur:
        parts.append(cur)
    return parts


# ---------- main ----------

def build(sub_id: str) -> list[str]:
    m = SUB_ID.fullmatch(sub_id)
    if not m:
        raise SystemExit(f"Dừng: `{sub_id}` không phải mã subtask (E0x-Tyy-Szz).")
    tdir = ct.find_task(m.group(1)).parent
    subs = sorted(tdir.glob(f"{sub_id}-*.md"))
    if len(subs) != 1:
        raise SystemExit(f"Dừng: tìm thấy {len(subs)} file cho {sub_id}.")
    sub_text = subs[0].read_text(encoding="utf-8")
    blocks = [f"=== {subs[0].relative_to(ct.REPO)}\n{sub_text}\n"]
    ctx = tdir / "context.md"
    if not ctx.is_file():
        return blocks + ["(task chưa có context.md: tự mở nguồn theo mục)\n"]
    context = ctx.read_text(encoding="utf-8")
    aliases = dict(ALIAS.findall(context))
    based_on = ct.frontmatter(context).get("based_on", "")
    for extra in ("Mục tiêu", "Quyết định liên quan", "Ràng buộc", "Câu hỏi mở"):
        sec = re.search(rf"(?ms)^## {extra}[^\n]*\n(.*?)(?=^## |\Z)", context)
        if sec and sec.group(1).strip():
            blocks.append(f"=== context.md § {extra}\n{sec.group(1).strip()}\n")
    acs = owned_acs(sub_text)
    manual = []
    for name_cell, where, why in source_rows(context, m.group(2)):
        name = name_cell.strip("` ")
        rel = aliases.get(name, name)
        path = ct.REPO / rel
        ranges = RANGE.findall(where)
        if not path.is_file() or not ranges:
            manual.append(f"- {rel}: {where} ({why})")
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        stale = ""
        if based_on and ct.sh("git", "diff", "--quiet", based_on, "--", rel, check=False).returncode == 1:
            stale = f" [CẢNH BÁO: file đã đổi từ {based_on}, kiểm lại số dòng]"
        for a, b in ranges:
            body = "\n".join(excerpt(lines, int(a), int(b), acs))
            blocks.append(f"=== {rel} dòng {a}–{b} ({why}){stale}\n{body}\n")
    if manual:
        blocks.append("=== Mở tay khi cần (không có số dòng)\n" + "\n".join(manual) + "\n")
    return blocks


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ctx_pack.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subtask_id")
    parser.add_argument("--part", type=int, default=1)
    args = parser.parse_args(argv)
    parts = split_parts(build(args.subtask_id))
    if not 1 <= args.part <= len(parts):
        print(f"Dừng: chỉ có {len(parts)} phần.")
        return 2
    sys.stdout.write(parts[args.part - 1])
    if args.part < len(parts):
        print(f"\n=== phần {args.part}/{len(parts)}: chạy tiếp với --part {args.part + 1} (lệnh riêng, không gộp)")
    else:
        print(f"\n=== hết ({len(parts)} phần)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
