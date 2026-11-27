"""Build management/DECISIONS-INBOX.md from management/decision-requests/DR-*.md.

Usage:
    python management/tools/build_inbox.py           # rebuild inbox
    python management/tools/build_inbox.py --check   # validate DRs + internal links, exit 1 on problems
    python management/tools/build_inbox.py --help    # usage; unknown flags exit 2 and write nothing

Only uses the standard library.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import is_moved, load_config, mgmt_dir, mgmt_rel, project_root  # noqa: E402

ROOT = project_root()
DR_DIR = mgmt_dir(ROOT) / "decision-requests"
INBOX = mgmt_dir(ROOT) / "DECISIONS-INBOX.md"
MANUAL_START, MANUAL_END = "<!-- manual:start -->", "<!-- manual:end -->"
DEFAULT_TOPICS = {
    "scope": "Phạm vi", "security": "Bảo mật", "cost": "Chi phí", "architecture": "Kiến trúc",
    "data": "Dữ liệu người dùng", "ops": "Vận hành", "ux": "Giao diện",
}
_INBOX_CONFIG = load_config(ROOT).get("inbox", {})
# `.agent-ops.toml` [inbox.topics] replaces the whole default list (key -> group title in the inbox).
TOPICS = {str(k).lower(): str(v) for k, v in _INBOX_CONFIG.get("topics", {}).items()} or dict(DEFAULT_TOPICS)
# [inbox] analyst_topics: DRs with one of these topics need a product-analyst opinion in section 5 (P6).
ANALYST_TOPICS = frozenset(str(t).lower() for t in _INBOX_CONFIG.get("analyst_topics", []))
DOSSIER_SINCE = "2026-11-07"  # phiếu tạo từ ngày này phải có mục 10 hồ sơ cho PO
# DRs for which the PO waived the section-7 reviewer conclusion (e.g. written before the rule).
# Only the error "chưa có kết luận phản biện (mục 7)" is waived, only for these ids; every other rule still applies.
# Per-project list: `.agent-ops.toml` [inbox] no_review_conclusion_exempt_ids = ["DR-<nnn>"].
NO_REVIEW_CONCLUSION_EXEMPT_IDS = frozenset(_INBOX_CONFIG.get("no_review_conclusion_exempt_ids", []))
LOOP_GUARDS_SINCE = "2026-11-07"  # R1, R2 apply to DRs created AFTER this date
VALID_STATUS = {"draft", "in_review", "open", "provisional", "decided", "withdrawn"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OPTION_RE = re.compile(r"^[A-Z][′'0-9]*$")
OPTION_COL_RE = re.compile(r"^([A-Z][′'0-9]*)(?=[.\s:)]|$)")
MAX_REVIEW_ROUNDS = 2
R1_LABELS = ("Bài toán gốc", "Ràng buộc bỏ được", "Phương án bỏ ràng buộc")
P_RULES_SINCE = "2026-11-05"  # P2, P4, P6: apply to DRs created AFTER this date, status not withdrawn
P_RULES_SKIP_STATUS = {"withdrawn"}  # draft IS checked: skill decision-requests has the architect run --check to zero before in_review
# Longest alternative first. A code is not matched when a word char follows it or a lowercase ASCII slug suffix
# (so ADR-0002-slug.md is not a code). A code right after "<digit>-" still counts, so D-001-D-002 yields both codes,
# but not right after a date: 2026-01-01-D-001 is a name, not a reference to D-001.
REF_CODE_RE = re.compile(r"(?:(?<![\w-])|(?<=\d-))(?<!\d{4}-\d{2}-\d{2}-)(?>E\d{2}-T\d{2}-S\d{2}|E\d{2}-T\d{2}|E\d{2}|ADR-\d{4}|D-\d{3})(?!\w|-[a-z])")
LINK_TARGET_RE = re.compile(r"(?<=\])\([^)\s]*\)")
EXTERNAL_URL_RE = re.compile(r"https?://[^\s)>\]]+")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
READ_LABEL_RE = re.compile(r"\[ngoài, đọc (\d{4}-\d{2}-\d{2})\]")  # S01 / skill decision-requests
REQUIRED_SECTIONS_AFTER_DRAFT = ["## 2.", "## 3.", "## 4.", "## 5.", "## 6."]
# Short-form DR (`form: short`), template templates/decision-request-short.md.
SHORT_REQUIRED_SECTIONS = ["## 1.", "## 2.", "## 3.", "## 4.", "## 5."]
SHORT_CONDITIONS = 5  # section 3 checklist: every box must be ticked once the ticket leaves draft
SHORT_ESCALATE = "⬆️"  # reviewer verdict: conditions not met, convert to a full DR
# A full-form type-2 DR must say why the short form does not fit. Applies to DRs created on/after this date.
WHY_NOT_SHORT_SINCE = "2026-11-11"
WHY_NOT_SHORT_RE = re.compile(r"^\*\*Vì sao không phiếu ngắn:\*\*[ \t]*(.*)$", re.M)


def _unquote(v: str) -> str:
    """Strip whitespace, then one matching pair of quotes at both ends (inner quotes are content)."""
    v = v.strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta: dict = {"_path": path, "_text": text}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            line = line.split("#", 1)[0].rstrip()
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            v = _unquote(v)
            if v.startswith("[") and v.endswith("]"):
                v = [_unquote(x) for x in v[1:-1].split(",") if x.strip()]
            meta[k.strip()] = v
    meta["_choice"] = _grab(text, r"\*\*Chọn:\s*(.+?)\*\*") or _grab(text, r"\*\*Chọn:\*\*\s*(.+)")
    meta["_short"] = _scalar(meta, "form") == "short"
    sec7 = _section(text, "## 5.", "## Lịch sử") if meta["_short"] else _section(text, "## 7.", "## 8.")
    meta["_review"] = _last(sec7, r"\*\*Kết luận:\*\*[ \t]*([^\n]+)")
    meta["_note"] = _last(sec7, r"\*\*Lời nhắn cho PO:\*\*[ \t]*([^\n]+)")
    sec10 = _section(text, "## 10.", "## Lịch sử")
    q = _last(sec10, r"\*\*Câu hỏi:\*\*[ \t]*([^\n]+)")
    meta["_dossier"] = bool(q) and not q.startswith("<")
    meta["_summary"] = _section_first_line(text, "## 2.")
    return meta


def _grab(text: str, pattern: str, flags: int = 0) -> str:
    m = re.search(pattern, text, flags)
    return re.sub(r"<!--.*?-->", "", m.group(1)).strip() if m else ""


def _section(text: str, head: str, nxt: str) -> str:
    i = text.find("\n" + head)
    if i < 0:
        return ""
    j = text.find("\n" + nxt, i + 1)
    return text[i: j if j > 0 else len(text)]


def _last(text: str, pattern: str) -> str:
    found = re.findall(pattern, text)
    return re.sub(r"<!--.*?-->", "", found[-1]).strip() if found else ""


def _section_first_line(text: str, head: str) -> str:
    i = text.find(head)
    if i < 0:
        return ""
    for line in text[i:].splitlines()[1:]:
        s = line.strip()
        if s.startswith("## "):
            break
        if s and not s.startswith("<") and not s.startswith(">"):
            return s[:160]
    return ""


def slug(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s, flags=re.U)
    return s.replace(" ", "-")


def check_links(meta: dict) -> list[str]:
    problems = []
    path: Path = meta["_path"]
    body = re.sub(r"`[^`\n]*`", "", meta["_text"])  # ignore links shown as code examples
    for target in re.findall(r"\]\(([^)\s]+)\)", body):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, anchor = target.partition("#")
        f = (path.parent / file_part).resolve() if file_part else path
        if not f.exists():
            if is_moved(f):
                continue
            problems.append(f"link hỏng: {target}")
            continue
        if anchor and f.suffix == ".md":
            heads = [slug(h) for h in re.findall(r"^#+\s+(.+)$", f.read_text(encoding="utf-8"), re.M)]
            if anchor.lower() not in heads:
                problems.append(f"không thấy mục #{anchor} trong {file_part or path.name}")
    return problems


def _scalar(meta: dict, key: str) -> str:
    """Frontmatter value as a stripped string; "" when absent or not a plain string (list etc.)."""
    v = meta.get(key, "")
    return v.strip() if isinstance(v, str) else ""


def topics_of(meta: dict) -> list[str]:
    """Normalized topics: lowercase, quotes and list form removed (`Learning`, `'learning'`, `[learning, ops]`)."""
    v = meta.get("topic", "")
    items = v if isinstance(v, list) else [v]
    return [t for x in items if isinstance(x, str) and (t := x.strip().strip("\"'").strip().lower())]


def check_frontmatter(meta: dict) -> list[str]:
    """Malformed `created`, `status`, `topic` become problems, never crashes in later rules."""
    p: list[str] = []
    created = meta.get("created")
    if created is not None:
        if not isinstance(created, str) or not DATE_RE.match(created.strip()):
            p.append(f"frontmatter created: phải là YYYY-MM-DD, đang là {created!r}")
        else:
            try:
                dt.date.fromisoformat(created.strip())
            except ValueError:
                p.append(f"frontmatter created: không phải ngày thật: {created!r}")
    status = meta.get("status", "")
    if not isinstance(status, str) or status not in VALID_STATUS:
        p.append(f"frontmatter status: không hợp lệ: {status!r}")
    if "id" not in meta or meta["id"] == "":
        p.append("frontmatter id: thiếu hoặc rỗng")
    for key in ("id", "type", "deadline"):
        if key in meta and not isinstance(meta[key], str):
            p.append(f"frontmatter {key}: phải là một giá trị đơn, đang là {meta[key]!r}")
    raw_topic = meta.get("topic")
    if raw_topic is None:
        p.append("frontmatter topic: thiếu")
    else:
        items = raw_topic if isinstance(raw_topic, list) else [raw_topic]
        topics = topics_of(meta)
        if not topics or len(topics) != len(items):
            p.append(f"frontmatter topic: rỗng hoặc sai dạng: {raw_topic!r}")
        for t in topics:
            if t not in TOPICS:
                p.append(f"frontmatter topic: không có trong danh sách ({', '.join(TOPICS)}): {t!r}")
    return p


def validate(meta: dict) -> list[str]:
    p = []
    st = meta.get("status", "")
    if st not in {"draft", "withdrawn"}:
        for sec in REQUIRED_SECTIONS_AFTER_DRAFT:
            if sec not in meta["_text"]:
                p.append(f"thiếu mục {sec}")
        if meta.get("type") not in {"1", "2"}:
            p.append("thiếu type (1|2)")
        if not meta["_choice"]:
            p.append("mục 4 chưa có dòng **Chọn: …**")
    exempt = meta.get("id") in NO_REVIEW_CONCLUSION_EXEMPT_IDS
    if st in {"open", "provisional", "decided"} and not exempt and (not meta["_review"] or meta["_review"].startswith("⏳")):
        p.append("chưa có kết luận phản biện (mục 7)")
    if st in {"provisional", "decided"} and not meta.get("decided_as"):
        p.append("thiếu decided_as (D-xxx)")
    if st == "provisional" and meta.get("type") == "1" and not meta["_review"].startswith("⬇️"):
        p.append("loại 1 chỉ được provisional khi reviewer kết luận ⬇️ (hạ loại)")
    if st in {"open", "provisional"} and (meta.get("created") or "") >= DOSSIER_SINCE and not meta["_dossier"]:
        p.append("mục 10 'Hồ sơ quyết định cho PO' chưa điền")
    if (st not in {"draft", "withdrawn"} and meta.get("type") == "2"
            and (meta.get("created") or "") >= WHY_NOT_SHORT_SINCE):
        m = WHY_NOT_SHORT_RE.search(_strip_code_and_comments(_section(meta["_text"], "## 4.", "## 5.")))
        if not m or not m.group(1).strip() or re.search(r"<[^>]*>", m.group(1)):
            p.append("loại 2 dùng phiếu đầy đủ: mục 4 thiếu dòng **Vì sao không phiếu ngắn:**")
    if (meta.get("created") or "") >= DOSSIER_SINCE and "Đồng ý có điều kiện" in meta["_review"]:
        p.append("kết luận 'Đồng ý có điều kiện' không còn dùng: chọn ✅ / 🔄 / ❓ / ⬇️")
    return p + check_links(meta)


def validate_short(meta: dict) -> list[str]:
    """Rules for a short-form DR. Only type 2; reviewer checks the conditions once (✅ or ⬆️); no section 10."""
    p: list[str] = []
    st, text = meta.get("status", ""), meta["_text"]
    if meta.get("type") != "2":
        p.append("phiếu ngắn chỉ dùng cho loại 2 (type: 2), kể cả siết nhất quán")
    if st not in {"draft", "withdrawn"}:
        for sec in SHORT_REQUIRED_SECTIONS:
            if "\n" + sec not in text:
                p.append(f"phiếu ngắn thiếu mục {sec}")
        if not meta["_choice"]:
            p.append("mục 2 chưa có dòng **Chọn: …**")
        sec3 = _strip_code_and_comments(_section(text, "## 3.", "## 4."))
        ticked = len(re.findall(r"^\s*- \[[xX]\]", sec3, re.M))
        if ticked < SHORT_CONDITIONS:
            p.append(f"mục 3: mới tích {ticked}/{SHORT_CONDITIONS} điều kiện; thiếu điều kiện nào thì dùng phiếu đầy đủ")
    review = meta["_review"]
    if st == "open":
        p.append("phiếu ngắn không chuyển open: ✅ → provisional; ⬆️ → chuyển sang phiếu đầy đủ (bỏ form: short)")
    if st in {"provisional", "decided"} and (not review or review.startswith("⏳")):
        p.append("chưa có kết luận kiểm nhanh (mục 5)")
    if st in {"provisional", "decided"} and review.startswith(SHORT_ESCALATE):
        p.append("reviewer kết luận ⬆️: phải chuyển sang phiếu đầy đủ, không áp dụng tạm")
    if st in {"provisional", "decided"} and not meta.get("decided_as"):
        p.append("thiếu decided_as (D-xxx)")
    return p + check_links(meta)


def _strip_code_and_comments(text: str) -> str:
    """Drop fenced code blocks and HTML comments so template examples are not counted."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def review_rounds(text: str) -> int:
    """R2: max (never sum) of the three round counters."""
    sec7 = _strip_code_and_comments(_section(text, "## 7.", "## 8."))
    sec9 = _strip_code_and_comments(_section(text, "## 9.", "## 10."))
    history = text.split("\n## Lịch sử", 1)[1] if "\n## Lịch sử" in text else ""
    headings = [h for h in re.findall(r"^### Vòng \d+.*$", sec7, re.M) if "YYYY" not in h]
    answers = re.findall(r"Trả lời \(decision-reviewer", sec9)
    rows = [r for r in history.splitlines() if r.startswith("|")]
    reviewer_rows = [r for r in rows if len(r.split("|")) > 3 and "decision-reviewer" in r.split("|")[2]]
    return max(len(headings), len(answers), len(reviewer_rows))


