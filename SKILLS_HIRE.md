# SKILLS_HIRE.md — Skill 人事任務清單

> **這份文件是什麼**：`SKILLS_RESEARCH.md` 的可執行版。研究文件講「為什麼」，這份講
> 「做什麼、怎麼做」。用人事比喻組織任務：**招募 (HIRE)**、**留任整頓 (FIX)**、
> **資遣 (FIRE)**、**待決簽核 (PENDING)**。
>
> **基準日**：2026-05-14　**分支**：`refactor/simply`
>
> **狀態**：任務清單草稿 —— 尚未執行任何一項。請 review 後再動工。

---

## 0. 先講一個關鍵限制（影響「安裝/卸除」的定義）

「安裝 skill / 卸除 skill」在本機其實**不是逐一操作**的：

- skills 是**整包外掛 (plugin)** 安裝的，不能單獨裝一個、退一個。
- 本專案目前掛了 4 個 plugin：

| Plugin | 範圍 scope | 內含 | 對本專案 |
|---|---|---|---|
| `python-engineering@jamie-bitflight-skills` | project（本專案） | ~42 skills + 6 agents | **留** —— 要用其中 ~8 個 |
| `uv@jamie-bitflight-skills` | project（本專案） | 1 skill (`uv`) | **資遣** —— 與 `python-engineering:uv` 完全重複 |
| `caveman@caveman` | user（全域） | 5 skills | 留 —— 使用者個人偏好工具，非本專案決定 |
| `nuxt-skills@nuxt-skills` | local（**屬於 `jen-lab` 專案**） | ~20 skills | 與本專案無關，本 repo 不需處理 |

所以實際可執行的「人事動作」是：

1. **招募 = 建立新的本地 skill**（補 `SKILLS_RESEARCH.md` §7 的缺口）。
2. **資遣 = 卸除整個 redundant plugin**（只有 `uv` 符合）+ 清掉 README 幽靈名單。
3. **python-engineering 內的 ~30 個不用的 skill：無法逐一卸除** → 改用「不啟用政策」列管。
4. **留任整頓 = 修現有本地 skill 的假訊號**。

---

## 1. 任務總表

| ID | 類別 | 動作 | 對象 | 優先 | 依賴 | 風險 |
|---|---|---|---|:--:|---|:--:|
| **P1** | 待決 | 拍板型別檢查器 | pyright vs ty | 🔴 P0 | — | 阻擋 F3/F4/F5 |
| **P2** | 待決 | 決定 htmx 去留 | `htmx-patterns` 要不要建 | 🟠 P1 | — | 阻擋 F4/F6 |
| **P3** | 待決 | 決定 `django-extensions` 套件 | 裝套件 or 標記休眠 | 🟡 P2 | — | 低 |
| **P4** | 待決 | 定品質檢查鏈入口 | `fix`/`code-quality`/`code-reviewer` | 🟡 P2 | P1 | 低 |
| **H1** | 招募 | **建立 `celery-patterns` skill** | 新本地 skill | 🔴 P0 | skill-creator | 低（純新增） |
| **H2** | 招募 | 建立 `storage-s3` skill | 新本地 skill | 🟠 P1 | skill-creator | 低（純新增） |
| **H3** | 招募 | 建立 `opentelemetry-patterns` skill | 新本地 skill | 🟡 P2 | skill-creator | 低（純新增） |
| **F1** | 資遣 | **卸除 `uv` plugin** | `uv@jamie-bitflight-skills` | 🟠 P1 | — | 極低（功能重複） |
| **F2** | 資遣 | 清掉 README 幽靈 skill 名單 | `.claude/skills/README.md` | 🟠 P1 | H1, P2 | 低 |
| **F3** | 整頓 | 修 `code-quality` 假訊號 | 本地 skill | 🟠 P1 | P1, P2 | 低 |
| **F4** | 整頓 | 修 `systematic-debugging` 假訊號 | 本地 skill | 🟠 P1 | P1, P2 | 低 |
| **F5** | 整頓 | 修本地 `code-reviewer` agent 假訊號 | 本地 agent | 🟠 P1 | P1, P2 | 低 |
| **F6** | 整頓 | 標註 Django skills 的 htmx 段落 | `django-forms`/`django-templates`/`pytest-django-patterns` | 🟡 P2 | P2 | 低 |
| **C1** | 政策 | 寫「python-engineering 啟用/不啟用」政策 | `CLAUDE.md` 或新 `.claude/SKILLS_POLICY.md` | 🟡 P2 | — | 低 |

