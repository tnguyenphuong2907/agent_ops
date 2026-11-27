---
description: Ghi nhận quyết định của Product Owner (theo phiếu DR hoặc tự do)
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Tôi (Product Owner) quyết định như sau:

$ARGUMENTS

Dùng agent `agent-ops:pm`, theo skill `agent-ops:decision-requests` mục 6:
1. Với mỗi phiếu được nhắc (`DR-xxx`): "đồng ý đề xuất" = phương án ở dòng **Chọn:** của phiếu. Câu trả lời mơ hồ → hỏi lại tôi, không đoán.
2. Ghi D-xxx mới vào `<mgmt>/decisions.md`: cột **Áp dụng cho** lấy từ `affects` của phiếu (bổ sung nếu thấy thiếu), Ghi chú dẫn `DR-xxx`. Quyết định không có phiếu → vẫn ghi D-xxx, tự xác định task/epic/ADR chịu ảnh hưởng.
3. Cập nhật phiếu (mục 10, `decided_as`, `status: decided`), thêm D-xxx vào `links` của từng task liên quan, gỡ `blocked` nếu có.
4. Bác một quyết định tạm → D-xxx mới ghi "thay thế D-yyy"; nếu đã có việc làm theo quyết định tạm → tạo task sửa.
5. Quyết định ảnh hưởng kiến trúc → nhắc architect cập nhật ADR.
6. Chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_inbox.py"`.
7. Tóm tắt cho tôi: D-xxx đã ghi, task được gỡ chặn, task phát sinh.

Chỉ sửa tài liệu sở hữu (bảng nguồn sự thật, file quy tắc của dự án (`CLAUDE.md`)): ngoài phần ghi nhận ở bước 2–4 và 6, nội dung quyết định không chép sang tài liệu khác.