def check_loop_guards(meta: dict) -> list[str]:
    """R1 (section 3 opening lines) and R2 (round ceiling). Only for DRs created since LOOP_GUARDS_SINCE."""
    created = _scalar(meta, "created")
    if not DATE_RE.match(created):
        return ["created thiếu hoặc sai dạng YYYY-MM-DD: không xác định được có áp R1, R2 hay không"]
    if created <= LOOP_GUARDS_SINCE:
        return []
    text, p = meta["_text"], []
    sec3 = _section(text, "## 3.", "## 4.")
    values: dict[str, str] = {}
    for label in R1_LABELS:
        m = re.search(rf"^\*\*{label}:\*\*[ \t]*(.*)$", sec3, re.M)
        if not m:
            p.append(f"R1: mục 3 thiếu dòng **{label}:**")
            continue
        values[label] = m.group(1).strip()
        if not values[label] or re.search(r"<[^>]*>", values[label]):
            p.append(f"R1: dòng **{label}:** để trống hoặc còn <…>")
    raw = values.get(R1_LABELS[2], "")
    if raw and not re.search(r"<[^>]*>", raw):
        letter = raw.strip("*` .")
        header = next((r for r in sec3.splitlines() if r.startswith("|")), "")
        cols = {m.group(1) for c in header.split("|")[1:] if (m := OPTION_COL_RE.match(re.sub(r"[*`]", "", c).strip()))}
        if not OPTION_RE.match(letter):
            p.append(f"R1: dòng **{R1_LABELS[2]}:** phải là mã phương án (A, B, A′…), đang là '{raw}'")
        elif letter not in cols:
            p.append(f"R1: phương án {letter} không khớp cột nào trong bảng mục 3")
    rounds = review_rounds(text)
    if rounds > MAX_REVIEW_ROUNDS:
        p.append(f"R2: vòng {rounds} > {MAX_REVIEW_ROUNDS} (trần 2 vòng)")
    elif rounds == MAX_REVIEW_ROUNDS and meta.get("status") == "in_review":
        p.append("R2: vòng 2 mà còn in_review: decision-reviewer điền mục 10, chuyển open/provisional")
    return p


