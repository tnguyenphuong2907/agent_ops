---
name: decision-requests
description: Quy trình phiếu quyết định (DR) - tạo phiếu, architect soạn, decision-reviewer phản biện, phân loại loại 1/loại 2, cập nhật DECISIONS-INBOX, trả lời /explain, ghi /decide. Dùng khi cần PO quyết, hoặc cần một quyết định chưa có trong decisions.md.
---

# Phiếu quyết định (DR)

Chính sách phân loại: `management/decision-policy.md`. Mẫu: `${CLAUDE_PLUGIN_ROOT}/templates/decision-request.md`. Phiếu nằm ở `management/decision-requests/DR-<3 số>-<slug>.md`. Hộp quyết định: `management/DECISIONS-INBOX.md` (tự sinh).

## Vòng đời
```
draft ──(architect soạn, gồm mục 10)──► in_review ──(decision-reviewer)──┬─ ✅ ──► reviewer điền dòng của mình ở mục 10 ─┬─► open         (loại 1: chờ PO)
  ▲                              │                            ├─ ⬇️ ──► reviewer điền dòng của mình ở mục 10 ─┴─► provisional  (loại 2 / hạ loại: áp dụng tạm)
  └── 🔄 / ❓ / lỗi --check ──────┘  (vòng 2 là vòng cuối: còn 🔄 hoặc ❓ → open, PO thấy cả hai ý kiến)
open / provisional ──(/decide)──► decided        ·   bất kỳ lúc nào ──► withdrawn
```

## 0. Tự chạy tới khi cần PO
- Phiếu vừa tạo → **phiên chính tự chạy hết các bước** (architect soạn mục 1–6 và mục 10 → `--check` → decision-reviewer → architect sửa nếu cần → decision-reviewer vòng 2, điền dòng reviewer ở mục 10, đặt trạng thái → `build_inbox.py`; pm chỉ vào ở `/decide`) **trong cùng lượt làm việc**, không hỏi PO giữa chừng, không đưa PO bản nháp hay phản biện dở dang.
- Chỉ báo PO khi: phiếu tới `open` / `provisional`, hoặc phải dừng theo giới hạn vòng; ngoài ra báo sớm theo token (R8, mục 7), chỉ là báo, phiên chính chạy tiếp. Khi báo: **dẫn tới mục 10**, không tóm lại theo cách khác.
- Cần ý kiến chuyên môn (product-analyst, db-designer, ui-designer) → phiên chính tự giao, không hỏi PO.
- Câu hỏi phụ phát sinh trong lúc chạy mà agent trả lời được bằng tài liệu / D-xxx → tự trả lời trong phiếu, không tạo phiếu mới.
- **Gom cụm:** 2 phiếu trở lên cùng chủ đề, cùng nguồn (ví dụ cùng một spike, cùng một ADR) và mở trong cùng đợt → **một agent architect soạn cả cụm**, rồi **một agent decision-reviewer phản biện cả cụm** (mỗi phiếu vẫn một câu hỏi, một mục 7 riêng, vòng đếm riêng). Phiếu nào phải sang vòng 2 thì vòng 2 gom các phiếu còn lại của cụm. Brief ghi danh sách phiếu và nguồn chung đọc một lần.

## 0b. Phiếu ngắn
Trước khi soạn, architect hỏi: **đủ điều kiện phiếu ngắn ở `decision-policy.md` mục 1b chưa?** (loại 2 hoặc siết nhất quán · không tốn tiền · không thêm dữ liệu người dùng · dễ đảo lại · chỉ một hướng hợp lý). Đủ → dùng `${CLAUDE_PLUGIN_ROOT}/templates/decision-request-short.md`:
1. architect điền mục 1–4, tích 5 điều kiện, `--check` tới 0 lỗi → `in_review`. Không bảng phương án, không phản chứng, không nhãn tham chiếu.
2. decision-reviewer **một lượt**, ≤ 100 chữ ở mục 5: ✅ đủ điều kiện → reviewer đặt `provisional`; phiên chính ghi D-xxx **⏳ tạm (agent, phiếu ngắn)**, `decided_as`, áp vào task, chạy `build_inbox.py`. ⬆️ thiếu điều kiện → architect chép mục 1 sang phiếu đầy đủ (bỏ `form: short`), chạy quy trình thường.
3. Không có mục 10, không báo PO riêng: PO thấy ở nhóm quyết định tạm của hộp quyết định (⚡).

