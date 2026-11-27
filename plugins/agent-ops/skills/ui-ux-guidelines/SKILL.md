---
name: ui-ux-guidelines
description: Nguyên tắc UI/UX chung cho thiết kế (ui-designer) và triển khai giao diện (frontend-dev) - quy trình thiết kế, heuristics, accessibility WCAG AA, trạng thái màn hình, mẫu UX cho app học, checklist so khớp spec. Dùng khi thiết kế, code hoặc review màn hình.
---

# UI/UX Guidelines

Token màu/chữ/spacing: file chủ là `docs/03-design/design-system.md` (skill này không chép token). Cấu trúc code: skill dự án về feature frontend (profile).

## A. Nguyên tắc chung (cả hai role)
1. **Một màn hình, một việc chính.** Một nút chính (primary) mỗi màn hình; hành động phụ dùng secondary/ghost.
2. **Heuristics Nielsen**, ưu tiên: trạng thái hệ thống luôn hiển thị; ngôn ngữ người dùng (ngôn ngữ đời thường của người dùng, không thuật ngữ kỹ thuật); cho phép hoàn tác thay vì hỏi xác nhận; nhất quán; phòng lỗi trước khi báo lỗi; nhận ra thay vì phải nhớ.
3. **Accessibility (WCAG 2.2 AA):**
   - Tương phản chữ ≥ 4.5:1 (chữ lớn ≥ 3:1), viền/icon có nghĩa ≥ 3:1.
   - Vùng chạm ≥ 44×44px, cách nhau ≥ 8px.
   - Không truyền tin chỉ bằng màu (đúng/sai: màu + icon + chữ).
   - Focus nhìn thấy rõ; thứ tự Tab theo thứ tự đọc; mọi thao tác làm được bằng bàn phím.
   - Animation tôn trọng `prefers-reduced-motion`; không nhấp nháy > 3 lần/giây.
   - Chữ nội dung ≥ 16px, line-height 1.5; đoạn khác ngôn ngữ giao diện có thuộc tính `lang` đúng (để TTS/screen reader đọc đúng).
4. **6 trạng thái bắt buộc** cho mỗi khối dữ liệu: loading (skeleton, không spinner toàn màn hình nếu > 300ms mới hiện), rỗng (giải thích + hành động gợi ý), lỗi (nói gì sai + cách sửa + nút thử lại), thành công, hết hạn mức nếu có (nói còn bao nhiêu/khi nào reset), offline.
5. **Phản hồi nhanh:** phản hồi thao tác < 100ms (optimistic UI cho thao tác lặp lại thường xuyên); việc > 1s có tiến trình; việc AI/stream hiện từng phần.
6. **Responsive:** thiết kế 375px trước; kiểm 768px, 1280px. Hành động chính trong vùng ngón cái (nửa dưới màn hình) trên mobile. Không cuộn ngang.

## B. Mẫu UX riêng của lĩnh vực sản phẩm
Mẫu UX đặc thù của sản phẩm (nội dung, microcopy, luồng học/dùng): skill dự án mà `.claude/project-profile.md` liệt kê cho vai ui-designer/frontend-dev.

## C. Quy trình cho ui-designer
1. Đọc user story + AC → liệt kê việc người dùng cần làm (job) và dữ liệu cần thấy.
2. User flow (Mermaid) có cả nhánh lỗi/rỗng/hết hạn mức.
3. Wireframe/prototype mobile 375px trước, chỉ dùng token và component có trong `design-system.md`; cần component/token mới → ghi rõ trong đặc tả để PO duyệt.
4. Đặc tả màn hình: mỗi phần tử có nhãn đúng ngôn ngữ giao diện (microcopy), map dữ liệu → API, 6 trạng thái ở mục A.4, ghi chú accessibility (thứ tự focus, nhãn aria cho icon button).
5. Tự kiểm bằng checklist D trước khi giao.

## D. Checklist (designer tự kiểm trước khi giao; frontend-dev tự kiểm trước `in_review`; code-reviewer/qa dùng khi rà)
- [ ] Đủ 6 trạng thái (A.4), có microcopy cho từng trạng thái.
- [ ] Chỉ dùng token/component trong `design-system.md`; không hard-code màu, cỡ chữ, spacing (frontend: không dùng giá trị Tailwind tuỳ ý kiểu `text-[13px]`, `#hex`).
- [ ] Tương phản (`scripts/check_contrast.py` đạt), vùng chạm 44px, focus rõ, dùng được bằng bàn phím.
- [ ] Icon button có `aria-label`; input có `<label>`; lỗi form gắn `aria-describedby`; dùng thẻ ngữ nghĩa (`button`, `nav`, `main`, heading theo cấp).
- [ ] Không cuộn ngang ở 375px; hành động chính dễ chạm bằng ngón cái.
- [ ] `prefers-reduced-motion` được tôn trọng.
- [ ] (frontend) Khớp đặc tả: chụp màn hình Playwright ở 375px và 1280px cho các trạng thái chính, so với prototype; lệch có chủ đích thì ghi lý do ở mục "Tiến trình" của task.
- [ ] (frontend) Chạy kiểm a11y tự động nếu có (`@axe-core/playwright`) cho luồng chính, 0 lỗi mức serious/critical.

## E. Tài nguyên trong skill
- `references/wcag-checklist.md`: 18 tiêu chí WCAG 2.2 AA kèm ví dụ đúng/sai. Đọc khi làm form, media, tương tác phức tạp, hoặc khi review a11y.
- `scripts/check_contrast.py`: kiểm tương phản token màu. Chạy ở gốc dự án: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/ui-ux-guidelines/scripts/check_contrast.py"` (mặc định đọc `docs/03-design/design-system.md`; exit 1 nếu có cặp trượt).
  - Quy ước để script đọc được: token màu viết dạng CSS biến kiểu shadcn trong khối ```css, `:root { --primary: …; --primary-foreground: …; }` và `.dark { … }`; giá trị hex / rgb() / hsl() / "H S% L%" / oklch().
  - Tự kiểm các cặp `X` / `X-foreground`, `foreground` / `background`, `muted-foreground` / `background`. Cặp khác thêm dòng `contrast-pair: <fg> <bg> [text|large|ui]`.
  - ui-designer chạy mỗi khi sửa màu trong design system; dán kết quả vào báo cáo.

