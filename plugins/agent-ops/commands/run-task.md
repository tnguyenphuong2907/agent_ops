---
description: Thực hiện một task theo đúng quy trình (dev → review → QA)
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Thực hiện task $ARGUMENTS theo đúng quy trình trong `<mgmt>/README.md`:

0. Đi theo làn ghi ở `lane:` của task (L1/L2/L3, quy tắc làn ở `<mgmt>/README.md`); chưa có `lane:` thì `agent-ops:pm` chọn rồi ghi vào. L3 bỏ qua bước thiết kế, review `effort: "medium"`, QA chỉ kiểm AC liên quan.
1. `agent-ops:pm` kiểm tra task đạt Definition of Ready. Không đạt → dừng, báo tôi thiếu gì.
2. Giao lần lượt từng subtask cho agent được ghi ở `assignee`; sau mỗi subtask kiểm tra đã ghi tiến trình + commit.
3. Giao `agent-ops:code-reviewer` (hoặc reviewer ghi trong task). Changes requested → quay lại dev (tối đa 2 vòng, quá thì dừng và báo tôi).
4. Giao `agent-ops:qa` nghiệm thu theo AC, lưu bằng chứng.
5. `agent-ops:pm` kiểm tra Definition of Done, cập nhật trạng thái rồi chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_board.py"`.
6. Báo tôi kết quả ngắn gọn và mọi điểm cần tôi quyết định.
