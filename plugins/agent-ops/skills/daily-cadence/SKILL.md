---
name: daily-cadence
description: Cách lập kế hoạch ngày và viết báo cáo ngày cho Product Owner. Dùng cho /daily-plan, /daily-report, và khi tổng kết sprint.
---

# Nhịp làm việc hằng ngày

## Đầu ngày — kế hoạch (`management/daily/YYYY-MM-DD-plan.md`)
1. Đọc báo cáo ngày gần nhất, `BOARD.md`, `decisions.md`, `DECISIONS-INBOX.md` (có quyết định mới của PO không? quyết định tạm nào bị bác?).
2. Áp dụng các quyết định mới vào task liên quan, gỡ `blocked` nếu được.
3. Chọn task: ưu tiên (a) task bị trả lại, (b) task `ready` theo thứ tự ưu tiên & phụ thuộc. Tổng ước lượng ≤ ~6 giờ làm việc agent.
4. Mục tiêu ngày phải là **kết quả PO nhìn thấy được** ("API thêm một mục dữ liệu chạy được trên trang tài liệu API"), không phải hoạt động ("làm API").
5. Ghi theo `${CLAUDE_PLUGIN_ROOT}/templates/daily-plan.md`.

## Cuối ngày — báo cáo (`management/daily/YYYY-MM-DD-report.md`)
1. Đối chiếu kế hoạch với thực tế từng task (đọc mục Lịch sử, `git log --since=midnight`).
2. Chạy test để lấy chỉ số thật, không ước đoán.
3. Mọi câu hỏi mới phải đã thành phiếu DR và qua architect → decision-reviewer (skill `agent-ops:decision-requests`). Chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_inbox.py" --check` rồi build inbox; mục ⚠️ của báo cáo chỉ tóm tắt số lượng + phiếu gấp nhất, dẫn link tới inbox.
4. Nêu bất thường: vượt ước lượng, bị trả lại > 2 lần, blocked > 1 ngày.
5. Ghi theo `${CLAUDE_PLUGIN_ROOT}/templates/daily-report.md`. Phần tóm tắt 3 dòng đầu tiên phải đủ để PO đọc trong 30 giây.

## Cuối tuần — retro
Chạy `/retro` (skill `agent-ops:lessons-learned`). Đầu ngày nếu retro gần nhất quá 7 ngày → nhắc PO.

## Cuối sprint (1 tuần)
Cập nhật `management/sprints/sprint-NN.md`: kết quả, demo cho PO (liệt kê cách tự thử), retro 3 ý.