def _blank_comments(text: str) -> str:
    """Remove HTML comments and fenced code blocks but keep their newlines so line numbers stay true."""
    keep_newlines = lambda m: "\n" * m.group(0).count("\n")  # noqa: E731
    text = re.sub(r"```.*?```", keep_newlines, text, flags=re.S)
    return re.sub(r"<!--.*?-->", keep_newlines, text, flags=re.S)


def _sections_with_line(text: str, first: str, last: str) -> tuple[int, str]:
    """Return (1-based line of the first section heading, text from `first` heading up to `last` heading)."""
    i = text.find("\n" + first)
    if i < 0:
        return 0, ""
    j = text.find("\n" + last, i + 1)
    return text.count("\n", 0, i + 1) + 1, text[i + 1: j if j > 0 else len(text)]


def _p_rules_text(meta: dict) -> str | None:
    """Normalized text if the P-rules apply to this DR (created after P_RULES_SINCE, not withdrawn), else None."""
    created = _scalar(meta, "created")
    if not DATE_RE.match(created) or created <= P_RULES_SINCE or _scalar(meta, "status") in P_RULES_SKIP_STATUS:
        return None
    return _blank_comments(unicodedata.normalize("NFC", meta["_text"]))


def _check_p4_line(line: str, lineno: int) -> list[str]:
    """Every URL needs a valid read label before it on the same line, after the previous URL."""
    problems: list[str] = []
    prev_end = 0
    line = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)
    for m in EXTERNAL_URL_RE.finditer(line):
        labels = READ_LABEL_RE.findall(line[prev_end:m.start()])
        prev_end = m.end()
        if not labels:
            problems.append(f"P4: dòng {lineno}: link ngoài thiếu nhãn [ngoài, đọc YYYY-MM-DD] đứng trước: {m.group(0)[:80]}")
            continue
        try:
            dt.date.fromisoformat(labels[-1])
        except ValueError:
            problems.append(f"P4: dòng {lineno}: ngày đọc không hợp lệ: {labels[-1]}")
    return problems


