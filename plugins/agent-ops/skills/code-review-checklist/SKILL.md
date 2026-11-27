---
name: code-review-checklist
description: Checklist review code chung (đúng AC, kiến trúc, chất lượng, hiệu năng, bảo mật, test, tài liệu). Dùng khi review bất kỳ thay đổi code nào; mục kiểm riêng dự án nằm ở skill dự án trong .claude/project-profile.md.
---

# Checklist review

Checklist chung cho mọi dự án. Mục kiểm riêng dự án (kiến trúc, auth, dữ liệu cá nhân, tích hợp bên thứ ba…): skill dự án mà `.claude/project-profile.md` liệt kê cho vai code-reviewer; kiểm cả hai.
**Mọi thay đổi đụng key, secret, token, log, dữ liệu cá nhân: đối chiếu thêm skill bảo mật của dự án (profile).**
Tên module/env/endpoint/bảng có thể chốt muộn: lệch tên không phải lỗi, lệch hành vi mới là lỗi.

## Đúng yêu cầu
- [ ] Mỗi AC có code + test tương ứng.
- [ ] Không có thay đổi ngoài phạm vi task.

## Kiến trúc
- [ ] Tuân thủ quy tắc import/ranh giới module của dự án; công cụ kiểm quy tắc (lệnh trong `CLAUDE.md`) đạt.
- [ ] Không có logic nghiệp vụ trong tầng hạ tầng/dùng chung; tầng dùng chung chỉ chứa phần được phép.
- [ ] Không sửa phần dữ liệu/schema thuộc quyền db-designer ngoài task DB.

## Chất lượng
- [ ] Tên rõ nghĩa, hàm ≤ ~40 dòng, không lồng quá 3 cấp.
- [ ] Type đầy đủ; type checker strict đạt.
- [ ] Lỗi dùng exception chuẩn, thông báo có ích cho debug.
- [ ] Không code chết, không TODO không có task.

## Hiệu năng
- [ ] Không N+1, không select `*` thừa, truy vấn có index phù hợp.
- [ ] Không I/O đồng bộ trong async; gọi ngoài có timeout.
- [ ] Danh sách có phân trang.
- [ ] Không gọi dịch vụ ngoài tốn tiền thừa (có dùng cache khi được?).

## Bảo mật chung
- [ ] Mọi truy vấn dữ liệu cá nhân lọc theo `user_id` của người đang đăng nhập.
- [ ] Không SQL nối chuỗi; input được validate.
- [ ] Không secret/key/token trong code, log, response, thông báo lỗi.

## Test & tài liệu
- [ ] Test lỗi + quyền; không gọi mạng thật.
- [ ] Tài liệu API đủ và đã cập nhật; thay đổi phá vỡ đã ghi rõ.
- [ ] Tài liệu/ADR cập nhật nếu đổi hành vi quan trọng.
- [ ] Test không đổi kết quả hoặc `skip` theo dữ liệu có sẵn trong DB/môi trường; dùng savepoint hoặc fixture tự dựng.
- [ ] Script smoke/tooling không có tác dụng phụ ngoài thư mục tạm (không ghi file cấu hình thật).
- [ ] Phần chỉ lộ ở chế độ dev (StrictMode) có test mount-lại.
- [ ] Test dùng thời gian thật (`sleep`, `now`, TOTP, TTL, hết hạn): không tính lại giá trị phụ thuộc đồng hồ sau `sleep`; gửi lại đúng giá trị cũ hoặc tiêm đồng hồ; reviewer chạy `grep -n "sleep(\|now(\|time.time(\|now_code("` trong test đã đổi.
- [ ] Subtask sửa công cụ quản lý (`management/tools/`): có bảng 5 loại ca phản ví dụ (nhiều mẫu/dòng, đậm/nghiêng, ô trống, giá trị sai, ngưỡng ngày) và 1 test mỗi ca; reviewer vẫn tự chạy thật.
- [ ] Task đồng bộ/chuyển quy tắc: mục 3 có lệnh `grep` theo ID, số kết quả, danh sách file, ghi sau subtask sửa cuối kèm mã subtask. Chạy lại đúng lệnh đó; lệch số kết quả hoặc danh sách file = `DRIFT`. Không đòi hash commit.

Mức độ: **Blocker** (sai/không an toàn) · **Major** (phải sửa trước merge) · **Minor** (nên sửa) · **Nit** (tuỳ).