Phân vân giữa phiếu ngắn và đầy đủ → phiếu đầy đủ.

## 1. Người gặp câu hỏi (mọi agent)
1. Kiểm `management/decisions.md` và các phiếu đang mở — đã có câu trả lời hoặc phiếu trùng chưa? Có thì dùng/thêm vào `affects` của phiếu đó. **Phiếu đã `decided`: đọc `decided_as` ở frontmatter và dòng D-xxx đó trong `decisions.md` là đủ**; chỉ mở thân phiếu khi cần đúng một mục (Grep tiêu đề rồi đọc mục đó).
2. Nếu là **việc PO cần làm** (không phải quyết định) → báo PM ghi vào mục *Việc bạn cần làm* của inbox, không tạo phiếu.
3. Tạo phiếu mới: số tiếp theo theo các file trong thư mục, copy template, điền frontmatter (`asked_by`, `blocks`, `affects`, `created`, `deadline`), viết **mục 1** (gặp ở đâu — task, file, dòng; vì sao không tự quyết được). `status: draft`.
4. Trong mục 6 của task chỉ ghi một dòng: `- [DR-012](../../../decision-requests/DR-012-….md) — <câu hỏi>`. Nếu không làm tiếp được → task `blocked`, chuyển việc khác.
5. Mỗi phiếu **một câu hỏi**. Chỉ gộp câu phụ vào cùng phiếu khi cùng dữ liệu, cùng vòng đời và cùng quy tắc policy; thiếu một điều kiện thì tách phiếu. Ngoại lệ: phiếu retro.
6. Mở lại phiếu đã `decided`: không sửa phiếu cũ, tạo phiếu mới ghi `supersedes: DR-xxx` ở frontmatter, theo điều kiện ở mục 5 của skill này (`/explain`).

## 2. architect soạn đề xuất (mục 2–6)
- Hỏi ý kiến chuyên môn khi cần: product-analyst (phạm vi, sư phạm), db-designer (dữ liệu), ui-designer (giao diện) — ghi ý kiến của họ vào mục 5 kèm tên.
- 2–4 phương án, luôn cân nhắc phương án "để sau / không làm".
- Mục 3 mở đầu bằng 3 dòng Bài toán gốc / Ràng buộc bỏ được / Phương án bỏ ràng buộc. Phương án đó nằm trong 2–4 phương án; đề xuất bác nó thì ghi lý do.
- **Mọi nhận định phải có tham chiếu ở mục 5**: link tới file + tiêu đề mục (`[security.md § Quản lý khoá](../../docs/07-security/security.md#quản-lý-khoá)`), D-xxx, ADR, hoặc nguồn ngoài có tên. Không có nguồn → ghi rõ "suy luận của architect".
- **Nhãn trạng thái cho mỗi tham chiếu:** đặt nhãn ngay trước tham chiếu, cùng dòng.
  - `[đã duyệt]`: PO đã chốt (D-xxx không mang nhãn tạm, ADR `accepted`, tài liệu đã qua cổng). Ví dụ: `[đã duyệt] D-xxx: trần 2 vòng cho mỗi phiếu.`
  - `[nháp]`: chưa chốt (ADR `proposed`, phiếu chưa `decided`, D-xxx nhãn ⏳ tạm). Ví dụ: `[nháp] ADR-NNNN (proposed): …`
  - `[suy luận]`: không có nguồn, ghi kèm người suy luận. Ví dụ: `[suy luận] của architect: …`
  - `[ngoài, đọc YYYY-MM-DD]`: nguồn ngoài, kèm ngày đọc. Ví dụ: `[ngoài, đọc 2026-11-07] [Tên tài liệu](https://…)`. Regex chính xác để `--check` dùng, so trên chuỗi NFC: `\[ngoài, đọc \d{4}-\d{2}-\d{2}\]`
