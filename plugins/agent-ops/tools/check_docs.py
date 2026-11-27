"""Consistency checks over management/ and docs/ markdown. Stdlib only; called by build_inbox.py --check.

- relative links must point to an existing file or directory, and `#anchor` to an existing heading (GitHub slug rules);
- BOARD.md must equal the regenerated text (see build_board.py);
- warning: a line `> Trạng thái: đề xuất (DR-xxx)` while that ticket is already `decided`;
- warning: an item of the inbox "Việc bạn cần làm" (manual) section whose tasks are all `done`, that names an unknown
  task, or that names no task at all (allowed only with the marker `(không task)`).

- error : a passage of >= 12 words shared by >= 2 files of `[check_docs] dup_scope` in
  `.agent-ops.toml` (first entry a file, the rest directories; default `CLAUDE.md`, `.claude/skills/`; copies break the single-source rule). Compared with a sliding 12-word window over
  normalized words (sentence punctuation, `->`, bold/italic/code markers, bullets and case ignored), so differently cut
  sentences still match; adjacent windows merge into one passage. Known passages live in `[[check_docs.dup_allowlist]]`, keyed by
  (file pair, first 12 words), kind `có chủ đích` or `nợ` (`nợ` names the cleanup task and deadline); an entry that matches
  nothing is an error too, so editing the start of a passage or cleaning it forces the entry to be updated or removed.

Links inside fenced code blocks, inline code and HTML comments are ignored; http(s)/mailto/other schemes are ignored.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import is_moved, load_config, mgmt_rel  # noqa: E402

# Defaults; override per project in `.agent-ops.toml` [check_docs] scan_dirs / dup_scope / dup_allowlist.
SCAN_DIRS = ("management", "docs")  # first entry is replaced by the configured management dir
LINK_RE = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^ {0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$")
HTML_ANCHOR_RE = re.compile(r"""<a\s[^>]*?(?:name|id)=["']([^"']+)["']""", re.I)
PROPOSAL_RE = re.compile(r"^> Trạng thái: đề xuất \((DR-\d+(?:[,\s]+DR-\d+)*)\)")
DR_ID_RE = re.compile(r"DR-\d+")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
TASK_ID_RE = re.compile(r"(?<![\w-])(E\d{2}-T\d{2})(?![\d])")
MANUAL_START, MANUAL_END = "<!-- manual:start -->", "<!-- manual:end -->"
NO_TASK_MARK = "(không task)"
CLOSED_TASK_STATUSES = {"done"}

DUP_SCOPE = ("CLAUDE.md", ".claude/skills")  # first entry: a single file; the others: directories
DUP_MIN_WORDS = 12
MARKUP_RE = re.compile(r"[*_`~]+|^\s*(?:[-+>]|\d+[.)])\s+|\[([^\]]*)\]\([^)]*\)")
PUNCT_RE = re.compile(r"[.!?;:,→]+")
KIND_INTENTIONAL, KIND_DEBT = "có chủ đích", "nợ"
# Passages shared on purpose or still owed, keyed by (file pair, first 12 words). Generated with find_duplicate_passages();
# Entries should only be removed over time, never added. `nợ` entries name the cleanup task and deadline.
def _load_sibling(name: str):
    """Import a sibling tool by path: `python -I` drops the script directory from sys.path."""
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def slug(heading: str) -> str:
    """GitHub-style anchor: lowercase, drop punctuation (keeps letters incl. Vietnamese, digits, `_`, `-`), spaces to `-`."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # [text](url) -> text
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def visible_lines(text: str) -> list[tuple[int, str]]:
    """(line number, line) outside fenced code blocks and HTML comments; hidden lines are skipped, numbering kept."""
    result: list[tuple[int, str]] = []
    fence = ""
    in_comment = False
    for no, line in enumerate(text.splitlines(), 1):
        m = FENCE_RE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = ""
            continue
        if m:
            fence = m.group(1)
            continue
        if in_comment:
            if "-->" in line:
                in_comment, line = False, line.split("-->", 1)[1]
            else:
                continue
        line = re.sub(r"<!--.*?-->", "", line)
        if "<!--" in line:
            in_comment, line = True, line.split("<!--", 1)[0]
        result.append((no, line))
    return result


