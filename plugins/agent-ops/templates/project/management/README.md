# Hệ thống quản lý công việc

Toàn bộ công việc của dự án được quản lý bằng file Markdown trong thư mục này. Mọi agent đọc/ghi trực tiếp, lịch sử thay đổi nằm trong Git.

## 1. Cấu trúc thư mục
File hoặc thư mục chưa có sau khi khởi tạo (`risks.md`, `daily/`, `sprints/`, `change-requests/`, `archive/`, `retros/`) được tạo khi cần.

```
management/
├─ README.md                 ← file này (luật chơi)
├─ BOARD.md                  ← bảng tổng hợp trạng thái mọi task (sinh bằng `build_board.py`, không sửa tay)
├─ roadmap.md                ← giai đoạn, mốc, sprint
├─ decisions.md              ← nhật ký quyết định (D-xxx)
├─ decision-policy.md        ← phân loại quyết định loại 1 (PO) / loại 2 (agent tạm)
├─ DECISIONS-INBOX.md        ← hộp quyết định của PO (tự sinh, không sửa tay)
├─ decision-requests/        ← phiếu quyết định DR-xxx
├─ lessons/                  ← học từ lỗi: README (mã nhóm lỗi, bậc rào chắn), LESSONS.md, retros/
├─ risks.md                  ← danh sách rủi ro
├─ tasks/
│  └─ E01-project-setup/                 ← Epic
│     ├─ epic.md
│     └─ E01-T01-repo-skeleton/          ← Task lớn (1 ngày)
│        ├─ task.md
│        ├─ log.md                     ← mục 7 Trao đổi + mục 8 Lịch sử
│        ├─ E01-T01-S01-backend-skeleton.md   ← Subtask (≤ 6 giờ)
│        ├─ E01-T01-S02-frontend-skeleton.md
│        └─ evidence/                    ← ảnh chụp, log test, báo cáo QA
├─ daily/
│  ├─ 2026-10-30-plan.md
│  └─ 2026-10-30-report.md
├─ sprints/
│  └─ sprint-01.md
├─ change-requests/
│  └─ CR-001-<slug>.md
└─ archive/                  ← epic đã hoàn thành chuyển vào đây
```

## 2. Đánh mã (ID)
| Cấp | Mẫu ID | Ví dụ | Quy mô |
|---|---|---|---|
| Epic | `E<2 số>` | `E02` | Một nhóm tính năng, 1–4 tuần |
| Luồng | `F<2 số>` | `F01` | Một hành trình người dùng chạy được đầu-cuối: giao diện + backend + E2E |
| Task | `E<nn>-T<nn>` | `E02-T03` | **Hoàn thành trong 1 ngày**; **task luồng** (có `flow:`, gồm BE + FE + E2E) ≤ 3 ngày, ≤ 6 subtask |
| Subtask | `E<nn>-T<nn>-S<nn>` | `E02-T03-S02` | **≤ 6 giờ, ≤ 25 file, 1 commit** |
| Bug | `BUG-<3 số>` | `BUG-007` | Gắn vào task liên quan |
| Change Request | `CR-<3 số>` | `CR-002` | Thay đổi phạm vi |
| Phiếu quyết định | `DR-<3 số>` | `DR-012` | Một câu hỏi cần quyết |

Tên thư mục/file = `ID-slug-tieng-anh` (chữ thường, gạch ngang).

## 3. Trạng thái
```
backlog → ready → in_progress → in_review → in_qa → done
                       │            │          │
                       └──► blocked ◄┴──────────┘     (kèm lý do)
                    in_review / in_qa ──► in_progress  (bị trả lại, kèm nhận xét)
```
- `backlog`: mới ghi nhận, chưa đủ thông tin.
- `ready`: đạt **Definition of Ready**.
- `in_progress`: dev đang làm (mỗi dev chỉ 1 subtask `in_progress` cùng lúc).
- `in_review`: chờ code-reviewer (hoặc db-reviewer / idea-reviewer với tài liệu).
- `in_qa`: chờ QA nghiệm thu. Sửa code sau khi QA Passed thì task về `in_progress`, sửa và review lại; CI xanh ở commit mới mới về `in_qa`.
- `done`: đạt **Definition of Done**.
- `blocked`: kẹt, ghi rõ chờ ai/cái gì.