> 註：`SKILLS_RESEARCH.md` §6.6 提到的 `CLAUDE.md` 漂移，**使用者已自行修好**
> （分支名、task 檔路徑、phase、no-django-storages 都已更新）。本清單不再列該項。

---

## 2. 招募 HIRE —— 建立缺口 skill

### H1 — 建立 `celery-patterns` skill 🔴 P0

- **為什麼**：本專案是 Celery worker，但 `.claude/skills/celery-patterns/` **不存在**。
  `django-models`、`systematic-debugging`、本地 `code-reviewer` 三處的 Integration / 引用段
  都指向它 —— 一個被三個 skill 依賴、卻是空的核心 skill。
- **怎麼做**：用 `skill-creator`，在 `.claude/skills/celery-patterns/SKILL.md` 建立。內容至少涵蓋：
  - `@shared_task` 慣例、命名
  - retry + exponential backoff 策略
  - **idempotency**（`CLAUDE.md` §5.8 鐵則：所有 task 可安全重試）
  - 傳 ID 不傳 model instance
  - `Image` / `ImageTask` 狀態流轉（retry → 新 `ImageTask` 記錄）
  - `CELERY_TASK_ALWAYS_EAGER` 測試模式
  - 真實檔案參照：`images/tasks.py`、`django_thumbnail/celery.py`
- **驗收**：`.claude/skills/README.md` 的 celery-patterns 連結不再是死連結；
  寫 Celery 相關程式時 skill 會被觸發。
- **依賴**：`skill-creator`（已在）。**無阻擋**，可立即開工。

### H2 — 建立 `storage-s3` skill 🟠 P1

- **為什麼**：專案有 `InternalS3` / `PublicS3` singleton、MinIO、`boto3` 直接呼叫；
  `tasks/refinement/03_storage_module.md` 整個任務在重構 storage。沒有 skill 涵蓋這塊。
- **怎麼做**：用 `skill-creator` 建 `.claude/skills/storage-s3/SKILL.md`。涵蓋：
  - `boto3` S3 client 建構（避免 import-time 建立 —— refinement #03 的痛點）
  - InternalS3 vs PublicS3 的分界與用途
  - bucket 管理（對應 `management/commands/create_bucket` 等）
  - MinIO endpoint / 憑證從 settings 讀取的模式
  - 真實檔案參照：`images/utils.py`
- **驗收**：refinement #03 重構時有 skill 可依。
- **依賴**：`skill-creator`。建議與 refinement #03 同時做（context 共用，最省事）。

### H3 — 建立 `opentelemetry-patterns` skill 🟡 P2

- **為什麼**：專案有 `telemetry.py`、3 個 OTel instrumentor；記憶中已有明確偏好
  （`span.set_attributes(dict)` 批次設定、不要重複呼叫 `set_attribute()`；web 與 Celery worker
  的 telemetry 要分開設定）。這些散落的偏好值得固化成 skill。
- **怎麼做**：用 `skill-creator` 建 `.claude/skills/opentelemetry-patterns/SKILL.md`。涵蓋：
  - span 屬性批次設定（`set_attributes(dict)` 而非多次 `set_attribute()`）
  - web vs Celery worker 的 telemetry 分流（對應 commit `af308f6`）
  - instrumentor 接線位置
  - 真實檔案參照：`django_thumbnail/telemetry.py`
- **驗收**：動 telemetry 程式時 skill 觸發，記憶中的偏好不再只活在 memory。
- **依賴**：`skill-creator`。最低優先 —— OTel 程式碼相對穩定。

---

## 3. 資遣 FIRE —— 卸除與清理

### F1 — 卸除 `uv` plugin 🟠 P1

- **為什麼**：`uv@jamie-bitflight-skills` 是獨立 plugin，但只裝了一個 `uv` skill ——
  而 `python-engineering` plugin **已經內含 `python-engineering:uv`**，功能完全重複。
  留著只是多佔 context、多一份要維護的東西。
