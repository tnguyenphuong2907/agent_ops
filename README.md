# agent-ops

Plugin Claude Code dùng lại hệ thống quản lý cho đội agent: bảng task, phiếu quyết định (DR), bài học, kế hoạch/báo cáo ngày, phím tắt `ct` (đóng task) và `mp` (merge PR) chạy 0 token, cảnh báo ngữ cảnh lớn.

## Cài đặt

Từ GitHub (khuyên dùng), gõ trong Claude Code:

```
/plugin marketplace add tnguyenphuong2907/agent_ops
/plugin install agent-ops@agent-ops-local
```

Từ bản clone ở máy (khi đang phát triển plugin):

```
git clone https://github.com/tnguyenphuong2907/agent_ops.git agent-ops
/plugin marketplace add ./agent-ops
/plugin install agent-ops@agent-ops-local
```

Clone vào thư mục `agent-ops` để khớp với `plugin_path` mẫu bên dưới.

Cập nhật lên bản mới nhất:

```
/plugin marketplace update agent-ops-local
```

Gỡ cài đặt: `/plugin uninstall agent-ops@agent-ops-local`.

## Khởi tạo dự án mới

Trong repo đã `git init`, gõ `/agent-ops:init` (hoặc chạy `tools/init_project.py [--management DIR] [--base BRANCH]`). Lệnh chỉ tạo file còn thiếu: `.agent-ops.toml`, `.claude/project-profile.md`, và trong thư mục quản lý: `README.md` (luật quy trình), `decision-policy.md`, `decisions.md`, `roadmap.md`, `lessons/`, `tasks/`, `decision-requests/`, BOARD và DECISIONS-INBOX. Bản chép thuộc về dự án: cập nhật plugin không đổi chúng.

Sau đó điền hồ sơ dự án và tên check CI vào `[merge] required_checks`. `mp` cần `gh`, remote GitHub và PR có ít nhất một check CI.

## Cấu hình dự án

Tạo `.agent-ops.toml` ở gốc dự án:

```toml
plugin_path = "../agent-ops/plugins/agent-ops"   # dùng cho shim tool (đường dẫn tuyệt đối hoặc tương đối gốc dự án)

[paths]
management = "management"                         # thư mục quản lý (mặc định)

[merge]
base = "main"                                     # nhánh đích của ct / mp
required_checks = []                              # tên check CI bắt buộc, vd. ["scan"]; mp bắt buộc có khoá này trên origin/<base> ([] = không bắt buộc check nào)

[inbox]
no_review_conclusion_exempt_ids = []              # DR được miễn kết luận phản biện
analyst_topics = []                               # topic bắt buộc có ý kiến product-analyst
# [inbox.topics]                                  # nếu khai: thay toàn bộ danh sách mặc định (khoá = "tên nhóm")

[check_docs]
scan_dirs = ["management", "docs"]                # thư mục .md cần kiểm link
dup_scope = ["CLAUDE.md", ".claude/skills"]       # phần tử đầu là file, còn lại là thư mục; kiểm đoạn chép trùng
# [[check_docs.dup_allowlist]]  files = [a, b], start = "...", kind = "có chủ đích", reason = "..."
```

Gốc dự án được tìm theo thứ tự: env `AGENT_OPS_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, `git rev-parse --show-toplevel`, thư mục hiện tại.

## Tool

Gọi trực tiếp: `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_board.py" --check`. Để giữ lệnh cũ `python3 management/tools/<x>.py`, đặt shim (~15 dòng) ở `<management>/tools/<x>.py`: đọc `plugin_path` (hoặc env `AGENT_OPS_PLUGIN_PATH`), đặt `AGENT_OPS_PROJECT_DIR`, rồi `runpy.run_path(<plugin>/tools/<x>.py, run_name="__main__")`.

## Test

```
python -m pytest plugins/agent-ops/tools/tests plugins/agent-ops/hooks/scripts   # hoặc: uvx pytest ...
```

## Nội dung

`tools/` (Python stdlib), `hooks/` (hooks.json + scripts), `templates/`, `commands/` (gọi dạng `/agent-ops:<lệnh>`). Agent (`agents/`) và skill chung (`skills/`) cũng nằm trong plugin.
