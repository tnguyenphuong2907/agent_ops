---
description: Phản biện một hoặc nhiều tính năng (có cần thiết không, có hiệu quả không, đáng công sức không)
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Giao agent `agent-ops:idea-reviewer` phản biện tính năng sau theo mục "Phản biện tính năng" trong file agent (7 câu hỏi):

$ARGUMENTS

Nếu tôi chỉ đưa tên tính năng, tìm mô tả của nó trong `tài liệu tầm nhìn và yêu cầu của dự án`, và `<mgmt>/decisions.md`. Nếu tôi đưa một file (PRD, user story, phiếu DR), phản biện mọi tính năng trong file đó.

Ghi kết quả vào `feature-review-<NN>.md` (số tiếp theo) trong thư mục tài liệu tầm nhìn của dự án. Tính năng có kết luận khác **Giữ** → tạo phiếu DR theo skill `agent-ops:decision-requests`. Trả lời tôi bằng bảng kết luận ngắn: tính năng · kết luận · lý do một câu.
