---
description: Hỏi thêm về một phiếu quyết định (DR) trước khi quyết
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Tôi (Product Owner) cần thêm thông tin về phiếu quyết định sau:

$ARGUMENTS

Làm theo skill `agent-ops:decision-requests` mục 5:
1. Đọc phiếu DR và các tài liệu nó dẫn tới.
2. Giao agent phù hợp trả lời (mặc định `agent-ops:architect`; phạm vi/nghiệp vụ → `agent-ops:product-analyst`; dữ liệu → `agent-ops:db-designer`).
3. Câu trả lời phải dẫn nguồn (file + mục, D-xxx, ADR, hoặc link ngoài). Không có nguồn thì nói rõ là suy luận.
4. Ghi câu hỏi và câu trả lời vào mục 9 "Hỏi thêm" của phiếu.
5. Nếu câu trả lời làm đổi đề xuất → làm theo skill `agent-ops:decision-requests` mục 5; lượt xem lại tính vào trần 2 vòng.
6. Trả lời tôi ngắn gọn ở đây, kèm link tới phiếu.