def check_reference_rules(meta: dict) -> list[str]:
    """P2 (codes in sections 3-6 must be in affects/related, each code by itself) and P4 (each external URL in
    section 5 needs a read date). Only for DRs created after P_RULES_SINCE, not withdrawn. Invalid `created`
    is already reported by check_loop_guards. A missing section marker is reported, never skipped silently."""
    text = _p_rules_text(meta)
    if text is None:
        return []
    declared: set[str] = set()
    for key in ("affects", "related"):
        v = meta.get(key, "")
        declared.update(REF_CODE_RE.findall(", ".join(v) if isinstance(v, list) else v))
    p: list[str] = []
    for marker in ("## 3.", "## 5.", "## 6.", "## 7."):
        if "\n" + marker not in text:
            p.append(f"P2/P4: thiếu mục '{marker}', không xác định được phạm vi kiểm")
    start, body = _sections_with_line(text, "## 3.", "## 7.")
    seen: set[str] = set()
    for offset, line in enumerate(body.splitlines()):
        for code in REF_CODE_RE.findall(LINK_TARGET_RE.sub("", line)):
            if code not in seen and code not in declared:
                seen.add(code)
                p.append(f"P2: dòng {start + offset}: mã {code} ở mục 3–6 chưa có trong affects/related")
    start5, sec5 = _sections_with_line(text, "## 5.", "## 6.")
    for offset, line in enumerate(sec5.splitlines()):
        p += _check_p4_line(line, start5 + offset)
    return p


