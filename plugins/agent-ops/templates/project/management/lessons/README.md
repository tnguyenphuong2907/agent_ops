# Bài học kinh nghiệm — cách đội tự cải thiện

> Agent không tự học giữa các phiên. "Trưởng thành" = **bộ luật và công cụ kiểm tra của đội tốt dần lên** sau mỗi lỗi.
> Quy trình chi tiết: skill `agent-ops:lessons-learned`. Duyệt thay đổi luật: theo từng đợt retro.

## 1. Mã nhóm lỗi (cột "Nhóm" trong mọi bảng review / phản biện / QA)
| Mã | Nghĩa | Ví dụ |
|---|---|---|
| `TRACE` | Thiếu/sai dẫn nguồn; dùng nguồn chưa duyệt (bản nháp) như sự thật; đọc sai một D-xxx | không nhắc quyết định liên quan; coi bản nháp là đã chốt |
| `DRIFT` | Lệch giữa các tài liệu; một quy định được chép ở nhiều nơi | skill nói khác tài liệu chủ |
| `OVERCLAIM` | Khẳng định mạnh hơn thiết kế thật sự bảo đảm | "đã bị chặn" nhưng admin tự gỡ được |
| `OPTIONS` | Thiếu phương án hợp lý (phương án lai, "để sau"); so sánh không công bằng | |
| `IMPACT` | Thiếu hệ quả / `affects`; PO duyệt ngầm một quy tắc không được nêu; phụ thuộc vào việc chưa ai được giao | sửa ADR đã duyệt mà tóm tắt không nói |
| `SCOPE` | Lọt hoặc thiếu phạm vi | thêm tính năng không nằm trong phương án |
| `ESTIMATE` | Ước lượng công sức / chi phí / thời gian lệch | "0,5 ngày" cho việc của 4 endpoint |
| `DOMAIN` | Thiếu hiểu biết nghiệp vụ | đề xuất đúng kỹ thuật nhưng sai với cách người dùng làm việc |
| `SEC` | Bảo mật, dữ liệu cá nhân | |
| `CLARITY` | Mơ hồ, nhiều cách hiểu, không rõ áp dụng khi nào | |
| `PROC` | Sai quy trình (trạng thái, quyền theo mục, vòng đời phiếu, tự nghiệm thu) | |
| `TEST` | Thiếu test, test sai, fixture mơ hồ | |
| `CODE` | Chất lượng code, hiệu năng, kiến trúc | |

Không chắc → chọn mã gần nhất và ghi thêm trong nhận xét. Có thể ghi 2 mã: `IMPACT,SCOPE`.

## 2. Bậc thang rào chắn (luôn chọn bậc cao nhất làm được)
| Bậc | Rào chắn | Nằm ở đâu |
|---|---|---|
| **3** | Kiểm tra tự động | tool kiểm tra, CI, hook Claude Code |
| **2** | Dòng checklist | skill liên quan (`code-review-checklist`, `decision-requests`…) hoặc mẫu (template) |
| **1** | Dòng nhắc "Lỗi hay gặp" | cuối file agent (tối đa 10 dòng / agent) |

## 3. Quy tắc
1. Một nhóm lỗi lặp lại **≥ 2 lần** trong một tuần, hoặc 1 lần mức Blocker → **bắt buộc** có bài học `LL-xxx` và đề xuất rào chắn.
2. Bài học phải có **nguyên nhân gốc** (hỏi "tại sao" tới khi ra nguyên nhân sửa được), không dừng ở "agent sơ ý".
3. Agent **không tự sửa** file agent, skill, `CLAUDE.md`, `decision-policy.md`. Mọi đề xuất sửa luật gom thành **một phiếu DR mỗi đợt retro**; PO duyệt.
4. Giữ gọn: mỗi agent tối đa 10 dòng "Lỗi hay gặp". Dòng đã có rào chắn bậc 3, hoặc 4 tuần liền không tái phạm → đề xuất bỏ ở retro.
5. Rào chắn đã áp dụng mà nhóm lỗi **không giảm** sau 2 tuần → rào chắn chưa đủ, phải nâng bậc.

## 4. File
- `LESSONS.md` — sổ bài học LL-xxx.
- `retros/YYYY-Www.md` — báo cáo retro hằng tuần (mẫu: `templates/retro.md` của plugin).
- Số liệu: `python3 "<plugin>/tools/retro_stats.py" [--since YYYY-MM-DD] [--dump file.csv]`.
