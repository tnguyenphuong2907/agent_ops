---
id: E00-T00-S00
task: E00-T00
title: "<Tên subtask>"
status: backlog
layer:                    # be | fe | e2e | doc
assignee:
estimate_hours:           # ≤ 6
actual_hours:
selfcheck:                # api | ui | trống (subtask thiết kế; mẫu design-selfcheck.md)
commit:
---

# E00-T00-S00 — <Tên subtask>

## Việc cần làm  ·  _pm_
<Mô tả cụ thể, đủ để làm không cần hỏi lại. Liệt kê file dự kiến (≤ 25).>

## Điều kiện xong  ·  _pm_
- [ ]

## Tiến trình  ·  _dev_
> Ghi giờ: chạy `date` lúc bắt đầu và lúc kết thúc, ghi cả hai vào đây rồi tính `actual_hours`.
> Subtask đồng bộ/chuyển quy tắc: ghi lệnh `grep` theo ID quy tắc chạy sau khi sửa, số kết quả và danh sách file (không chép từng dòng). Chỉ subtask sửa cuối của task ghi kết quả quét cuối cùng; sửa thêm thì quét lại. Không ghi hash commit.
> Subtask sửa tool kiểm tra (`tools/`): kèm bảng ca phản ví dụ dưới đây và 1 test mỗi ca trước khi gửi review.
>
> | Loại ca | Ca cụ thể | Test |
> |---|---|---|
> | Nhiều mẫu/dòng | | |
> | Định dạng đậm/nghiêng | | |
> | Ô trống | | |
> | Giá trị sai | | |
> | Ngưỡng ngày | | |
-

## Tự kiểm  ·  _người làm_
> Chỉ khi frontmatter có `selfcheck:`: chép bảng tương ứng từ mẫu `design-selfcheck.md` của plugin vào đây và trả lời từng dòng. Còn ô trống thì chưa chuyển review (`check_task.py <task> --stage review`).

## Kết quả kiểm tra  ·  _reviewer / qa_
-