HYBRID_LINE_RE = re.compile(r"^[ \t]*[*_]*Đã cân nhắc phương án lai / để sau\?[*_]*[ \t:]*(.*)$", re.M)
HYBRID_LETTER_RE = re.compile(r"(?<!\w)[A-Z][0-9]*['′’]?(?!\w)")  # option letter: A, B, B′, C1, A'
HYBRID_HEADER_CELL_RE = re.compile(r"^[*_]*([A-Z][0-9]*['′’]?)\.")  # table header cell "A. text", "B′. text"


def _option_letter(token: str) -> str:
    return token.replace("'", "′").replace("’", "′")


def check_hybrid_line(meta: dict) -> list[str]:
    """In section 3, the line 'Đã cân nhắc phương án lai / để sau?' starts with có/không; with
    'có' it must name at least one option letter that is a column header of the options table in the same section.
    DRs without the line, withdrawn DRs, decided and superseded DRs are skipped (no false alarm on closed tickets)."""
    if _scalar(meta, "status") in {"decided", "superseded"}:
        return []
    text = _p_rules_text(meta)
    if text is None:
        return []
    start, body = _sections_with_line(text, "## 3.", "## 4.")
    lines = body.splitlines()
    for offset, line in enumerate(lines):
        m = HYBRID_LINE_RE.match(line)
        if not m:
            continue
        lineno = start + offset
        value = m.group(1).strip().lstrip("*_ ").strip()
        head = re.match(r"(có|không)(?![^\W_])", value, re.I)
        if not head:
            return [f"P-LAI: dòng {lineno}: 'phương án lai' phải bắt đầu bằng 'có' hoặc 'không'"]
        if head.group(1).lower() == "không":
            return []
        header: set[str] = set()
        for row in lines:
            if not row.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            found = {_option_letter(h.group(1)) for c in cells if (h := HYBRID_HEADER_CELL_RE.match(c))}
            if found:
                header = found
                break
        if not header:
            return [f"P-LAI: dòng {lineno}: mục 3 không có bảng phương án với cột 'A.', 'B.'… để đối chiếu chữ cái"]
        named = {_option_letter(t) for t in HYBRID_LETTER_RE.findall(value[head.end():])}
        if not named & header:
            return [f"P-LAI: dòng {lineno}: trả lời 'có' nhưng không nêu chữ cái phương án nào có trong bảng ({', '.join(sorted(header))})"]
        return []
    return []


