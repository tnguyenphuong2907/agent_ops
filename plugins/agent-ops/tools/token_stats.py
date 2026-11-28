"""Token usage of subagent runs, from local Claude Code transcripts, for /retro.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/token_stats.py"                     # per-agent summary (markdown) to stdout
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/token_stats.py" --since 2026-11-20  # only runs started on/after date
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/token_stats.py" --by task           # group by task ID (E01-T02) found in the brief
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/token_stats.py" --transcripts DIR   # another transcripts dir (default: this repo's)
    python3 "${CLAUDE_PLUGIN_ROOT}/tools/token_stats.py" --session last
        # one main session (ID prefix, or `last` = newest with subagents): run by run and per model,
        # in weighted tokens (base input units, 1 hour cache write x2; not money)

Reads `<transcripts>/<session>/subagents/agent-*.jsonl` (+ `.meta.json` for agent type and model).
One API response can span several transcript lines, so usage is counted once per message id.
Context-fill metrics: tokens of tool output from reading task.md (Read or cat/sed/head/tail in Bash),
from grep, and count of CLAUDE.md re-reads; tokens estimated as characters / 4.
Main session: `<transcripts>/*.jsonl`; per-call context, share of calls and of context tokens above
MAIN_CTX_LIMIT (the ctx_guard.py hook threshold).
Cost share uses prices relative to base input: cache read x0.1, cache write x1.25, output x5
(same weights for every model; a rough split, not a bill). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import project_root  # noqa: E402

ROOT = project_root()
WEIGHTS = {"cache_read": 0.1, "cache_write": 1.25, "output": 5.0}
WRITE_1H_EXTRA = 0.75  # a 1 hour cache write costs x2, i.e. 0.75 more than the 5 minute one
TASK_RE = re.compile(r"\bE\d{2}-T\d{2}\b")
DR_RE = re.compile(r"\bDR-\d{3}\b")
TASK_READ_RE = re.compile(r"\b(cat|sed|head|tail|nl|awk|less|git show)\b[^|;&>]*task\.md")  # stops at ">": writes are not reads
SED_INPLACE_RE = re.compile(r"\bsed\s+(-\w*\s+)*-i")
GREP_RE = re.compile(r"(^|[|;&(]\s*)(grep|rg)\b")
CLAUDE_MD_RE = re.compile(r"\b(cat|sed|head|tail|nl|less)\b[^|;&]*CLAUDE\.md")
CHARS_PER_TOKEN = 4
MAIN_CTX_LIMIT = 150_000
BIG_OUTPUT_CHARS = 30_000  # above this a tool result is truncated or floods the context


def tool_kind(name: str, inp: dict) -> str | None:
    """Which context-fill bucket a tool call belongs to (None = not tracked)."""
    if name == "Read":
        path = str(inp.get("file_path", ""))
        if path.endswith("/task.md") or path == "task.md":
            return "task_md"
        return "claude_md" if path.endswith("CLAUDE.md") else None
    if name == "Grep":
        return "grep"
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        m = TASK_READ_RE.search(cmd)
        if m and not SED_INPLACE_RE.search(m.group(0)):
            return "task_md"
        if CLAUDE_MD_RE.search(cmd):
            return "claude_md"
        if GREP_RE.search(cmd):
            return "grep"
    return None


def result_chars(block: dict) -> int:
    content = block.get("content")
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(c.get("text", "")) for c in content if isinstance(c, dict))
    return 0


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content if isinstance(content, str) else ""


def call_label(name: str, inp: dict) -> str:
    """Tool name plus the start of its command or file name."""
    arg = str(inp.get("command") or inp.get("file_path") or inp.get("pattern") or "")
    if inp.get("file_path"):
        arg = Path(arg).name
    arg = " ".join(arg.split()).replace("|", "\\|")
    return f"{name} {arg[:80]}".strip()


def default_transcripts() -> Path:
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))


def parse_run(path: Path) -> dict | None:
    """Summarise one subagent transcript; None if it has no API usage."""
    meta_path = path.with_name(path.name[: -len(".jsonl")] + ".meta.json")
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
    usage: dict[str, dict] = {}
    reads: dict[str, tuple[str, bool]] = {}
    kinds: dict[str, str] = {}
    fill = {"task_md": 0, "grep": 0}
    claude_md_reads = 0
    calls_made: dict[str, str] = {}
    errors: list[tuple[str, str]] = []
    big: list[tuple[str, int]] = []
    seen_results: set[str] = set()
    started, brief = "", ""
    used_models: Counter = Counter()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not started and rec.get("timestamp"):
            started = rec["timestamp"]
        msg = rec.get("message") or {}
        content = msg.get("content")
        if not brief and rec.get("type") == "user" and isinstance(content, str):
            brief = content
        if rec.get("type") == "assistant" and msg.get("id") and msg.get("usage"):
            if msg["id"] not in usage and msg.get("model"):
                used_models[msg["model"]] += 1
            usage[msg["id"]] = msg["usage"]
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    kind = tool_kind(block.get("name", ""), block.get("input") or {})
                    if kind == "claude_md":
                        claude_md_reads += 1
                    elif kind:
                        kinds[block.get("id", "")] = kind
                if block.get("type") == "tool_use":
                    calls_made[block.get("id", "")] = call_label(block.get("name", ""), block.get("input") or {})
                if block.get("type") == "tool_result" and block.get("tool_use_id") not in seen_results:
                    seen_results.add(block.get("tool_use_id"))
                    label = calls_made.get(block.get("tool_use_id"), "?")
                    if block.get("is_error"):
                        errors.append((label, result_text(block)[:120].replace("\n", " ")))
                    if result_chars(block) > BIG_OUTPUT_CHARS:
                        big.append((label, result_chars(block)))
                if block.get("type") == "tool_result" and block.get("tool_use_id") in kinds:
                    fill[kinds.pop(block["tool_use_id"])] += result_chars(block) // CHARS_PER_TOKEN
                if block.get("type") == "tool_use" and block.get("name") == "Read":
                    inp = block.get("input") or {}
                    full = "offset" not in inp and "limit" not in inp
                    reads[block.get("id", "")] = (Path(inp.get("file_path", "")).name, full)
    if not usage:
        return None
    ctx = [u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
           for u in usage.values()]
    tag = TASK_RE.search(brief) or DR_RE.search(brief) or TASK_RE.search(meta.get("description", ""))
    return {
        "agent": meta.get("agentType") or "?",
        "model": meta.get("model") or "default",
        "used_model": used_models.most_common(1)[0][0] if used_models else meta.get("model") or "?",
        "desc": meta.get("description") or "",
        "task": tag.group(0) if tag else "?",
        "date": started[:10],
        "started": started,
        "calls": len(usage),
        "first": ctx[0],
        "last": ctx[-1],
        "cache_read": sum(u.get("cache_read_input_tokens", 0) for u in usage.values()),
        "cache_write": sum(u.get("cache_creation_input_tokens", 0) for u in usage.values()),
        "write_1h": sum((u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) for u in usage.values()),
        "output": sum(u.get("output_tokens", 0) for u in usage.values()),
        "full_reads": Counter(name for name, full in reads.values() if full),
        "task_md": fill["task_md"],
        "grep": fill["grep"],
        "claude_md_reads": claude_md_reads,
        "errors": errors,
        "big": big,
    }


def collect(transcripts: Path, since: str | None) -> list[dict]:
    runs = []
    for path in sorted(transcripts.glob("*/subagents/*.jsonl")):
        run = parse_run(path)
        if run and (not since or run["date"] >= since):
            runs.append(run)
    return runs


def main_calls(path: Path) -> tuple[str, list[int], int]:
    """(start timestamp, context size per API call, output tokens) of one main-session transcript."""
    usage: dict[str, dict] = {}
    started = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not started and rec.get("timestamp"):
            started = rec["timestamp"]
        msg = rec.get("message") or {}
        if rec.get("type") == "assistant" and msg.get("id") and msg.get("usage"):
            usage[msg["id"]] = msg["usage"]
    ctx = [u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
           for u in usage.values()]
    return started, ctx, sum(u.get("output_tokens", 0) for u in usage.values())


def render_main(transcripts: Path, since: str | None) -> str:
    sessions = []
    for path in sorted(transcripts.glob("*.jsonl")):
        started, ctx, out = main_calls(path)
        if ctx and (not since or started[:10] >= since):
            sessions.append((ctx, out))
    if not sessions:
        return ""
    ctx = sorted(c for s, _ in sessions for c in s)
    big = [c for c in ctx if c > MAIN_CTX_LIMIT]
    return "\n".join([
        "", "## Phiên chính", "",
        f"- Phiên: {len(sessions)}; gọi model: {len(ctx)} (trung vị/phiên {statistics.median(len(s) for s, _ in sessions):g})",
        f"- Ngữ cảnh mỗi lần gọi: trung vị {int(statistics.median(ctx)):,}, p90 {ctx[int(len(ctx) * 0.9)]:,}, cao nhất {ctx[-1]:,}",
        f"- Gọi khi ngữ cảnh > {MAIN_CTX_LIMIT // 1000}K: {len(big) / len(ctx):.0%} số lần gọi, {sum(big) / sum(ctx):.0%} token ngữ cảnh",
        f"- Đầu ra: {sum(o for _, o in sessions):,}",
    ]) + "\n"


def weighted(run: dict) -> float:
    return sum(run[k] * w for k, w in WEIGHTS.items()) + run.get("write_1h", 0) * WRITE_1H_EXTRA


def find_session(transcripts: Path, wanted: str) -> Path | None:
    """Main transcript whose ID starts with `wanted`; `last` = newest one that ran subagents."""
    paths = list(transcripts.glob("*.jsonl"))
    if wanted == "last":
        paths = [p for p in paths if any((p.with_suffix("") / "subagents").glob("*.jsonl"))]
        return max(paths, key=lambda p: p.stat().st_mtime, default=None)
    hits = [p for p in paths if p.stem.startswith(wanted)]
    return hits[0] if len(hits) == 1 else None


def render_session(main_path: Path) -> str:
    main_run = parse_run(main_path)
    runs = [main_run | {"agent": "phiên chính", "desc": ""}] if main_run else []
    subs = [parse_run(p) for p in sorted((main_path.with_suffix("") / "subagents").glob("*.jsonl"))]
    runs += sorted((r for r in subs if r), key=lambda r: r["started"])
    if not runs:
        return "Phiên không có lần gọi model nào.\n"
    cost = sum(map(weighted, runs)) or 1
    out = [f"# Token phiên {main_path.stem[:8]}", "",
           f"- Lượt agent: {len(runs) - bool(main_run)}; gọi model: {sum(r['calls'] for r in runs)}",
           f"- Thô: đọc cache {sum(r['cache_read'] for r in runs):,} · ghi cache {sum(r['cache_write'] for r in runs):,} "
           f"· đầu ra {sum(r['output'] for r in runs):,}",
           f"- Quy đổi (đơn vị input, chưa nhân giá model): {cost / 1e6:.2f}M", "",
           "| lượt | việc | model | gọi | ngữ cảnh cuối | quy đổi | % |", "|---|---|---|---|---|---|---|"]
    out += [f"| {r['agent']} | {r['desc']} | {r['used_model']} | {r['calls']} | {r['last']:,} | "
            f"{weighted(r) / 1e6:.2f}M | {weighted(r) / cost:.0%} |" for r in runs]
    out += ["", "| model | gọi | quy đổi | % |", "|---|---|---|---|"]
    models: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        models[r["used_model"]].append(r)
    for name, rs in sorted(models.items(), key=lambda kv: -sum(map(weighted, kv[1]))):
        part = sum(map(weighted, rs))
        out.append(f"| {name} | {sum(r['calls'] for r in rs)} | {part / 1e6:.2f}M | {part / cost:.0%} |")
    out += ["", "| lượt | lỗi tool | output > 30K ký tự |", "|---|---|---|"]
    noisy = [(i, r) for i, r in enumerate(runs) if r["errors"] or r["big"]]
    out += [f"| {i}. {r['agent']} {r['desc']} | {len(r['errors'])} | {len(r['big'])} |" for i, r in noisy]
    if not noisy:
        out.append("| (không có) | 0 | 0 |")
    for i, r in noisy:
        out += ["", f"Lượt {i}:"]
        out += [f"- lỗi: `{label}`: {why}" for label, why in r["errors"][:5]]
        out += [f"- lớn: `{label}`: {n:,} ký tự" for label, n in sorted(r["big"], key=lambda x: -x[1])[:5]]
    return "\n".join(out) + "\n"


def render(runs: list[dict], by: str) -> str:
    if not runs:
        return "Không có lượt agent nào trong khoảng đã chọn.\n"
    total = {k: sum(r[k] for r in runs) for k in ("cache_read", "cache_write", "write_1h", "output")}
    cost = sum(weighted(r) for r in runs)
    out = [
        f"# Token theo {'agent' if by == 'agent' else 'task'}",
        "",
        f"- Lượt agent: {len(runs)}; gọi model: {sum(r['calls'] for r in runs)}",
        f"- Ngữ cảnh lượt đầu (trung vị): {int(statistics.median(r['first'] for r in runs)):,}; "
        f"lượt cuối: trung vị {int(statistics.median(r['last'] for r in runs)):,}, cao nhất {max(r['last'] for r in runs):,}",
        f"- Đọc cache {total['cache_read']:,} · ghi cache {total['cache_write']:,} (loại 1 giờ {total['write_1h']:,}) · đầu ra {total['output']:,}",
        "- Tỷ trọng chi phí ước tính: " + ", ".join(
            f"{name} {sum(r[k] for r in runs) * w / cost:.0%}"
            for k, w, name in (("cache_read", 0.1, "đọc cache"), ("cache_write", 1.25, "ghi cache"), ("output", 5.0, "đầu ra"))),
        f"- Ngữ cảnh do tool trả (ước tính): đọc `task.md` {sum(r['task_md'] for r in runs):,} "
        f"(trung vị/lượt {int(statistics.median(r['task_md'] for r in runs)):,}) · grep {sum(r['grep'] for r in runs):,} "
        f"(trung vị/lượt {int(statistics.median(r['grep'] for r in runs)):,}) · đọc lại `CLAUDE.md` {sum(r['claude_md_reads'] for r in runs)} lần",
        "",
        f"| {by} | lượt | gọi/lượt (tv) | ngữ cảnh cuối (tv) | cao nhất | đầu ra | task.md/lượt (tv) | tỷ trọng chi phí |",
        "|---|---|---|---|---|---|---|---|",
    ]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        groups[r[by]].append(r)
    for key, rs in sorted(groups.items(), key=lambda kv: -sum(weighted(r) for r in kv[1])):
        out.append(
            f"| {key} | {len(rs)} | {statistics.median(r['calls'] for r in rs):g} | "
            f"{int(statistics.median(r['last'] for r in rs)):,} | {max(r['last'] for r in rs):,} | "
            f"{sum(r['output'] for r in rs):,} | {int(statistics.median(r['task_md'] for r in rs)):,} | "
            f"{sum(weighted(r) for r in rs) / cost:.0%} |")
    reads: Counter = Counter()
    for r in runs:
        reads.update(r["full_reads"])
    if reads:
        out += ["", "File bị `Read` nguyên cả file nhiều nhất: " + ", ".join(f"`{n}` {c}" for n, c in reads.most_common(8))]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Token usage of subagent runs, for /retro.")
    ap.add_argument("--since", help="only runs started on/after YYYY-MM-DD")
    ap.add_argument("--by", choices=("agent", "task"), default="agent")
    ap.add_argument("--transcripts", type=Path, default=None, help="transcripts dir (default: this repo's)")
    ap.add_argument("--session", help="one session: ID prefix or `last`")
    args = ap.parse_args(argv)
    if args.since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since):
        ap.error("--since must be YYYY-MM-DD")
    transcripts = args.transcripts or default_transcripts()
    if not transcripts.is_dir():
        print(f"Không thấy thư mục transcript: {transcripts}", file=sys.stderr)
        return 1
    if args.session:
        path = find_session(transcripts, args.session)
        if not path:
            print(f"Không tìm được đúng một phiên cho `{args.session}`", file=sys.stderr)
            return 1
        sys.stdout.write(render_session(path))
        return 0
    sys.stdout.write(render(collect(transcripts, args.since), args.by))
    sys.stdout.write(render_main(transcripts, args.since))
    return 0


if __name__ == "__main__":
    sys.exit(main())
