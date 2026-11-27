# WCAG 2.2 AA — checklist chi tiết

Đọc khi thiết kế/code/review màn hình có form, media, tương tác phức tạp. Tóm tắt nằm ở `SKILL.md` mục A.3.

| # | Tiêu chí (mã WCAG) | Đúng | Sai |
|---|---|---|---|
| 1 | Tương phản chữ (1.4.3) ≥ 4.5:1; chữ ≥ 24px hoặc ≥ 18.7px đậm ≥ 3:1 | Chữ phụ `muted-foreground` đạt 4.5:1 trên nền | Placeholder xám nhạt dùng làm nhãn |
| 2 | Tương phản thành phần UI (1.4.11) ≥ 3:1 | Viền input, icon trạng thái, vòng focus | Viền input `#e5e7eb` trên nền trắng |
| 3 | Không chỉ dùng màu (1.4.1) | Đáp án sai: viền đỏ + icon ✗ + chữ "Chưa đúng" | Chỉ đổi nền sang đỏ |
| 4 | Kích thước vùng chạm (2.5.8, AA tối thiểu 24px; khuyến nghị 44px) | Nút loa phát âm 44×44 dù icon 20px | Icon 16px sát nhau trong danh sách |
| 5 | Focus nhìn thấy (2.4.7) và không bị che (2.4.11) | `focus-visible:ring-2` rõ; bottom bar không che phần tử đang focus | `outline: none` không thay thế |
| 6 | Bàn phím (2.1.1) | Thẻ lật: Space lật, phím số chọn mức; Esc đóng bottom sheet | Thao tác chỉ làm được bằng vuốt |
| 7 | Thao tác kéo có cách thay thế (2.5.7) | Sắp xếp kéo thả có thêm chế độ chạm chọn | Chỉ kéo thả |
| 8 | Nhãn và hướng dẫn (3.3.2) | `<label>` hiển thị cho mọi input; định dạng nêu trước | Chỉ có placeholder |
| 9 | Báo lỗi (3.3.1, 3.3.3) | Lỗi dưới ô, gắn `aria-describedby`, nói cách sửa | Toast "Có lỗi xảy ra" chung chung |
| 10 | Tên, vai trò, giá trị (4.1.2) | Icon button có `aria-label="Phát âm từ này"`; toggle có `aria-pressed` | `<div onClick>` làm nút |
| 11 | Thông báo trạng thái (4.1.3) | Kết quả chấm, "Đã thêm vào danh sách" qua `aria-live="polite"` | Thông báo chỉ hiện bằng hình |
| 12 | Ngôn ngữ của phần (3.1.2) | Từ/câu khác ngôn ngữ giao diện bọc `lang` đúng | Screen reader đọc từ ngoại ngữ bằng giọng sai |
| 13 | Media (1.2.x) | Audio có transcript (hiện sau khi làm bài nếu là bài kiểm tra) | Audio không có cách xem chữ |
| 14 | Thời gian (2.2.1) | Bài có giới hạn giờ cho phép tắt/kéo dài; luyện tập không giới hạn | Tự chuyển câu sau 5 giây |
| 15 | Chuyển động (2.3.3) | Hiệu ứng lật thẻ, hiệu ứng ăn mừng tắt khi `prefers-reduced-motion` | Animation không tắt được |
| 16 | Phóng to (1.4.4, 1.4.10) | Zoom 200% / rộng 320px không mất nội dung, không cuộn ngang | Khung cố định chiều cao cắt chữ |
| 17 | Xác thực dễ dùng (3.3.8) | Cho dán mật khẩu, dùng trình quản lý mật khẩu, mã 2FA nhận dán | Chặn paste ô mật khẩu |
| 18 | Thứ tự focus (2.4.3) và tiêu đề (2.4.2, 2.4.6) | Mỗi route có `<title>` và một `<h1>`; mở modal → focus vào modal, đóng → trả focus | Focus nhảy về đầu trang sau khi đóng dialog |

Kiểm tự động: `@axe-core/playwright` bắt được khoảng 30–40% lỗi; các mục 3, 6, 7, 11, 12, 14 cần kiểm tay.
