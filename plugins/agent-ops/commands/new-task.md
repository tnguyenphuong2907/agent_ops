---
description: Tạo epic/task/subtask mới từ mô tả (PM)
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Dùng agent `agent-ops:pm` với skill `agent-ops:task-management` để tạo công việc mới từ mô tả sau:

$ARGUMENTS

Yêu cầu: xác định epic phù hợp (hoặc đề xuất epic mới), tạo task ở trạng thái `backlog`, đề xuất cách chia subtask và tiêu chí nghiệm thu nháp, chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_board.py"`. Nếu việc này nằm ngoài phạm vi đã chốt, tạo Change Request thay vì task.
