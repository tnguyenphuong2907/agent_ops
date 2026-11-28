---
name: close-task
description: Đóng task khi review Approved và QA Passed bằng script `close_task.py` của plugin - kiểm DoD, đổi `done` ở task/subtask/epic, sinh BOARD, build_inbox --check, commit + push. Dùng sau QA Passed, trước merge. PO gõ `ct [task-id]` = chạy script, 0 token.
argument-hint: "[task-id] [--pr] [--handoff]  (bỏ trống task = lấy từ tên nhánh)"
context: fork
model: haiku
---

Đóng task `$ARGUMENTS` (vai `pm`, việc cơ học). Mọi ô kiểm (nhánh, Approved/Passed bỏ comment mẫu, subtask `done`, bằng chứng QA, phiếu DR `open` ở mục 6) và mọi bước cập nhật, commit, push nằm trong script; ô nào trượt thì script không sửa gì.

Chạy đúng một lệnh, foreground, không sửa gì thêm:
```bash
cd "${CLAUDE_PROJECT_DIR}" && python3 "${CLAUDE_PLUGIN_ROOT}/tools/close_task.py" $ARGUMENTS
```
Cờ tuỳ chọn: `--pr` (mở PR hoặc bỏ nháp), `--handoff` / `--next "…"` (ghi HANDOFF, giữ bước tiếp cũ). Subtask còn `in_review` sau review/QA đạt: người gọi chạy trước `python3 "${CLAUDE_PLUGIN_ROOT}/tools/prepare_close.py" <task>` (chuyển `done`, kiểm cột "Đã sửa?").

Trả về nguyên văn output của script, thêm dòng `Tool:` nếu lệnh lỗi. Script báo trượt → không tự sửa task, chỉ báo.
