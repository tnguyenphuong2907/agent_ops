---
id: DR-000
title: "<Câu hỏi ngắn, kết thúc bằng dấu ?>"
form: short           #phiếu ngắn. Chỉ dùng khi tích được đủ 5 điều kiện ở mục 3
type: 2               # phiếu ngắn luôn là loại 2 (kể cả siết nhất quán thuộc bảo mật)
policy_rule:          # "2 (siết nhất quán, D-xxx)" hoặc "2 (<nhóm loại 2>)"
status: draft         # draft | in_review | provisional | decided | withdrawn  (không có open)
topic:                # scope | security | cost | architecture | data | learning | ops | ux
asked_by:
proposal_by: architect
reviewer: decision-reviewer
blocks: []
affects: []
related: []           # D-xxx đang được áp theo, ADR, DR khác
deadline:
created:
decided_as:
---

# DR-000 — <Câu hỏi>

> Phiếu ngắn: tối đa ~1 trang. Không bảng phương án, không phản chứng, không mục 10. Cần nhiều hơn thế là dấu hiệu phải dùng phiếu đầy đủ (`decision-request.md`).

## 1. Vấn đề  ·  _người hỏi_
<2–3 câu: gặp ở đâu (task, file, dòng), chỗ nào sót hoặc chưa rõ.>

## 2. Cách sửa  ·  _architect_
**Chọn: <một câu>**
<1–3 câu: làm gì, áp theo quy tắc nào (D-xxx / ADR, mục), công sức.>

## 3. Điều kiện phiếu ngắn  ·  _architect tích, decision-reviewer kiểm_
- [ ] **Loại 2**, hoặc **siết nhất quán**: áp đúng quy tắc của <D-xxx/ADR mục …> đã chốt sang chỗ tương đương bị sót, chỉ làm **chặt hơn**, không nới.
- [ ] **Không tốn tiền** (không dịch vụ mới, không tăng chi phí định kỳ).
- [ ] **Không thêm hoặc giữ thêm dữ liệu người dùng.**
- [ ] **Dễ đảo lại** (cách đảo ở mục 4).
- [ ] **Chỉ một hướng hợp lý**: không có phương án khác mà PO có lý do để chọn.

## 4. Cách đảo lại  ·  _architect_
<1 câu: bỏ gì, sửa file nào.>

## 5. Kiểm nhanh  ·  _decision-reviewer (1 lượt, ≤ 100 chữ)_
**Kết luận:** ⏳  <!-- ✅ Đủ 5 điều kiện → provisional | ⬆️ Thiếu điều kiện → chuyển phiếu đầy đủ -->
**Lời nhắn cho PO:** ⏳  <!-- 1 câu -->

## Lịch sử
| Thời gian | Ai | Thay đổi |
|---|---|---|
