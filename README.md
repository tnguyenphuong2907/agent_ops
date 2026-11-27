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

## Cấu hình dự án

Tạo `.agent-ops.toml` ở gốc dự án:

```toml
plugin_path = "../agent-ops/plugins/agent-ops"   # dùng cho shim tool (đường dẫn tuyệt đối hoặc tương đối gốc dự án)

[paths]
management = "management"                         # thư mục quản lý (mặc định)

[inbox]
no_review_conclusion_exempt_ids = []              # DR được miễn kết luận phản biện

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
python -m pytest plugins/agent-ops/tools/tests plugins/agent-ops/hooks/scripts
```

## Nội dung

`tools/` (Python stdlib), `hooks/` (hooks.json + scripts), `templates/`, `commands/` (gọi dạng `/agent-ops:<lệnh>`). Agent và skill chưa chuyển vào bản 0.1.0.
