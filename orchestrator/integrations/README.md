# `orchestrator/integrations/` — trạng thái thực tế của từng module

**Đọc trước khi dùng hoặc mở rộng bất kỳ file nào trong thư mục này.**

Mỗi class trong thư mục này được đặt tên theo một tool/repo GitHub có thật
(vd: `microsoft/playwright`, `abhigyanpatwari/GitNexus`,
`multica-ai/andrej-karpathy-skills`...), nhưng **không có class nào thực sự
gọi tool/repo đó**. Chúng chỉ được nối vào demo script của chính mình và
test tự-tham-chiếu — **không được gọi từ luồng CEO/CTO/workforce thật** của
hệ thống. Runtime sẽ phát `UserWarning` khi các class này được khởi tạo, để
không ai vô tình dựa vào output của chúng cho quyết định thật mà không biết.

## Bảng trạng thái

| Module | Class | Trạng thái thật |
|---|---|---|
| `git_nexus.py` | `GitNexusEngine` | 🔴 Giả hoàn toàn — không chạy git, trả hash/health-score cố định |
| `codegraph_tool.py` | `CodeGraphTool` | 🔴 Giả hoàn toàn — chỉ index 2 symbol viết cứng |
| `karpathy_skills.py` | `KarpathySkillsEngine` | 🔴 Giả hoàn toàn — 5 mục text viết cứng, không "execute" gì |
| `mattpocock_skills.py` | `MattPocockSkillsEngine` | 🔴 Giả hoàn toàn — 2 mục text viết cứng |
| `anysearch_skill.py` | `AnySearchSkill` | 🔴 Giả hoàn toàn — không tìm kiếm gì, đếm từ khoá nhân 2 |
| `agent_reach.py` | `AgentReachEngine` | 🔴 Giả hoàn toàn — tự bịa URL trích dẫn từ query |
| `taste_skill.py` | `TasteSkill` | 🔴 Giả hoàn toàn — luôn trả cùng 1 bộ design token |
| `ui_ux_pro_max.py` | `UIUXProMaxSkill` | 🔴 Giả hoàn toàn — luôn trả cùng 1 bộ token |
| `impeccable_design.py` | `ImpeccableDesignSkill` | 🔴 Giả hoàn toàn — luôn trả "AA Passed" |
| `chatdev_adapter.py` | `ChatDevAdapter` | 🔴 Giả hoàn toàn — không có agent nào thật sự chạy |
| `public_apis_catalog.py` | `PublicAPIsCatalog` | 🔴 Giả hoàn toàn — chỉ có 2 entry viết cứng |
| `playwright_moderator.py` | `PlaywrightVisualAuditor` | 🟠 Có ít logic thật (substring check trên HTML text), nhưng không chạy browser thật |
| `sag_framework.py` | `SAGAgentFramework` | 🟠 Lưu node thật (in-memory), nhưng `synchronize_graph()` là no-op |
| `ponytail_runner.py` | `PonytailRunner` | 🟠 **Topological sort là logic thật**, nhưng `execute_workflow()` không gọi agent thật, retry không hoạt động |
| `openclaw_processor.py` / `providers/openclaw_provider.py` | `OpenClawPromptProcessor` | 🟠 **`scan_project_context()` đọc file thật** (package.json, tailwind config...), nhưng phần "refine" chỉ là chọn template theo từ khoá |
| `providers/prompt_optimizer.py` | `PromptOptimizerEngine` | 🔴 Giả hoàn toàn — chọn 1 trong 4 template cố định theo từ khoá, `clarity_score` là công thức bịa (`0.85 + độ_dài_prompt*0.002`) |
| `rtk_compressor.py` | `RTKTokenCompressor` | 🟢 **Logic thật** (dedup dòng trùng, gộp khoảng trắng) — chỉ không phải thư viện `rtk-ai/rtk` thật, và ước lượng token theo quy tắc thô (~4 ký tự/token) |
| `ecosystem_hub.py` | `ExternalEcosystemHub` | Hub gộp toàn bộ các module ở trên — trạng thái thật = trạng thái của từng module con |

# `orchestrator/integrations/` — trạng thái thực tế của từng module

**Đọc trước khi dùng hoặc mở rộng bất kỳ file nào trong thư mục này.**

Cập nhật (lượt "implement thật bằng repo GitHub"): **7 module đã được viết lại
bằng logic thật** — gọi `git` thật, parse AST thật, tải dữ liệu thật từ
GitHub, chạy browser Chromium thật, tính contrast WCAG thật. Phần còn lại
vẫn là mock có nhãn rõ (đa số cần API key hoặc mang tính chủ quan, không thể
"làm thật" một cách khách quan).

## Bảng trạng thái