def anchors_of(text: str) -> set[str]:
    """All valid `#anchor` targets of a document, with GitHub's `-1`, `-2` suffix for repeated headings."""
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    for _, line in visible_lines(text):
        anchors.update(HTML_ANCHOR_RE.findall(line))
        m = HEADING_RE.match(line)
        if m:
            base = slug(m.group(1))
            n = seen.get(base, 0)
            seen[base] = n + 1
            anchors.add(base if n == 0 else f"{base}-{n}")
    return anchors


def scan_dirs(root: Path) -> list[str]:
    cfg = load_config(root).get("check_docs", {}).get("scan_dirs")
    return list(cfg) if cfg else [mgmt_rel(root), *SCAN_DIRS[1:]]


def dup_scope(root: Path) -> list[str]:
    return list(load_config(root).get("check_docs", {}).get("dup_scope") or DUP_SCOPE)


def dup_allowlist(root: Path) -> list[dict]:
    """Entries of `[[check_docs.dup_allowlist]]`: files (2 paths), start, kind, reason (+ task, deadline for debt)."""
    return [{**e, "files": tuple(e.get("files", ()))} for e in load_config(root).get("check_docs", {}).get("dup_allowlist", [])]


def markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for d in scan_dirs(root):
        files += sorted((root / d).glob("**/*.md"))
    return files


def check_links(root: Path, files: list[Path] | None = None) -> list[str]:
    """Broken relative links as `path:line: message`."""
    problems: list[str] = []
    cache: dict[Path, set[str]] = {}
    for path in files if files is not None else markdown_files(root):
        rel = path.relative_to(root).as_posix()
        for no, line in visible_lines(path.read_text(encoding="utf-8")):
            for target in LINK_RE.findall(INLINE_CODE_RE.sub("", line)):
                msg = _link_problem(path, target, cache)
                if msg:
                    problems.append(f"{rel}:{no}: {msg}: {target}")
    return problems


def _link_problem(path: Path, target: str, cache: dict[Path, set[str]]) -> str | None:
    if SCHEME_RE.match(target) or target.startswith("/"):
        return None
    file_part, _, anchor = unquote(target).partition("#")
    dest = (path.parent / file_part).resolve() if file_part else path
    if not dest.exists():
        return None if is_moved(dest) else "link hỏng, không có file"
    if anchor and dest.is_file() and dest.suffix == ".md":
        if dest not in cache:
            cache[dest] = anchors_of(dest.read_text(encoding="utf-8"))
        if anchor.lower() not in cache[dest]:
            return "link hỏng, không có mục"
    return None


def check_board(root: Path) -> list[str]:
    msg = _load_sibling("build_board").board_mismatch(root)
    return [f"{mgmt_rel(root)}/BOARD.md: {msg}"] if msg else []


def dr_statuses(root: Path) -> dict[str, str]:
    board = _load_sibling("build_board")
    result: dict[str, str] = {}
    for path in sorted((root / mgmt_rel(root) / "decision-requests").glob("DR-*.md")):
        meta = board.read_frontmatter(path)
        result[meta.get("id") or path.stem.split("-", 2)[0] + "-" + path.stem.split("-", 2)[1]] = meta.get("status", "")
    return result