- **怎麼做**：用 Claude Code 的 `/plugin` 管理介面移除 `uv@jamie-bitflight-skills`
  （scope 是 project，只影響本專案，可隨時重裝）。
- **驗收**：skill 清單不再出現獨立 `uv`；`python-engineering:uv` 仍在，需要時照用。
- **風險**：極低。功能重複、可逆。
- **註**：`nuxt-skills` plugin 是 `jen-lab` 專案的 local 安裝，**本專案不受影響、無需處理**。
  若要全域清掉，去 `jen-lab` 那邊決定。

### F2 — 清掉 `.claude/skills/README.md` 的幽靈名單 🟠 P1

- **為什麼**：README 列了 16 個 skill，磁碟上只有 9 個。7 個幽靈：
  `onboard`、`ticket`、`pr-review`、`pr-summary`、`worktree-commit-merge`、
  `htmx-patterns`、`celery-patterns`。入口文件說謊 = skill 體系可信度崩。
- **怎麼做**：
  - `celery-patterns` → **不刪，由 H1 補實**。
  - `htmx-patterns` → 看 **P2** 決定（多半是刪，專案沒 htmx）。
  - `onboard` / `ticket` / `pr-review` / `pr-summary` / `worktree-commit-merge`
    → **刪掉這幾列**。它們的功能已被現有工具覆蓋：
    - `pr-review` / `pr-summary` → 本地 `code-reviewer` agent + `review`
    - `worktree-commit-merge` → `github-workflow` agent
    - `onboard` / `ticket` → 無對應，若真要這流程再重建
  - 同步修正 README 開頭「project-specific skills」的數量敘述。
- **驗收**：README 列的每個 skill 都在磁碟上有對應目錄。
- **依賴**：H1（celery 那列）、P2（htmx 那列）。可與 `docs-sync` / refinement #01 一起做。

---

## 4. 留任整頓 FIX —— 修現有本地 skill 的假訊號

> 共同背景：本地 skills 寫於專案早期，內含三類**過期假訊號** ——
> ① `pyright` 指令（型別檢查器未定案，見 P1）　② HTMX 教學（**專案沒裝 htmx**）
> ③ `django-extensions` / Debug Toolbar（**套件沒裝**）。
> 假訊號會讓 review 失焦、讓新人照錯的做。

### F3 — 修 `code-quality` skill 🟠 P1

- **改什麼**：① 型別檢查指令依 P1 結果改成 pyright 或 ty（目前寫死 `uv run pyright`）；
  ② 人工 checklist 移除「HTMX partials handle HX-Request header」這項。
- **依賴**：P1、P2。

### F4 — 修 `systematic-debugging` skill 🟠 P1

- **改什麼**：① checklist 的 `uv run pyright` 依 P1 對齊；② 移除「Django Debug Toolbar」
  整段（套件沒裝）；③ 移除「Debugging HTMX」整段。
- **依賴**：P1、P2。

### F5 — 修本地 `code-reviewer` agent 🟠 P1

- **改什麼**：① Review Process 的 `uv run pyright` 依 P1 對齊；② 移除 / 標註
  「HTMX handling — Check `request.htmx`」相關項；③ Integration 段的 `celery-patterns`
  連結在 H1 完成後即生效，不需改。
- **依賴**：P1、P2、（H1 讓連結生效）。

### F6 — 標註 Django skills 的 htmx 段落 🟡 P2

- **改什麼**：`django-forms`、`django-templates`、`pytest-django-patterns` 各有 HTMX 段落。
  本專案前端是純 JS fetch + `JsonResponse`，**沒有 htmx**。不必整段刪（未來可能引入），
  但要加一行註記：「本專案目前未使用 htmx —— 以下段落暫不適用」。
- **依賴**：P2。若 P2 決定未來要引入 htmx，這項改為「保留不動」。

---

## 5. 政策 POLICY

### C1 — 寫下「python-engineering 啟用/不啟用」政策 🟡 P2

- **為什麼**：python-engineering 的 ~30 個不用的 skill **無法逐一卸除**（plugin 綁定）。
  既然刪不掉，就要明文管理，否則每次都得重新判斷、或不小心誤用。
