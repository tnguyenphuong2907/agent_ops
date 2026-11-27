---
description: Lập kế hoạch làm việc hôm nay (PM)
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Dùng agent `agent-ops:pm` với skill `agent-ops:daily-cadence` để lập kế hoạch cho hôm nay.

1. Đọc báo cáo ngày gần nhất trong `<mgmt>/daily/`, `<mgmt>/BOARD.md`, `<mgmt>/decisions.md`.
2. Áp dụng các quyết định mới của Product Owner vào các task liên quan.
3. Tạo `<mgmt>/daily/<hôm nay>-plan.md` theo `<mgmt>/templates/daily-plan.md`.
4. Trình bày cho tôi: mục tiêu ngày, danh sách task, việc đang chờ tôi quyết định. Hỏi tôi xác nhận trước khi giao việc cho các agent.

Ghi chú thêm của tôi (nếu có): $ARGUMENTS
