---
id: DR-000
title: "<Câu hỏi ngắn, kết thúc bằng dấu ?>"
type:                 # 1 | 2  (architect đề xuất theo decision-policy.md; reviewer xác nhận)
policy_rule:          # ví dụ 1.5 (bảo mật) hoặc 2 (tham số kỹ thuật)
status: draft         # draft | in_review | open | provisional | decided | withdrawn
topic:                # scope | security | cost | architecture | data | learning | ops | ux
asked_by:
proposal_by: architect
reviewer: decision-reviewer
blocks: []            # task bị chặn tới khi có quyết định, ví dụ [E01-T05]
affects: []           # task / epic / ADR chịu ảnh hưởng (→ cột "Áp dụng cho" của D-xxx)
related: []           # D-xxx, ADR, DR khác
deadline:             # YYYY-MM-DD — ngày muộn nhất trước khi task bị chặn
created:
decided_as:           # D-xxx khi đã quyết
# supersedes: DR-xxx  # chỉ thêm khi phiếu này mở lại phiếu đã decided (skill decision-requests mục 5, P10)
---

# DR-000 — <Câu hỏi>

## 1. Câu hỏi & bối cảnh  ·  _người hỏi_
<Gặp vấn đề này ở đâu (task, file, dòng), vì sao không tự quyết được.>

## 2. Tóm tắt 30 giây  ·  _architect_
<1–2 câu: câu hỏi và đề xuất. Hồ sơ đủ để PO quyết nằm ở mục 10, không lặp ở đây.>

## 3. Phương án  ·  _architect_
**Bài toán gốc:** <việc thật cần giải, 1 câu, không nhắc phương án>
**Ràng buộc bỏ được:** <ràng buộc hoặc trạng thái nào, kể cả D-xxx đã chốt>
**Phương án bỏ ràng buộc:** <chữ cái phương án trong bảng>
**Đã cân nhắc phương án lai / để sau?** <có/không; nếu có nêu phương án lai hoặc phần để sau, nếu không nêu lý do>

| Tiêu chí | A. … | B. … | C. … |
|---|---|---|---|
| Trải nghiệm người học | | | |
| Công sức | | | |
| Chi phí | | | |
| Rủi ro / bảo mật | | | |
| Đảo ngược được? | | | |

**A. …** — chi tiết
**B. …** — chi tiết

## 4. Đề xuất  ·  _architect_
**Chọn: …**
Lý do:
-
Phân loại: **Loại _**, theo quy tắc `decision-policy.md` mục _.
**Vì sao không phiếu ngắn:** <chỉ phiếu loại 2: điều kiện nào ở `decision-policy.md` mục 1b không đạt; loại 1 thì xoá dòng này>

## 5. Bằng chứng & tham chiếu  ·  _architect_
> Mỗi nhận định ở trên phải có ít nhất một dòng ở đây. Link nội bộ dạng `[tên](../../đường/dẫn.md#tieu-de-muc)`, link ngoài gắn nhãn theo skill `decision-requests` mục 2.
- Quyết định liên quan:
- Tài liệu trong repo:
- Nguồn ngoài:
- Ý kiến product-analyst (bắt buộc khi `topic: learning`; ghi "không áp dụng" nếu topic khác): <tóm tắt ý kiến, ngày, link>

## 6. Ảnh hưởng nếu chọn  ·  _architect_
| Phương án | Task/file thay đổi | Công sức thêm | Ghi chú |
|---|---|---|---|

**D-xxx/ADR bị sửa hoặc diễn giải:** <ID và điểm bị sửa/diễn giải, hoặc "Không">
**Quy tắc PO duyệt kèm:** <quy tắc đi kèm khi chọn, hoặc "Không">
**Phụ thuộc mới (ai làm):** <thư viện/dịch vụ/việc mới và người làm, hoặc "Không">
**Thứ bị loại khỏi phạm vi:** <điều không làm nữa hoặc để sau, hoặc "Không">
**Công sức theo slice:** <mỗi slice/task một dòng, theo giờ>
**Thời gian của PO:** <PO phải làm gì, bao lâu, hoặc "Không">

## 7. Phản biện  ·  _decision-reviewer (tối đa 2 vòng, ~400 chữ/vòng, ≤ 5 nhận xét quan trọng)_
### Vòng 1 (YYYY-MM-DD)
**Kết luận:** ⏳  <!-- ✅ Tin được đề xuất | 🔄 Nên chọn phương án khác | ❓ Chưa đủ để quyết | ⬇️ Không cần PO -->
**Lời nhắn cho PO:** ⏳  <!-- 2–3 câu viết cho PO -->
| # | Mức độ | Nhóm | Nhận xét (vì sao đổi lựa chọn) | Đề xuất |
|---|---|---|---|---|

**Lưu ý khi làm:** _(không chặn phiếu; PM chuyển sang task khi quyết)_
-

## 8. Phản hồi của architect  ·  _architect (tối đa 1 lượt, giữa vòng 1 và vòng 2)_
**Quy tắc:** +_ / −_ (so với bản vòng 1, không tính phần luật khác đã làm)
-

## 9. Hỏi thêm  ·  _PO hỏi qua `/explain`, agent trả lời_
<!--
### H1 (YYYY-MM-DD): <câu hỏi của PO>
**Trả lời (<agent>):** … (kèm link nguồn)
-->

## 10. Hồ sơ quyết định cho PO  ·  _architect viết khi soạn; decision-reviewer kiểm và điền dòng của mình ở lượt kết luận; PO chỉ cần đọc mục này_
> Tóm từ mục 2–8, không thêm phân tích mới, tối đa ~300 chữ. architect để trống dòng **decision-reviewer** và **Còn bất đồng**; reviewer điền.

**Câu hỏi:** <một câu>
**Vì sao cần anh/chị:** quy tắc 1._ — <một câu> · **Chặn:** <task> · **Hạn:** <ngày> · **Nếu chậm:** <một câu>

| Phương án | Là gì | Được | Mất | Công sức / chi phí |
|---|---|---|---|---|

**architect đề xuất:** <X> — <lý do 1–2 câu>
**decision-reviewer:** <✅/🔄/❓/⬇️> — <lời nhắn cho PO>
**Còn bất đồng:** <mỗi điểm 1 dòng: architect nói…, reviewer nói…> hoặc "Không"
**Chọn <X> thì anh/chị cũng đồng ý luôn:** <quy tắc / hệ quả đi kèm> hoặc "Không có gì thêm"
**Khó đảo ngược / tốn kém nếu đổi sau:** <…> hoặc "Đổi lại dễ"
**Đọc thêm (nếu muốn):** mục 3 (phương án đầy đủ), mục 7 (phản biện)
**Trả lời:** `/decide DR-000 <phương án>` · hỏi thêm: `/explain DR-000 <câu hỏi>`

### Quyết định
- Lựa chọn:
- Ghi chú / điều kiện:
- Ghi nhận: D-xxx

## Lịch sử
| Thời gian | Ai | Thay đổi |
|---|---|---|