def check_stale_proposals(root: Path, files: list[Path] | None = None) -> list[str]:
    """Warnings for `> Trạng thái: đề xuất (DR-xxx)` lines whose ticket is already `decided`."""
    statuses = dr_statuses(root)
    warnings: list[str] = []
    for path in files if files is not None else markdown_files(root):
        rel = path.relative_to(root).as_posix()
        for no, line in visible_lines(path.read_text(encoding="utf-8")):
            m = PROPOSAL_RE.match(line)
            for dr in DR_ID_RE.findall(m.group(1)) if m else []:
                if statuses.get(dr) == "decided":
                    warnings.append(f"{rel}:{no}: ghi 'đề xuất ({dr})' nhưng {dr} đã decided; cập nhật dòng Trạng thái")
    return warnings


def manual_items(inbox_text: str) -> list[tuple[int, str]]:
    """Top-level bullets of the inbox manual section as (1-based line of the bullet, text incl. continuation lines)."""
    if MANUAL_START not in inbox_text or MANUAL_END not in inbox_text:
        return []
    head, rest = inbox_text.split(MANUAL_START, 1)
    body = rest.split(MANUAL_END, 1)[0]
    first = head.count("\n") + 1  # line of the start marker; body line i is at first + i
    items: list[tuple[int, str]] = []
    for i, line in enumerate(body.split("\n")):
        if line.startswith("- "):
            items.append((first + i, line))
        elif items and line.strip():
            items[-1] = (items[-1][0], items[-1][1] + "\n" + line)
    return [(no, text) for no, text in items if text.strip() not in ("- —", "- -")]


def check_manual_actions(root: Path) -> list[str]:
    """Warnings for stale PO action items: every named task is done, a task id is unknown, or no task is named."""
    inbox = root / mgmt_rel(root) / "DECISIONS-INBOX.md"
    if not inbox.exists():
        return []
    statuses = {t["id"]: t.get("status", "") for t in _load_sibling("build_board").load_tasks(root)}
    rel = inbox.relative_to(root).as_posix()
    warnings: list[str] = []
    for no, text in manual_items(inbox.read_text(encoding="utf-8")):
        if NO_TASK_MARK in text:  # PO action not tracked by any task: skipped on purpose
            continue
        ids = sorted(set(TASK_ID_RE.findall(text)))
        if not ids:
            warnings.append(f"{rel}:{no}: việc của PO không gắn mã task (Exx-Tyy); thêm mã task hoặc ghi '{NO_TASK_MARK}'")
            continue
        unknown = [i for i in ids if i not in statuses]
        if unknown:
            warnings.append(f"{rel}:{no}: việc của PO trỏ tới task không tồn tại: {', '.join(unknown)}")
        known = [i for i in ids if i in statuses]
        if known and not unknown and all(statuses[i] in CLOSED_TASK_STATUSES for i in known):
            warnings.append(f"{rel}:{no}: việc của PO trỏ tới task đã done ({', '.join(known)}); xoá việc hoặc cập nhật")
    return warnings


def normalize_sentence(raw: str) -> str:
    """Lowercase, markdown markers/bullets/link targets removed, whitespace collapsed."""
    text = MARKUP_RE.sub(lambda m: m.group(1) or "", raw)
    return " ".join(text.lower().split())


def segments_of(text: str) -> list[list[str]]:
    """Word lists (lowercase, no markup, no sentence punctuation) per visible line and per table cell."""
    result: list[list[str]] = []
    for _, line in visible_lines(text):
        for cell in line.split("|"):
            words = PUNCT_RE.sub(" ", normalize_sentence(cell)).split()
            if words:
                result.append(words)
    return result


def passages_of(text: str) -> dict[str, int]:
    """Passages of >= DUP_MIN_WORDS words as {first window (12 words): word count}; adjacent windows merge into one passage.

    Windows ignore sentence boundaries, so the same text cut into different sentences is still one passage.
    """
    return {" ".join(words[i : i + DUP_MIN_WORDS]): n for words, i, n in _runs(text, None)}


