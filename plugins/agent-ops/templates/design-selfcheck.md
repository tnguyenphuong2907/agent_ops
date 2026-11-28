# Bảng tự kiểm thiết kế

> Subtask thiết kế đặt `selfcheck: api` hoặc `selfcheck: ui` ở frontmatter, chép bảng tương ứng vào mục `## Tự kiểm` của file subtask.
> Cột "Trả lời": chỗ trong đặc tả đã xử lý (mục/dòng) hoặc `không áp dụng vì <lý do>`. Viết `\|` nếu câu trả lời có dấu gạch đứng. Không đổi mã H/M.
> Người rà kiểm từng câu trả lời với nguồn, không chỉ kiểm ô đã điền.

## api — hợp đồng API
| # | Câu hỏi | Trả lời (mục/dòng, hoặc "không áp dụng vì …") |
|---|---|---|
| H1 | Gửi lại sau khi dữ liệu nguồn đã đổi: trường nào của response có thể `null` hoặc đổi? | |
| H2 | Trường dẫn xuất từ hàm có sẵn ánh xạ thế nào (đã đọc code của hàm)? | |
| H3 | Dữ liệu thiếu hoặc hỏng có bị chặn trước khi người dùng tốn công không? | |
| H4 | Hai lỗi cùng đúng thì mã nào thắng (thứ tự kiểm), có khớp AC không? | |
| H5 | Mỗi mã lỗi phát ra qua route/luồng nào? Mã không phát ra được thì test cần fixture gì? | |
| H6 | Giả định gì về đồng thời, gửi trùng và mức isolation? | |
| H7 | Test đề xuất có thể đỗ giả hoặc trượt giả không? | |

## ui — đặc tả màn hình
| # | Câu hỏi | Trả lời (mục/dòng, hoặc "không áp dụng vì …") |
|---|---|---|
| M1 | AC nói "luôn/mọi" thì ngoại lệ là gì (đã ghi vào AC hoặc báo chủ AC)? | |
| M2 | Mỗi lỗi có ca con nào cần xử lý khác nhau (ví dụ hết phiên khác lỗi tạm)? | |
| M3 | Hai luật cùng áp một màn (ví dụ cache cũ và tải lại lỗi) thì luật nào thắng? | |
| M4 | Sự kiện đến khi đang gửi hoặc đang mở hộp thoại thì sao? | |
| M5 | Prototype không mô phỏng ca nào? Bảng lệch đã so cả prototype lẫn luồng màn hình chưa? | |
| M6 | Chữ hiển thị có khẳng định hơn điều hệ thống thật sự đo hoặc làm được không? | |