Trạng thái ghi ở **frontmatter** của file. Task lớn chỉ `done` khi mọi subtask `done` và QA nghiệm thu task.

## 4. Ai được sửa phần nào (quyền theo mục)
Mỗi file task chia thành các mục có chủ sở hữu. **Agent chỉ được ghi vào mục của mình**; muốn góp ý mục khác thì ghi vào "Trao đổi".

| Mục | Chủ sở hữu |
|---|---|
| Frontmatter (trạng thái, người làm, ngày) | PM (dev được đổi `in_progress`→`in_review`; reviewer/QA được đổi trạng thái kết quả của mình) |
| 1. Yêu cầu & Tiêu chí nghiệm thu | PM / product-analyst |
| 2. Thiết kế kỹ thuật | architect / db-designer / ui-designer |
| 3. Tiến trình thực hiện | dev được giao |
| 4. Review | code-reviewer / db-reviewer |
| 5. Nghiệm thu QA | qa |
| 6. Cần quyết định | chỉ chứa link tới phiếu DR (mọi agent thêm); nội dung nằm trong phiếu |
| 7. Trao đổi | mọi agent |
| 8. Lịch sử | mọi agent (chỉ thêm dòng, không sửa dòng cũ) |

Mục 7 và 8 nằm ở `log.md` cạnh `task.md` (mẫu `log.md` của plugin). Quyền theo mục không đổi.

## 5. Definition of Ready (được phép bắt đầu)
- [ ] Mô tả rõ ràng, có **tiêu chí nghiệm thu đo được** (dạng Given/When/Then hoặc checklist).
- [ ] Có thiết kế kỹ thuật nếu cần (hợp đồng API, thay đổi DB, màn hình).
- [ ] Mọi phụ thuộc đã `done`.
- [ ] Không còn câu hỏi mở ở mục "Cần quyết định".
- [ ] Đã chia subtask, mỗi subtask ≤ 6 giờ.
- [ ] Có ước lượng.

## 6. Definition of Done
- [ ] Code + test viết xong, **CI xanh ở commit đổi code cuối**, coverage không giảm. PR chỉ đổi tài liệu (CI không chạy): dùng CI xanh của commit đổi code gần nhất.
- [ ] Lint, type-check và kiểm tra kiến trúc của dự án đạt.
- [ ] Tài liệu API cập nhật (nếu đổi API).
- [ ] Điều kiện riêng của dự án (nếu có): ghi thêm tại đây.
- [ ] code-reviewer: **Approved**.
- [ ] QA: **Passed** toàn bộ tiêu chí nghiệm thu, có bằng chứng trong `evidence/`.
- [ ] Không còn TODO mà chưa có task.
- [ ] Đã chạy `build_board.py`; `build_inbox.py --check` 0 vấn đề (tool của plugin `agent-ops`).