def _windows(text: str) -> dict[str, tuple[int, int]]:
    """Every 12-word window as {window: (segment index, start index)} (first occurrence)."""
    found: dict[str, tuple[int, int]] = {}
    for seg_no, words in enumerate(segments_of(text)):
        for i in range(len(words) - DUP_MIN_WORDS + 1):
            found.setdefault(" ".join(words[i : i + DUP_MIN_WORDS]), (seg_no, i))
    return found


def _runs(text: str, other: set[str] | None) -> list[tuple[list[str], int, int]]:
    """Maximal runs of consecutive windows (all windows when `other` is None, else only those in `other`) as (words, start, length)."""
    runs: list[tuple[list[str], int, int]] = []
    for words in segments_of(text):
        start = None
        for i in range(len(words) - DUP_MIN_WORDS + 1):
            hit = other is None or " ".join(words[i : i + DUP_MIN_WORDS]) in other
            if hit and start is None:
                start = i
            if not hit and start is not None:
                runs.append((words, start, i - 1 - start + DUP_MIN_WORDS))
                start = None
        if start is not None:
            runs.append((words, start, len(words) - start))
    return runs


def dup_scope_files(root: Path) -> list[Path]:
    scope = dup_scope(root)
    files = [root / scope[0]] if scope and (root / scope[0]).exists() else []
    for d in scope[1:]:
        files += sorted((root / d).glob("**/*.md"))
    return files


def find_duplicate_passages(root: Path) -> list[tuple[tuple[str, str], str, int]]:
    """Shared passages as ((file A, file B) sorted, first 12 words of the passage in file A, word count), for every file pair."""
    texts = {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in dup_scope_files(root)}
    windows = {rel: set(_windows(t)) for rel, t in texts.items()}
    found: list[tuple[tuple[str, str], str, int]] = []
    names = sorted(texts)
    for ai, a in enumerate(names):
        for b in names[ai + 1 :]:
            shared = windows[a] & windows[b]
            for words, start, length in _runs(texts[a], shared):
                found.append(((a, b), " ".join(words[start : start + DUP_MIN_WORDS]), length))
    return found


def duplicate_entry_keys(entries: list[dict[str, str | tuple[str, str]]]) -> set[tuple[tuple[str, str], str]]:
    return {(tuple(sorted(e["files"])), normalize_start(str(e["start"]))) for e in entries}  # type: ignore[arg-type]


def normalize_start(start: str) -> str:
    return " ".join(PUNCT_RE.sub(" ", normalize_sentence(start)).split()[:DUP_MIN_WORDS])


def check_duplicate_sentences(root: Path, allowlist: list[dict[str, str | tuple[str, str]]] | None = None) -> list[str]:
    """Errors for passages of >= 12 words shared by >= 2 files of the rule-doc scope (sliding window).

    An allowlist entry (files + start of passage) silences one passage; an entry that matches nothing is an error too
    (the passage was edited or cleaned: update or delete the entry).
    """
    entries = dup_allowlist(root) if allowlist is None else allowlist
    allowed = duplicate_entry_keys(entries)
    seen: set[tuple[tuple[str, str], str]] = set()
    errors: list[str] = []
    for files, start, length in find_duplicate_passages(root):
        key = (files, start)
        seen.add(key)
        if key not in allowed:
            errors.append(
                f"{files[0]}: đoạn {length} từ trùng ở {files[0]} và {files[1]} (chép lại thay vì link tới file chủ): {start}..."
            )
    for files, start in sorted(allowed - seen):
        if not all((root / f).exists() for f in files):  # other repo (tests, partial checkout): nothing to compare
            continue
        errors.append(f"{files[0]}: mục trong danh sách bỏ qua không còn khớp đoạn nào (đã sửa/đã dọn; cập nhật hoặc xoá mục): {files[1]} | {start}...")
    return errors


def run(root: Path) -> tuple[list[str], list[str]]:
    """(errors, warnings) of every docs check."""
    files = markdown_files(root)
    return check_links(root, files) + check_board(root) + check_duplicate_sentences(root), check_stale_proposals(root, files) + check_manual_actions(root)
