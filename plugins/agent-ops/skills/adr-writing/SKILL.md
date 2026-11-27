---
name: adr-writing
description: Khi nào và cách viết Architecture Decision Record (ADR). Dùng khi chọn thư viện/công nghệ, thay đổi kiến trúc, đánh đổi quan trọng về hiệu năng/bảo mật/chi phí.
---

# Viết ADR

## Khi nào bắt buộc
- Thêm/đổi thư viện hoặc dịch vụ quan trọng (DB, auth, AI provider, queue…).
- Thay đổi nguyên tắc trong `CLAUDE.md`.
- Đánh đổi lớn: hiệu năng vs đơn giản, bảo mật vs tiện, chi phí.
- Bất cứ điều gì mà 3 tháng sau ai đó sẽ hỏi "tại sao lại làm thế này?".

## Cách viết
- File: `docs/02-architecture/adr/ADR-NNNN-<slug>.md`, đánh số tăng dần, theo `${CLAUDE_PLUGIN_ROOT}/templates/adr.md`.
- Tối thiểu 2 phương án đã cân nhắc, có bảng ưu/nhược.
- Trạng thái ban đầu `proposed`; chỉ PO chuyển `accepted`.
- Không sửa ADR đã `accepted` — viết ADR mới và đánh dấu cái cũ `superseded by ADR-xxxx`.
- Ghi thêm một dòng vào `management/decisions.md` khi được chấp nhận.
- Mỗi phương án bị loại ghi **lý do loại** (không chỉ ưu/nhược). Ghi link nguồn chính thức đã đọc khi chọn thư viện/dịch vụ.
- Mục Hệ quả ghi cả điều xấu chấp nhận được và điều kiện để xem lại quyết định.

## Red flags
- Quyết định kiến trúc chỉ nằm trong chat/task, không có ADR hay dòng trong `decisions.md`.
- ADR chỉ mô tả *làm gì* (chép lại code) mà không nói *vì sao* và *đã loại gì*.
- Phương án "rơm" (dựng cho có, rõ ràng thua) để làm đủ tối thiểu 2 phương án.
- Sửa nội dung ADR `accepted` thay vì viết ADR thay thế.
- Lý do kiểu "code tự giải thích", "viết sau khi ổn định", "ADR tốn công": ADR ngắn vẫn tốt hơn tranh luận lặp lại.

## Tự kiểm
- [ ] Đúng mẫu `${CLAUDE_PLUGIN_ROOT}/templates/adr.md`, đúng thư mục và số thứ tự.
- [ ] ≥ 2 phương án thật, mỗi cái có lý do chọn/loại; có link nguồn.
- [ ] Hệ quả có cả mặt xấu + điều kiện xem lại.
- [ ] Câu "luôn / không thể / bảo đảm" kèm kịch bản phản chứng (skill `agent-ops:decision-requests` mục 2).
- [ ] Sơ đồ/tài liệu bị ảnh hưởng (`overview.md`, `conventions.md`) cập nhật cùng commit.
