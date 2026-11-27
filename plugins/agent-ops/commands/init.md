---
description: Khởi tạo file quản lý của agent-ops cho dự án mới (không ghi đè file đã có)
---
Chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/init_project.py" $ARGUMENTS`.

Sau đó báo tôi danh sách file đã tạo/đã giữ, rồi hỏi các thông tin còn trống trong `.claude/project-profile.md` và tên check CI bắt buộc cho `[merge] required_checks` trong `.agent-ops.toml`. Không đoán các thông tin này. Không sửa `CLAUDE.md` hay `.claude/settings.json` khi tôi chưa yêu cầu.
