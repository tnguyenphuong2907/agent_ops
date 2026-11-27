"""Collect review / QA / DR-critique findings for the weekly retro.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/retro_stats.py"                    # summary (markdown) to stdout
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/retro_stats.py" --since 2026-11-02 # only items anchored on/after date
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/retro_stats.py" --dump findings.csv  # every finding, for classification

A "finding" is a row of any markdown table whose header has a "Mức độ" column
(review tables in task.md section 4/5, critique tables in DR section 7).
Category comes from a "Nhóm" column if present (codes in <management>/lessons/README.md),
otherwise "?" (unclassified). Standard library only.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import mgmt_rel, project_root  # noqa: E402

ROOT = project_root()
SEVERITIES = ("Blocker", "Major", "Minor", "Nit")
SOURCES = [("task", f"{mgmt_rel(ROOT)}/tasks/**/task.md"), ("dr", f"{mgmt_rel(ROOT)}/decision-requests/DR-*.md")]


def frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.split("#", 1)[0].strip().strip('"')
    return out


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def tables(text: str):
    """Yield (header_cells, rows) for each table having a 'Mức độ' column."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and "Mức độ" in lines[i] and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = cells(lines[i])
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            yield head, rows
            i = j
        else:
            i += 1


def number(v: str):
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)", v or "")
    return float(m.group(1)) if m else None


def collect(since: str | None):
    findings, items = [], []
    for kind, pattern in SOURCES:
        for path in sorted(ROOT.glob(pattern)):
            text = path.read_text(encoding="utf-8")
            fm = frontmatter(text)
            anchor = fm.get("planned_date") or fm.get("created") or ""
            if since and anchor and anchor < since:
                continue
            item = {
                "kind": kind, "id": fm.get("id", path.stem), "path": path.relative_to(ROOT).as_posix(),
                "owner": fm.get("assignee") if kind == "task" else fm.get("proposal_by", "architect"),
                "anchor": anchor, "rounds": 0, "first_pass": None,
                "estimate": number(fm.get("estimate_hours", "")), "actual": number(fm.get("actual_hours", "")),
            }
            for n, (head, rows) in enumerate(tables(text)):
                sev_i = next(k for k, h in enumerate(head) if "Mức độ" in h)
                cat_i = next((k for k, h in enumerate(head) if h.startswith("Nhóm")), None)
                round_sev = []
                for r in rows:
                    if sev_i >= len(r):
                        continue
                    sev = next((s for s in SEVERITIES if s.lower() in r[sev_i].lower()), None)
                    if not sev:
                        continue
                    round_sev.append(sev)
                    note = max(r, key=len)
                    findings.append({
                        "item": item["id"], "kind": kind, "owner": item["owner"], "round": n + 1,
                        "severity": sev, "category": (r[cat_i] if cat_i is not None and cat_i < len(r) and r[cat_i] else "?"),
                        "note": re.sub(r"\s+", " ", note)[:300], "path": item["path"],
                    })
                if round_sev:
                    item["rounds"] += 1
                    if item["first_pass"] is None:
                        item["first_pass"] = not any(s in ("Blocker", "Major") for s in round_sev)
            items.append(item)
    return findings, items


def summary(findings, items) -> str:
    out = ["## Số liệu tự động (retro_stats.py)", ""]
    reviewed = [i for i in items if i["first_pass"] is not None]
    out.append(f"- Hạng mục có review: **{len(reviewed)}** (task + DR) · tổng nhận xét: **{len(findings)}**")
    sev = Counter(f["severity"] for f in findings)
    out.append("- Theo mức độ: " + ", ".join(f"{s} {sev.get(s, 0)}" for s in SEVERITIES))
    cat = Counter(f["category"] for f in findings if f["severity"] in ("Blocker", "Major"))
    out.append("- Blocker/Major theo nhóm: " + (", ".join(f"`{k}` {v}" for k, v in cat.most_common()) or "—"))
    out += ["", "### Theo người làm", "", "| Người làm | Hạng mục | Đạt ngay vòng 1 | Vòng review TB | Blocker+Major | Thực tế/Ước lượng |", "|---|---|---|---|---|---|"]
    by_owner = defaultdict(list)
    for i in reviewed:
        by_owner[i["owner"]].append(i)
    for owner, its in sorted(by_owner.items()):
        fp = sum(1 for i in its if i["first_pass"])
        rounds = sum(i["rounds"] for i in its) / len(its)
        bm = sum(1 for f in findings if f["owner"] == owner and f["severity"] in ("Blocker", "Major"))
        pairs = [(i["actual"], i["estimate"]) for i in its if i["actual"] and i["estimate"]]
        ratio = f"{sum(a for a, _ in pairs) / sum(e for _, e in pairs):.2f} ({len(pairs)} task)" if pairs else "không đủ dữ liệu"
        out.append(f"| {owner} | {len(its)} | {fp}/{len(its)} | {rounds:.1f} | {bm} | {ratio} |")
    missing_actual = [i["id"] for i in items if i["kind"] == "task" and i["estimate"] and not i["actual"]]
    if missing_actual:
        out += ["", f"- Task có ước lượng nhưng **thiếu giờ thực tế**: {', '.join(missing_actual)}"]
    unclassified = sum(1 for f in findings if f["category"] == "?")
    if unclassified:
        out.append(f"- Nhận xét **chưa gắn nhóm lỗi**: {unclassified} (dùng `--dump` để phân loại khi retro)")
    return "\n".join(out) + "\n"


def main() -> int:
    args = sys.argv[1:]
    since = args[args.index("--since") + 1] if "--since" in args else None
    findings, items = collect(since)
    if "--dump" in args:
        dest = Path(args[args.index("--dump") + 1])
        with dest.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(findings[0].keys()) if findings else ["item"])
            w.writeheader()
            w.writerows(findings)
        print(f"Đã ghi {len(findings)} nhận xét vào {dest}")
        return 0
    sys.stdout.write(summary(findings, items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
