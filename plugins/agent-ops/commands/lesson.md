---
description: Ghi nhận một bài học khi tôi (PO) chỉ ra lỗi của agent
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Tôi (Product Owner) chỉ ra lỗi sau:

$ARGUMENTS

Dùng agent `agent-ops:pm`, theo skill `agent-ops:lessons-learned` mục 2:
1. Ghi một dòng `LL-xxx` trạng thái `ghi nhận` vào `<mgmt>/lessons/LESSONS.md`: nhóm lỗi, chuyện gì xảy ra, trích lời tôi, file/task liên quan.
2. Nếu sản phẩm bị lỗi chưa xong → giao người phụ trách sửa ngay trong task đó.
3. Không sửa file agent/skill/`CLAUDE.md` — để retro tuần này đề xuất.
4. Xác nhận lại với tôi trong 2 dòng.
