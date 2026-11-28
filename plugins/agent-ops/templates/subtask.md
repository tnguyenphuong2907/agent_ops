---
id: E00-T00-S00
task: E00-T00
title: "<Tên subtask>"
status: backlog
layer:                    # be | fe | e2e | doc
assignee:
estimate_hours:           # ≤ 6
actual_hours:
selfcheck:                # CHỈ subtask thiết kế: api | ui (mẫu design-selfcheck.md); subtask code để trống
plan:                     # opus | trống (subtask khó: opus lập kế hoạch trước khi code)
commit:
---

# E00-T00-S00 — <Tên subtask>

## Việc cần làm  ·  _pm_
<Mô tả cụ thể, đủ để làm không cần hỏi lại. Liệt kê file dự kiến (≤ 25).>

## Điều kiện xong  ·  _pm_
- [ ]

## Kế hoạch  ·  _người lập kế hoạch (opus)_
> Chỉ khi frontmatter có `plan: opus`: viết **trước khi code**, ≤ 60 dòng, không viết code: file cần tạo/sửa và việc ở mỗi file, thứ tự làm, ca biên + cách xử lý, test cần có, đoạn nguồn người code cần mở (đường dẫn + dòng). Còn trống thì `task_step.py` và hook chặn.

## Tiến trình  ·  _dev_
> Bắt đầu/kết thúc bằng `task_step.py <subtask> start|done [--commit <sha>] [--note "..."]`: tool lấy giờ, đổi trạng thái, ghi Lịch sử và tính `actual_hours`.
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