- **"Diễn giải D-xxx: …":** dựa vào cách đọc một quyết định thì ghi rõ là diễn giải. Ví dụ: `Diễn giải D-xxx: "phiếu tạo sau ngày duyệt" không gồm phiếu tạo đúng ngày 2026-11-05.`
- **Kịch bản phản chứng:** câu 'chặn / bảo đảm / không thể / luôn / tốt nhất', khi là khẳng định về hiệu quả hoặc an toàn của phương án, phải kèm kịch bản phản chứng đã thử. Ví dụ: `--check chặn link ngoài thiếu ngày đọc ở mục 5. Phản chứng đã thử: phiếu mới thiếu nhãn → bị báo; phiếu tạo từ 2026-11-05 trở về trước → không kiểm, nên câu chỉ đúng với phiếu mới.`
- **Bước rà soát trong phương án:** phương án có bước rà soát phải nêu ai rà; người rà không phải người làm.
- **architect viết mục 10 hoàn chỉnh** (không chỉ nháp), theo mẫu, ~300 chữ, sau cùng, chỉ tóm mục 2–6, không thêm phân tích mới; để trống 2 dòng của reviewer. Mục 2 chỉ **1–2 câu** (câu hỏi + đề xuất), không lặp mục 10.
- **Phiếu loại 2 dùng mẫu đầy đủ** phải ghi ở mục 4 dòng `**Vì sao không phiếu ngắn:** <điều kiện nào ở decision-policy.md mục 1b không đạt>`; `--check` báo lỗi nếu thiếu.
- **Đọc nguồn theo brief:** brief của phiên chính liệt kê file + mục + D-xxx cần đọc. Đọc thêm ngoài danh sách chỉ khi thiếu thật, và ghi một dòng "đọc thêm: <file> vì …" ở Lịch sử.
- Phân loại theo `decision-policy.md`: loại 1 phải chỉ ra quy tắc 1.x cụ thể + một câu lý do, ghi vào `policy_rule`. Không chỉ ra được → loại 2. Chi tiết triển khai của một quyết định loại 1 đã chốt → loại 2 (trừ 1.5, 1.6, 1.7, 1.9). Siết nhất quán (mục 1b) → loại 2 kể cả 1.5, thường dùng phiếu ngắn (mục 0b).
- Phiếu là để **chọn hướng**, không phải đặc tả: chi tiết thiết kế (tên trường, từng trạng thái, chữ trên màn hình) để cho user story / ADR / task, ghi một dòng "sẽ đặc tả ở …".
- Chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_inbox.py" --check` cho tới khi phiếu không còn lỗi → `status: in_review`.

## 3. decision-reviewer phản biện (mục 7)
Theo agent `decision-reviewer`: phép thử "PO có chọn khác đi không?", tối đa 5 nhận xét quan trọng, một trong 4 kết luận.
- **Trần 2 vòng, không ngoại lệ.** Một vòng là một lượt decision-reviewer ghi nhận xét, ở bất kỳ mục, trạng thái nào; mỗi vòng có một dòng Lịch sử.
- 🔄 / ❓ ở vòng 1 → trả architect, giữ `in_review`. architect phản hồi ở **mục 8** (1 lượt), rồi vòng 2.
- Vòng 2 chỉ kiểm các điểm của vòng 1. Sau vòng 2 còn 🔄 hoặc ❓ → `open`, mục 10 ghi rõ "Còn bất đồng".
- ✅ → loại 1: `open`; loại 2: `provisional`.
- ⬇️ → `provisional` (nhãn ⬇️ hạ loại).
- *Lưu ý khi làm* không bao giờ làm phiếu quay lại architect.
- **Ở lượt kết luận (✅ / ⬇️, hoặc hết vòng 2), decision-reviewer:** kiểm mục 10 khớp mục 3–8 (sai lệch → sửa thẳng mục 10, ghi Lịch sử); điền dòng `**decision-reviewer:**` và `**Còn bất đồng:**`; thêm nhãn "có thể sai câu hỏi" nếu R3; đặt `status`; chạy `build_inbox.py --check` tới 0 lỗi rồi `build_inbox.py`. Mục 10 không gọn trong ~300 chữ → ghi chỗ chưa gọn ở "Còn bất đồng", không trả architect thêm vòng.

## 3b. Mục 10 "Hồ sơ quyết định cho PO"
- architect viết (mục 2), decision-reviewer kiểm và điền phần của mình (mục 3). **pm không tham gia trước `/decide`.** Lý do: pm chỉ tóm lại nội dung có sẵn mà tốn một agent 15–30K; độc lập của hồ sơ do reviewer kiểm.
- Mục 10 phải đủ để PO quyết mà không đọc mục khác: câu hỏi, vì sao cần PO, phương án (được/mất/công sức), đề xuất của architect, kết luận + lời nhắn của reviewer, bất đồng còn lại, những gì PO đồng ý kèm theo, điều khó đảo ngược, cách trả lời.
- Loại 2 / ⬇️: **phiên chính** ghi D-xxx nhãn **⏳ tạm (agent)** (⬇️ thì ghi thêm "hạ loại"), điền `decided_as`, chép *Lưu ý khi làm* sang task, chạy `build_inbox.py`.