PA_BULLET_RE = re.compile(r"^(\s*)[-*]\s+[*_]*Ý kiến product-analyst")  # `-`/`*`, indented, optional bold/italic
# Exact hint and placeholder of templates/decision-request.md; nothing else is stripped as "template text".
PA_GUIDANCE = '(bắt buộc khi topic nằm trong `analyst_topics`; ghi "không áp dụng" nếu topic khác)'
# Hint of earlier template versions, still present in existing DRs.
PA_OLD_GUIDANCE = '(bắt buộc khi `topic: learning`; ghi "không áp dụng" nếu topic khác)'
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
PA_PLACEHOLDER_RE = re.compile(r"<tóm tắt ý kiến[^>]*>")


def _pa_bullet_value(lines: list[str], i: int, indent: int) -> str:
    """Text of the opinion bullet at lines[i]: rest of its line plus the lines that belong to it."""
    rest = PA_BULLET_RE.sub("", lines[i], count=1)
    parts = [rest]
    for nxt in lines[i + 1:]:
        stripped = nxt.strip()
        if stripped and len(nxt) - len(nxt.lstrip()) <= indent:  # not indented deeper than the bullet: ends it (no lazy continuation)
            break
        parts.append(stripped)
    return " ".join(parts)


def _pa_value_is_empty(raw: str) -> bool:
    value = raw.replace(PA_GUIDANCE, "").replace(PA_OLD_GUIDANCE, "")
    value = PA_PLACEHOLDER_RE.sub("", value)
    value = ISO_DATE_RE.sub("", value)  # a date alone is not an opinion: "(2026-11-08): (không áp dụng)" is still empty
    if not re.search(r"\w", value):  # only punctuation / emphasis marks
        return True
    return value.strip(" \t:*_`.()").lower() == "không áp dụng"


def check_pa_opinion(meta: dict) -> list[str]:
    """P6 (auto part): DRs in ANALYST_TOPICS created after P_RULES_SINCE need a filled product-analyst line in section 5."""
    text = _p_rules_text(meta)
    matched = sorted(ANALYST_TOPICS.intersection(topics_of(meta)))
    if text is None or not matched:
        return []
    label = "topic " + ", ".join(matched)
    start, sec5 = _sections_with_line(text, "## 5.", "## 6.")
    if not sec5:
        return [f"P6: thiếu mục 5; {label} cần dòng '- Ý kiến product-analyst' có nội dung"]
    lines = sec5.splitlines()
    for offset, line in enumerate(lines):
        m = PA_BULLET_RE.match(line)
        if not m:
            continue
        if _pa_value_is_empty(_pa_bullet_value(lines, offset, len(m.group(1)))):
            return [f"P6: dòng {start + offset}: {label} nhưng ý kiến product-analyst để trống, còn mẫu hoặc 'không áp dụng'"]
        return []
    return [f"P6: mục 5 (từ dòng {start}): {label} thiếu dòng '- Ý kiến product-analyst'"]


