---
description: Viết báo cáo cuối ngày (PM)
---
> `<mgmt>` = thư mục quản lý của dự án (mặc định `management/`, cấu hình ở `.agent-ops.toml` mục `[paths]`).
Dùng agent `agent-ops:pm` với skill `agent-ops:daily-cadence` và `agent-ops:decision-requests` để viết báo cáo hôm nay.

1. Đối chiếu `<mgmt>/daily/<hôm nay>-plan.md` với trạng thái thực tế của các task và `git log` hôm nay.
2. Chạy test để lấy số liệu thật.
3. Mọi câu hỏi mới trong ngày phải đã thành phiếu DR và đi hết bước architect soạn → decision-reviewer phản biện. Phiếu nào chưa xong thì ghi rõ trong báo cáo, không đưa câu hỏi thô cho tôi.
4. Chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_inbox.py" --check` rồi `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_inbox.py"`.
5. Ghi `<mgmt>/daily/<hôm nay>-report.md` theo template, chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_board.py"`.
6. Trả lời tôi bằng phần tóm tắt 3 dòng + số phiếu cần tôi quyết + số quyết định tạm mới + link `<mgmt>/DECISIONS-INBOX.md`.

$ARGUMENTS