## 4. Sau mỗi thay đổi phiếu
Agent vừa sửa phiếu chạy `python3 "${CLAUDE_PLUGIN_ROOT}/tools/build_inbox.py"` để cập nhật inbox. Báo cáo ngày dẫn tới inbox thay vì chép lại nội dung phiếu.

## 5. `/explain DR-xxx <câu hỏi>`
- Người trả lời: architect (mặc định) hoặc agent chuyên môn phù hợp.
- Ghi vào **mục 9** dạng `### H<n> (ngày): <câu hỏi>` + `**Trả lời (<agent>):** …`, kèm tham chiếu như mục 5.
- Câu trả lời làm đổi đề xuất/phương án, hoặc thêm quy tắc, là đổi đề xuất. Còn vòng: cập nhật mục 3–6, ghi Lịch sử, về `in_review`, decision-reviewer xem phần đổi, tính một vòng. Hết vòng: cập nhật, giữ `open`, phần đổi ghi `[chưa phản biện]` ở mục 9. Phiếu `decided`: mục 9 chỉ hỏi đáp, không sửa mục 3–6; muốn đổi thì mở phiếu mới `supersedes`, chỉ khi PO yêu cầu hoặc đồng ý. Vòng đếm riêng từng phiếu.

## 6. `/decide`
- PO có thể trả lời nhiều phiếu một lúc: `DR-012 A, DR-013 đồng ý đề xuất, DR-015 B nhưng 30 ngày`.
- "Đồng ý đề xuất" = chọn phương án ở dòng **Chọn:** của mục 4 (cũng là dòng "architect đề xuất" ở mục 10).
- Chép các dòng *Lưu ý khi làm* của mục 7 sang mục 7 "Trao đổi" của các task trong `affects` (hoặc user story liên quan).
- PM: ghi D-xxx mới trong `decisions.md` (cột *Áp dụng cho* = `affects` của phiếu, Ghi chú dẫn `DR-xxx`), điền mục 10, `decided_as`, `status: decided`; cập nhật `links` của task, gỡ `blocked`; rebuild inbox.
- PO bác một quyết định tạm → D-xxx mới ghi "thay thế D-yyy"; task đã làm theo quyết định tạm → PM tạo task sửa.

## 7. Giao vòng phiếu cho agent mới
Mỗi bước (architect soạn → decision-reviewer phản biện → architect phản hồi mục 8 → decision-reviewer kết luận) là **một agent mới**, theo skill `agent-ops:agent-orchestration` và mục "Giao vòng review / sửa cho agent mới" của skill `agent-ops:task-management`. Brief cho phiếu ghi thêm:
- Chỉ đọc phiếu DR-xxx (mục cần cho vòng đó) + các D-xxx phiếu dẫn (Grep trong `decisions.md`) + mục PRD liên quan (đường dẫn PRD: `.claude/project-profile.md`).
- **Brief cho architect lượt soạn** liệt kê sẵn nguồn: nơi phát sinh câu hỏi (task + mục), D-xxx liên quan, ADR/PRD + mục, số liệu (file spike). Phiên chính đã biết các nguồn này khi tạo phiếu; không để architect tự dò cả repo.
- Vòng mấy của mục 7; các `#n` đã chốt; bất đồng còn giữ (ví dụ "D-xxx và D-yyy va nhau — để PO quyết").
- Không đọc lại các phiếu DR khác trừ khi phiếu này dẫn tới một mục cụ thể của chúng.
- **Gắn nhãn (phiên chính, R3):** sau mục 8, nếu `a > b` (`+a / −b` khai ở dòng `Quy tắc`) → decision-reviewer vòng 2 ghi mục 10 nhãn "có thể sai câu hỏi"; vòng 2 vẫn chạy bình thường.
- **Báo sớm (phiên chính, R8):** sau mỗi lượt agent của phiếu, gồm `/explain`, lấy số token ở thông báo hoàn thành, thêm `· ~NK` vào dòng Lịch sử của lượt đó. Tổng quá **200K** → báo PO ngay trong lượt trả lời kế tiếp, kèm bài toán gốc trong 3 câu, ghi `đã báo R8` vào Lịch sử. Báo một lần mỗi phiếu; chỉ báo, không dừng. Xem lại ngưỡng sau 5 phiếu.