def row_link(meta: dict) -> str:
    rel = meta["_path"].relative_to(INBOX.parent).as_posix()
    if meta.get("_dossier"):
        heading = re.search(r"^## 10\..*$", meta["_text"], re.M)  # real heading, so the anchor resolves on GitHub
        rel += "#" + slug(heading.group(0)[3:]) if heading else ""
    return f"[{meta.get('id', meta['_path'].stem)}]({rel})"


def short(v: str, n: int = 160) -> str:
    v = (v or "—").replace("|", "/")
    return v if len(v) <= n else v[: n - 1] + "…"


def fmt_list(v) -> str:
    return ", ".join(v) if isinstance(v, list) else (v or "—")


def dr_key(meta: dict) -> str:
    """Label for messages: the `id` when it is a non-empty string, else the file name without `.md`."""
    v = meta.get("id")
    return v if isinstance(v, str) and v else meta["_path"].stem


def _renderable(meta: dict) -> dict:
    """Copy whose id and deadline are plain strings, so a malformed ticket cannot crash the rendering."""
    d = dict(meta)
    d["id"] = dr_key(meta)
    if not isinstance(d.get("deadline"), str):
        d["deadline"] = ""
    return d


def build(drs: list[dict]) -> str:
    """Every ticket stays visible: a ticket with bad frontmatter is listed in a warning section at the top,
    and, when its `status` is valid, also in its normal group (unknown topic goes to "khác")."""
    broken = [(d, check_frontmatter(d)) for d in drs]
    broken = [(_renderable(d), msgs) for d, msgs in broken if msgs]
    drs = [_renderable(d) for d in drs]
    today = dt.date.today().isoformat()
    old = INBOX.read_text(encoding="utf-8") if INBOX.exists() else ""
    manual = "- —"
    if MANUAL_START in old and MANUAL_END in old:
        manual = old.split(MANUAL_START, 1)[1].split(MANUAL_END, 1)[0].strip() or "- —"

    open_ = sorted([d for d in drs if d.get("status") == "open"], key=lambda d: (d.get("deadline") or "9999", d.get("id")))
    prov = [d for d in drs if d.get("status") == "provisional"]
    pipeline = [d for d in drs if d.get("status") in ("draft", "in_review")]
    recent = [d for d in drs if d.get("status") == "decided"][-15:]

    out = [
        "# 📥 Hộp quyết định của Product Owner",
        "",
        f"> Tự sinh bởi `build_inbox.py` (plugin agent-ops) — cập nhật {today}. **Không sửa tay**, trừ mục *Việc bạn cần làm*.",
        "> Trả lời: `/decide DR-012 A, DR-013 đồng ý đề xuất` · Hỏi thêm: `/explain DR-012 <câu hỏi>`",
        "",
        f"**Cần bạn quyết:** {len(open_)} · **Quyết định tạm của agent:** {len(prov)} · **Đang soạn/phản biện:** {len(pipeline)}"
        + (f" · **Phiếu lỗi frontmatter:** {len(broken)}" if broken else ""),
        "",
    ]
    if broken:
        out += ["## ⚠️ Phiếu lỗi frontmatter (cần agent sửa; phiếu vẫn được liệt kê ở nhóm của nó nếu `status` hợp lệ)", ""]
        for d, msgs in broken:
            out.append(f"- {row_link(d)} (`{d['_path'].name}`): " + "; ".join(msgs))
        out.append("")
    out += [
        "## 🔴 Cần bạn quyết định (loại 1)",
    ]
    if not open_:
        out.append("- Không có.")
    by_topic: dict[str, list[dict]] = {}
    for d in open_:
        by_topic.setdefault((topics_of(d) or ["khác"])[0], []).append(d)
    for topic, items in by_topic.items():
        out += ["", f"### {TOPICS.get(topic, topic)}", "",
                "| Phiếu (mở thẳng hồ sơ) | Câu hỏi | Đề xuất | Reviewer | Lời nhắn của reviewer | Chặn | Hạn |", "|---|---|---|---|---|---|---|"]
        for d in items:
            out.append(f"| {row_link(d)} | {d.get('title','')} | {short(d['_choice'], 80)} | {short(d['_review'], 60)} | {short(d.get('_note'))} | {fmt_list(d.get('blocks'))} | {d.get('deadline') or '—'} |")
    out += ["", "## 🟡 Quyết định tạm của agent (loại 2) — bác bằng `/decide DR-xxx <lựa chọn khác>`", ""]
    if prov:
        out += ["| Phiếu | Câu hỏi | Agent đã chọn | Lời nhắn của reviewer | Ghi nhận |", "|---|---|---|---|---|"]
        out += [f"| {row_link(d)}{' ⬇️ hạ loại' if d['_review'].startswith('⬇️') else ''}{' ⚡ phiếu ngắn' if d.get('_short') else ''} | {d.get('title','')} | {short(d['_choice'], 80)} | {short(d.get('_note'))} | {d.get('decided_as','')} |" for d in prov]
    else:
        out.append("- Không có.")
    out += ["", "## 🧰 Việc bạn cần làm (không phải quyết định)", MANUAL_START, manual, MANUAL_END, "",
            "## ⏳ Đang soạn / phản biện (chưa cần bạn xem)", ""]
    out += [f"- {row_link(d)} — {d.get('title','')} (`{d.get('status')}`)" for d in pipeline] or ["- Không có."]
    out += ["", "## ✅ Đã quyết gần đây", ""]
    out += [f"- {row_link(d)} → {d.get('decided_as','')} — {d.get('title','')}" for d in reversed(recent)] or ["- Chưa có."]
    return "\n".join(out) + "\n"