- **怎麼做**：在 `CLAUDE.md` 加一節，或新建 `.claude/SKILLS_POLICY.md`，明列：
  - **可用（情境）**：`python3-web`、`comprehensive-test-review`、`python-pytest-architect`、
    `modernpython`、`python3-core`、`python3-typing`、`python3-testing`、`python-engineering:uv`
    —— 並註明「當原則參考讀，不照抄指令（src/ 佈局、prek、ty 假設與本專案不符）」。
  - **不啟用**：CLI/TUI 全家、打包/發布全家、`orchestrate`/SAM 系列、`stinkysnake`/`snakepolish`、
    `ty`、`debug`/`lint`/`cleanup`/`review`（與本地工具重複）、`python-engineering:code-reviewer`
    （依賴未裝的 `dh:` / `holistic-linting` 外掛）。
  - **品質檢查鏈**（依 P4）：內迴圈 `fix` → PR 前 `code-quality` + 本地 `code-reviewer`。
- **依賴**：建議 P1/P4 拍板後一起寫。

---

## 6. 待決 PENDING —— 需要人簽核才能動

這些不是「執行任務」，是「決策任務」。卡住的話下游動不了。

| ID | 要決定什麼 | 選項 | 卡住誰 |
|---|---|---|---|
| **P1** | 型別檢查器 | (A) 留 pyright：加進 dev 依賴 + 接 CI　/　(B) 轉 ty：停用 `pyrightconfig.json` | F3, F4, F5, C1 |
| **P2** | htmx 去留 | (A) 永不引入：刪 `htmx-patterns` README 列、F6 改為刪段　/　(B) 未來會用：保留、F6 只加註記 | F2, F4, F6 |
| **P3** | `django-extensions` 套件 | (A) 裝套件（skill 本身寫得好、Django 內省實用）　/　(B) 不裝：把 `django-extensions` skill 標記休眠 | —（獨立） |
| **P4** | 品質檢查入口 | 建議：內迴圈 `fix`、PR 前 `code-quality` + 本地 `code-reviewer`；`lint`/`review` 不啟用 | C1 |

> **建議**：P1 是最高優先 —— 它卡住三個整頓任務。其餘三個可平行決定。

---

## 7. 建議執行順序

```
第 1 波（解鎖 + 零風險，立刻可做）
  ├─ P1  拍板 pyright vs ty          ← 解鎖 F3/F4/F5/C1
  ├─ P2  拍板 htmx 去留              ← 解鎖 F2/F4/F6
  ├─ F1  卸除 uv plugin              ← 無依賴，極低風險
  └─ H1  建立 celery-patterns        ← 無依賴，最高價值

第 2 波（補洞 + 整頓）
  ├─ H2  建立 storage-s3            （搭 refinement #03 一起做）
  ├─ F2  清 README 幽靈名單
  ├─ F3  修 code-quality
  ├─ F4  修 systematic-debugging
  └─ F5  修本地 code-reviewer agent

第 3 波（深度 + 政策）
  ├─ H3  建立 opentelemetry-patterns
  ├─ F6  標註 Django skills 的 htmx 段落
  ├─ C1  寫 python-engineering 啟用政策
  └─ P3  決定 django-extensions 套件
```

---

## 8. 一頁速覽

**招募 3 個**（建本地 skill）：`celery-patterns`🔴、`storage-s3`🟠、`opentelemetry-patterns`🟡

**資遣 2 項**：卸 `uv` plugin、清 README 7 個幽靈名單

**整頓 4 個**（修假訊號）：`code-quality`、`systematic-debugging`、本地 `code-reviewer`、3 個 Django skills 的 htmx 段

**待決 4 案**：型別檢查器 (P0)、htmx 去留、django-extensions 套件、品質檢查鏈

**不動**：9 個本地 skill 主體、2 個本地 agent、`python-engineering` plugin（留著用 8 個）、
`caveman`（使用者偏好）、`nuxt-skills`（屬 jen-lab，非本專案）

---

*本清單僅供 review；尚未執行任何安裝、卸除或檔案變更。*
*配套文件：`SKILLS_RESEARCH.md`（研究與評分依據）。*
