---
description: Retro hằng tuần - tổng hợp lỗi, rút bài học, đề xuất sửa luật (PM)
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Dùng agent `agent-ops:pm` với skill `agent-ops:lessons-learned` mục 3 để chạy retro tuần này.

1. Lấy số liệu bằng `python3 "${CLAUDE_PLUGIN_ROOT}/tools/retro_stats.py" --since <thứ Hai tuần này>` và so với retro gần nhất trong `<mgmt>/lessons/retros/`.
2. Gắn nhóm cho nhận xét chưa có nhóm, tìm nguyên nhân gốc, viết/ cập nhật `LL-xxx` trong `<mgmt>/lessons/LESSONS.md`.
3. Gom mọi đề xuất sửa luật vào **một phiếu DR** (P1, P2…), giao `agent-ops:decision-reviewer` phản biện, rồi build inbox.
4. Ghi báo cáo `<mgmt>/lessons/retros/<năm>-W<tuần>.md`.
5. Trả lời tôi: tóm tắt 1 phút, nhóm lỗi tăng/giảm, link phiếu DR cần tôi duyệt.

Ghi chú của tôi (nếu có): $ARGUMENTS