## 7. Quy tắc vận hành
1. **Không làm ngoài kế hoạch.** Việc phát sinh → thêm task `backlog`, báo PM.
2. Danh sách task của ngày phải có trong `daily/<ngày>-plan.md` **trước khi code**.
3. Subtask vượt **1.5× ước lượng** → dừng, ghi vào "Trao đổi", PM chia nhỏ lại.
4. Thay đổi phạm vi → tạo `change-requests/CR-xxx.md`, PO duyệt mới làm.
5. Quyết định kỹ thuật quan trọng → viết ADR ở `docs/02-architecture/adr/`.
6. Gặp điểm mơ hồ → tạo **phiếu DR** (skill `agent-ops:decision-requests`): architect soạn đề xuất, decision-reviewer phản biện, phân loại theo `decision-policy.md`. Đổi task `blocked` nếu không làm tiếp được, chuyển việc khác. **Không đoán.**
7. Bị trả lại từ review/QA quá **2 lần** → PM báo lên PO trong báo cáo ngày.
8. Bug QA tìm thấy: nhỏ, trong phạm vi task → ghi ở mục QA và trả về `in_progress`; lớn hoặc ngoài phạm vi → tạo `BUG-xxx` trong backlog.
9. Lịch sử chỉ được **thêm**, không sửa/xoá dòng cũ.
10. Cuối mỗi ngày, PM chạy `/agent-ops:daily-report`; đầu ngày chạy `/agent-ops:daily-plan`.
11. **Truy vết quyết định hai chiều:** mỗi D-xxx trong `decisions.md` ghi các task/epic/ADR chịu ảnh hưởng ở cột *Áp dụng cho*; mỗi task ghi các D-xxx liên quan trong `links`. Hai phía phải khớp nhau.
12. **Ghi giờ:** chạy `date` lúc bắt đầu và lúc kết thúc mỗi subtask, ghi cả hai vào Tiến trình rồi tính `actual_hours` từ khoảng đó; không ước chừng.
13. **Đọc task theo mục:** không đọc nguyên `task.md`. Chạy `grep -n "^## " task.md` rồi đọc đúng đoạn (`sed -n a,bp` hoặc `Read` với `offset`/`limit`). Mỗi vai đọc:

    | Vai | Đọc | Không đọc (trừ khi brief chỉ định) |
    |---|---|---|
    | backend-dev, frontend-dev | frontmatter, 1, 2, Subtasks, dòng subtask của mình ở 3; vòng sửa: đúng `#n` ở 4/5 brief nêu | 4, 5 các vòng đã đóng; `log.md` |
    | code-reviewer, db-reviewer | 1 (AC), 2, 3; vòng 2+: bảng mục 4 vòng trước | 5; `log.md` |
    | qa | 1 (AC), 2 phần liên quan AC, "Ghi chú kỹ thuật cho người sau" ở 3, 5 | 4; `log.md` |
    | architect, db-designer, ui-designer, product-analyst | 1, 2; mục 7 (nhãn `GAP`/`CONFLICT`/`WRONG-ASSUMPTION`; task mới: trong `log.md`); đối chiếu mục 6 với 7, 8 | 3, 4, 5 |
    | pm | frontmatter, Subtasks, dòng **Kết quả:** của 4 và 5, 6; `log.md` khi kiểm DoD/lịch sử | thân mục 2 |

    Brief của phiên chính kèm ảnh chụp trạng thái (skill `agent-ops:task-management` § Giao việc) thay cho việc agent tự đọc lại mục của agent trước.
14. **Làn công việc:** pm/phiên chính chọn làn khi tạo task, ghi `lane:` ở frontmatter task. Code-reviewer luôn tách khỏi QA.
    - **L1** ý tưởng/tính năng mới chưa có PRD: product-analyst → idea-reviewer → [PO G0] → architect (hợp đồng API trước) → ui-designer + db-designer song song → review thiết kế (db-reviewer; architect soát UI; decision-reviewer cho phiếu DR) → [PO G1/G2] → L2.
    - **L2** task đã có thiết kế: dev (BE → FE) → code-reviewer → qa (theo AC) → close.
    - **L3** sửa nhỏ/chore (≤ ~5 file, không đụng schema/bảo mật/khoá): dev → code-reviewer (`effort: "medium"`) → qa chỉ kiểm AC liên quan.

## 8. Vòng đời một task (ví dụ)
```
PM tạo task (backlog) → product-analyst viết tiêu chí → architect viết thiết kế
→ task luồng: thiết kế luồng (architect + ui-designer) → duyệt
→ PM kiểm DoR, chia subtask → ready
→ dev: in_progress, ghi tiến trình từng subtask, commit
→ in_review: người làm đẩy nhánh, mở PR nháp (`gh pr create --draft`) để CI chạy cả bộ song song; code-reviewer ghi nhận xét → Approved / Changes requested
→ in_qa: qa chạy test của các AC, dẫn link CI xanh làm bằng chứng hồi quy → Passed / Failed
→ done: PM chạy build_board.py + `--check`, báo cáo ngày → PR bỏ nháp → merge
(không merge PR khi CI chưa xanh: `gh pr checks`)
```
Task luồng: BE và FE cùng nhánh `feat/<task-id>-<slug>`.

## 9. Tài liệu ghi đề xuất theo phiếu DR
Tài liệu còn chờ phiếu quyết định ghi dòng `> Trạng thái: đề xuất (DR-xxx)`; khi phiếu `decided`, `build_inbox.py --check` cảnh báo để sửa dòng này.