def check_dr(meta: dict) -> list[str]:
    """All rules for one DR. Malformed frontmatter is reported alone: the other rules assume it is well-formed."""
    bad = check_frontmatter(meta)
    if bad:
        return bad
    if meta.get("_short"):
        return validate_short(meta)
    return validate(meta) + check_loop_guards(meta) + check_reference_rules(meta) + check_pa_opinion(meta) + check_hybrid_line(meta)


def check_duplicate_ids(drs: list[dict]) -> dict[str, list[str]]:
    """Two tickets with the same non-empty string `id` overwrite each other in reports; flag each such id once."""
    files: dict[str, list[str]] = {}
    for d in drs:
        v = d.get("id")
        if isinstance(v, str) and v:
            files.setdefault(v, []).append(d["_path"].name)
    return {k: [f"id trùng ở {len(v)} file: {', '.join(v)}"] for k, v in files.items() if len(v) > 1}


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Unknown flags exit with rc=2 and usage on stderr; -h/--help prints usage on stdout, rc=0. Nothing is written."""
    parser = argparse.ArgumentParser(
        prog="build_inbox.py",
        allow_abbrev=False,
        description="Build management/DECISIONS-INBOX.md from management/decision-requests/DR-*.md.",
    )
    parser.add_argument("--check", action="store_true",
                        help="validate DRs and internal links, print problems, exit 1 on problems; writes nothing")
    return parser.parse_args(argv)


def _docs_checks():
    """Load the sibling check_docs.py by path (`python -I` removes the script directory from sys.path)."""
    path = Path(__file__).resolve().with_name("check_docs.py")
    spec = importlib.util.spec_from_file_location("check_docs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    args = parse_args(sys.argv[1:])
    drs = [parse(p) for p in sorted(DR_DIR.glob("DR-*.md"))]
    problems: dict[str, list[str]] = {}
    for d in drs:
        msgs = check_dr(d)
        if msgs:
            problems.setdefault(dr_key(d), []).extend(msgs)
    for k, v in check_duplicate_ids(drs).items():
        problems.setdefault(k, []).extend(v)
    if args.check:
        for k, v in problems.items():
            for msg in v:
                print(f"{k}: {msg}")
        doc_errors, doc_warnings = _docs_checks().run(ROOT)  # links, BOARD, stale "đề xuất" lines
        for msg in doc_errors:
            print(msg)
        for msg in doc_warnings:
            print(f"Cảnh báo: {msg}")
        n = sum(map(len, problems.values())) + len(doc_errors)
        print(f"{len(drs)} phiếu, {n} vấn đề, {len(doc_warnings)} cảnh báo")
        return 1 if n else 0
    INBOX.write_text(build(drs), encoding="utf-8")
    print(f"Đã ghi {INBOX.relative_to(ROOT)} ({len(drs)} phiếu)")
    for d in drs:
        for msg in check_frontmatter(d):
            print(f"Cảnh báo, phiếu lỗi frontmatter vẫn hiện trong Inbox: {dr_key(d)}: {msg}")
    if problems:
        print(f"Cảnh báo: {len(problems)} phiếu có vấn đề — chạy --check để xem")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