| Module | Class | Trạng thái thật |
|---|---|---|
| `git_nexus.py` | `GitNexusEngine` | 🟢 **THẬT** — `sync_multi_remotes()`/`audit_repository_health()` chạy `git status/fsck/ls-files/rev-list` + `git ls-remote` qua mạng thật. `list_pr_issue_nexus()` vẫn giả (cần GitHub token). |
| `codegraph_tool.py` | `CodeGraphTool` | 🟢 **THẬT** — `index_directory()` parse AST thật toàn bộ codebase, dựng graph caller/callee thật. |
| `public_apis_catalog.py` | `PublicAPIsCatalog` | 🟢 **THẬT** — `load()` tải README thật từ `public-apis/public-apis` trên GitHub (~1700 API thật), `search_apis()` tìm trên dữ liệu thật. |
| `playwright_moderator.py` | `PlaywrightVisualAuditor` | 🟢 **THẬT** — Chromium headless thật qua package `playwright`, đo overflow/overlap/contrast thật từ DOM. `pixel_diff()` so ảnh thật bằng Pillow. |
| `_wcag.py` (mới) | — | 🟢 **THẬT** — công thức WCAG 2.1 chuẩn, verify khớp case mẫu W3C. |
| `impeccable_design.py` | `ImpeccableDesignSkill` | 🟢 **THẬT** (phạm vi hẹp) — tính contrast ratio thật từ màu input; trung thực báo "NEEDS_INPUT" nếu thiếu màu thay vì đoán. |
| `ui_ux_pro_max.py` | `UIUXProMaxSkill` | 🟡 4 theme preset **thật sự khác nhau** (không còn 1 kết quả cố định) + verify contrast thật; bảng màu mỗi theme vẫn là do người thiết kế chọn tay, không fetch từ đâu. |
| `taste_skill.py` | `TasteSkill` | 🟡 Đã bỏ điểm số bịa (`visual_taste_score: 0.98`); guideline là ý kiến thiết kế có ghi rõ nhãn, phần contrast (nếu có màu input) là số đo thật. |
| `karpathy_skills.py` | `KarpathySkillsEngine` | 🔴 Giả hoàn toàn — 5 mục text viết cứng, không "execute" gì |
| `mattpocock_skills.py` | `MattPocockSkillsEngine` | 🔴 Giả hoàn toàn — 2 mục text viết cứng |
| `anysearch_skill.py` | `AnySearchSkill` | 🔴 Giả hoàn toàn — không tìm kiếm gì, đếm từ khoá nhân 2 |
| `agent_reach.py` | `AgentReachEngine` | 🔴 Giả hoàn toàn — tự bịa URL trích dẫn từ query (cần API tìm kiếm thật + key để làm thật) |
| `chatdev_adapter.py` | `ChatDevAdapter` | 🔴 Giả hoàn toàn — không có agent nào thật sự chạy |
| `sag_framework.py` | `SAGAgentFramework` | 🟠 Lưu node thật (in-memory), nhưng `synchronize_graph()` là no-op |
| `ponytail_runner.py` | `PonytailRunner` | 🟠 **Topological sort là logic thật**, nhưng `execute_workflow()` không gọi agent thật, retry không hoạt động |
| `openclaw_processor.py` / `providers/openclaw_provider.py` | `OpenClawPromptProcessor` | 🟠 **`scan_project_context()` đọc file thật**, nhưng phần "refine" chỉ là chọn template theo từ khoá (cần LLM thật để hoàn thiện — ví dụ gọi `OllamaProvider` đã có sẵn trong dự án) |
| `providers/prompt_optimizer.py` | `PromptOptimizerEngine` | 🔴 Giả hoàn toàn — chọn 1 trong 4 template cố định theo từ khoá |
| `rtk_compressor.py` | `RTKTokenCompressor` | 🟢 **Logic thật** (dedup dòng trùng, gộp khoảng trắng) — chỉ không phải thư viện `rtk-ai/rtk` thật |
| `ecosystem_hub.py` | `ExternalEcosystemHub` | Hub gộp toàn bộ các module ở trên — trạng thái thật = trạng thái của từng module con. Đã xử lý an toàn trường hợp `playwright` chưa cài (không crash cả hub). |

## Vì sao 10 module còn lại chưa "làm thật" được?

- **Cần API key mình không có quyền tạo thay bạn**: `agent_reach.py` (search
  engine thật), `git_nexus.py::list_pr_issue_nexus()` (GitHub token).
- **Mang tính chủ quan/sáng tạo, không có "đáp án đúng" khách quan**:
  `karpathy_skills.py`, `mattpocock_skills.py` (nội dung "skill" do con
  người biên soạn), `taste_skill.py`/`ui_ux_pro_max.py` (thẩm mỹ) — phần đo
  được (contrast) đã làm thật, phần còn lại ghi rõ là ý kiến curated.
- **Cần chạy 1 multi-agent framework nặng (`OpenBMB/ChatDev`) hoặc 1 LLM
  thật**: `chatdev_adapter.py`, `openclaw_processor.py`'s refinement step —
  khả thi nếu nối vào `OllamaProvider` đã có sẵn trong dự án (`providers/ollama_provider.py`),
  nhưng cần 1 Ollama server đang chạy để test, ngoài phạm vi sandbox này.

## Bạn nên làm gì tiếp theo?

Ưu tiên theo chi phí hoàn thiện thấp → cao:
1. `sag_framework.py::synchronize_graph()` — chỉ cần ghi/đọc node ra file JSON thật thay vì no-op.
2. `ponytail_runner.py::execute_workflow()` — nhận 1 dict `{step_type: callable}` và gọi callable thật thay vì đánh dấu "COMPLETED" giả.
3. `openclaw_processor.py`/`chatdev_adapter.py` — nối vào `OllamaProvider` đã có sẵn (cần bạn có Ollama server chạy local).
4. `git_nexus.py::list_pr_issue_nexus()` — thêm `GITHUB_TOKEN` và gọi thật `GET /repos/{owner}/{repo}/pulls`.
5. `agent_reach.py`/`anysearch_skill.py` — cần đăng ký 1 search API thật (Brave Search API, Serper...).

