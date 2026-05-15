# SKILLS_HIRE.md — Skill 人事任務清單

> **這份文件是什麼**：`SKILLS_RESEARCH.md` 的可執行版。研究文件講「為什麼」，這份講
> 「做什麼、怎麼做」。用人事比喻組織任務：**招募 (HIRE)**、**留任整頓 (FIX)**、
> **資遣 (FIRE)**、**待決簽核 (PENDING)**。
>
> **基準日**：2026-05-14　**最後更新**：2026-05-16　**分支**：`claude/skills`
>
> **狀態**：**全部完成** —— 第 1 波 (F1/F2/P1/P2/H1/F3/F4/F5/F6) + 第 2 波 (H2)
> + 第 3 波 (H3/P3/C1/P4) 全部結案。
>
> **第 2/3 波結果**（2026-05-16）：
> - **H2** 建 `.claude/skills/storage-s3/SKILL.md`（118 行）—— boto3 singleton、
>   InternalS3/PublicS3 雙端點、bucket commands、MinIO endpoint env
> - **H3** 建 `.claude/skills/opentelemetry-patterns/SKILL.md`（146 行）——
>   `set_attributes(dict)` 批次、web vs Celery worker 分流、SimpleSpanProcessor fork-safety
> - **P3** 拍板「不裝 django-extensions」—— 證據：套件未在 `pyproject.toml`、無使用記錄；
>   於 `.claude/skills/django-extensions/SKILL.md` 開頭加 DORMANT 註記與啟用步驟
> - **C1 + P4** 新建 `.claude/SKILLS_POLICY.md`（英文版）—— 12 可用 / 24 不啟用、
>   本地工具對應表、品質檢查鏈三階段（/fix → /code-quality + code-reviewer → CI）
>
> **重大更正**：原 §0 / P1 假設專案用 pyright 或 ty —— 錯。
> 實際 `pyproject.toml` dev group 裝的是 **`pyrefly`**（Meta 出的），
> `Makefile` `make check` 跑 `python -m pyrefly check`，CI 也走這條。
> `pyrightconfig.json` 不存在。

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
| **P1** | 待決 | 拍板型別檢查器 ✅ DONE（對齊 pyrefly） | 6 處假訊號改 `pyrefly check` | 🔴 P0 | — | — |
| **P2** | 待決 | 決定 htmx 去留 ✅ DONE（永不引入，2026-05-16） | 已不建 `htmx-patterns`、F4/F5 刪 htmx 段、F6 加未用註記 | 🟠 P1 | — | — |
| **P3** | 待決 | 決定 `django-extensions` 套件 ✅ DONE（不裝、休眠註記，2026-05-16） | `.claude/skills/django-extensions/SKILL.md` 加 DORMANT block | 🟡 P2 | — | — |
| **P4** | 待決 | 定品質檢查鏈入口 ✅ DONE（2026-05-16） | 入口已寫入 `SKILLS_POLICY.md` §5 | 🟡 P2 | P1 | — |
| **H1** | 招募 | **建立 `celery-patterns` skill** ✅ DONE (2026-05-16) | `.claude/skills/celery-patterns/SKILL.md` | 🔴 P0 | skill-creator | 低（純新增） |
| **H2** | 招募 | 建立 `storage-s3` skill ✅ DONE (2026-05-16) | `.claude/skills/storage-s3/SKILL.md`（118 行） | 🟠 P1 | skill-creator | — |
| **H3** | 招募 | 建立 `opentelemetry-patterns` skill ✅ DONE (2026-05-16) | `.claude/skills/opentelemetry-patterns/SKILL.md`（146 行） | 🟡 P2 | skill-creator | — |
| **F1** | 資遣 | **卸除 `uv` plugin** ✅ DONE | `uv@jamie-bitflight-skills` | 🟠 P1 | — | 極低（功能重複） |
| **F2** | 資遣 | 清掉 README 幽靈 skill 名單 ✅ DONE（celery 列待 H1） | `.claude/skills/README.md` | 🟠 P1 | H1, P2 | 低 |
| **F3** | 整頓 | 修 `code-quality` 假訊號 ✅ DONE (2026-05-16) | 本地 skill | 🟠 P1 | — | — |
| **F4** | 整頓 | 修 `systematic-debugging` 假訊號 ✅ DONE (2026-05-16) | 本地 skill | 🟠 P1 | — | — |
| **F5** | 整頓 | 修本地 `code-reviewer` agent 假訊號 ✅ DONE (2026-05-16) | 本地 agent | 🟠 P1 | — | — |
| **F6** | 整頓 | 標註 Django skills 的 htmx 段落 ✅ DONE (2026-05-16) | `django-forms`/`django-templates`/`pytest-django-patterns` | 🟡 P2 | — | — |
| **C1** | 政策 | 寫「python-engineering 啟用/不啟用」政策 ✅ DONE (2026-05-16) | `.claude/SKILLS_POLICY.md`（英文、136 行） | 🟡 P2 | — | — |

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

### F1 — 卸除 `uv` plugin 🟠 P1 ✅ **DONE** (2026-05-16)

- **為什麼**：`uv@jamie-bitflight-skills` 是獨立 plugin，但只裝了一個 `uv` skill ——
  而 `python-engineering` plugin **已經內含 `python-engineering:uv`**，功能完全重複。
  留著只是多佔 context、多一份要維護的東西。
- **怎麼做**：用 Claude Code 的 `/plugin` 管理介面移除 `uv@jamie-bitflight-skills`
  （scope 是 project，只影響本專案，可隨時重裝）。
- **實作**：直接編輯 `.claude/settings.json`，從 `enabledPlugins` 移除
  `"uv@jamie-bitflight-skills": true` 一行（重啟 Claude Code 生效）。
- **驗收**：skill 清單不再出現獨立 `uv`；`python-engineering:uv` 仍在，需要時照用。
- **風險**：極低。功能重複、可逆。
- **註**：`nuxt-skills` plugin 是 `jen-lab` 專案的 local 安裝，**本專案不受影響、無需處理**。
  若要全域清掉，去 `jen-lab` 那邊決定。

### F2 — 清掉 `.claude/skills/README.md` 的幽靈名單 🟠 P1 ✅ **DONE** (2026-05-16，部分)

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
- **實作**（2026-05-16）：
  - 已刪 6 列：`onboard` / `ticket` / `pr-review` / `pr-summary` /
    `worktree-commit-merge` / `htmx-patterns`（提前判決：專案無 htmx）。
  - 「Frontend & UI」整段移除、「Building a New Feature」combo 移除 htmx 步驟。
  - `celery-patterns` 列保留（仍為死連結，H1 完成後自然生效）。
- **剩餘**：H1 完成後驗證 `celery-patterns` 連結生效。
- **驗收**：README 列的每個 skill 都在磁碟上有對應目錄。
- **依賴**：H1（celery 那列）、P2（htmx 那列 → 已提前處理）。

---

## 4. 留任整頓 FIX —— 修現有本地 skill 的假訊號

> 共同背景：本地 skills 寫於專案早期，內含三類**過期假訊號** ——
> ① `pyright` / `ty check` 指令（**真相**：實際工具是 `pyrefly` —— P1 已對齊）
> ② HTMX 教學（**專案沒裝 htmx**）
> ③ `django-extensions` / Debug Toolbar（**套件沒裝**）。
> 假訊號會讓 review 失焦、讓新人照錯的做。

### F3 — 修 `code-quality` skill 🟠 P1 ✅ DONE (2026-05-16)

- ① 型別檢查指令 ✅（已改 `uv run pyrefly check`，含 description）
- ② 移除「HTMX partials handle HX-Request header」checklist 行 ✅

### F4 — 修 `systematic-debugging` skill 🟠 P1 ✅ DONE (2026-05-16)

- ① checklist `uv run pyright` ✅（已改 pyrefly）
- ② 移除「Django Debug Toolbar」整段 ✅
- ③ 移除「Debugging HTMX」整段 ✅
- ④ Integration 段移除 `htmx-alpine-patterns` 行 ✅

### F5 — 修本地 `code-reviewer` agent 🟠 P1 ✅ DONE (2026-05-16)

- ① Review Process `uv run pyright` ✅（已改 pyrefly）
- ② 「Django Views」checklist 移除 HTMX handling 行 ✅
- ③ CORRECT view 範例移除 `if request.htmx` 分支 ✅
- ④ Integration 段移除 `htmx-alpine-patterns` 行 ✅
- ⑤ Integration 段的 `celery-patterns` 連結隨 H1 完成自動生效 ✅

### P1 完成備註（型別檢查器對齊 pyrefly，2026-05-16）

實際改動 6 處：
1. `.claude/settings.json` PostToolUse hook —— `pyright` → `pyrefly check`
2. `.claude/settings.md` —— Pyright Type Check 章節改名 + 指令
3. `.claude/agents/code-reviewer.md` —— Review Process 第 2 條
4. `.claude/skills/systematic-debugging/SKILL.md` —— Checklist 行
5. `.claude/skills/code-quality/SKILL.md` —— frontmatter description + 指令
6. `.claude/commands/fix.md` —— `ty check` → `pyrefly check`

驗證：`grep -rE "pyright|ty check" .claude/` 已無命中（LICENSE.txt 例外）。
`pyrefly check [FILES]...` 接受檔案/目錄/glob 參數。

### F6 — 標註 Django skills 的 htmx 段落 🟡 P2 ✅ DONE (2026-05-16)

- 三個 Django skills 各於最 htmx-concentrated 的章節下，加上註記：
  > **註**：本專案目前未使用 htmx —— 以下段落暫不適用，僅供未來引入時參考。
- 註記位置：
  - `django-forms/SKILL.md` —— `**HTMX handling:**` 子節下
  - `django-templates/SKILL.md` —— `Partials and Components` 章節下
  - `pytest-django-patterns/SKILL.md` —— `### Testing HTMX Responses` 章節下
- htmx 內文全數保留（為未來引入留路）。

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
| ~~**P1**~~ | ~~型別檢查器~~ | ✅ 已拍板對齊 `pyrefly`（2026-05-16）—— pyright/ty 都不是專案實際使用工具 | — |
| ~~**P2**~~ | ~~htmx 去留~~ | ✅ 拍板「永不引入」（2026-05-16）—— README 已刪 htmx-patterns 行；F4/F5 刪 htmx 段；F6 三 Django skills 加未用註記（內文保留） | — |
| ~~**P3**~~ | ~~`django-extensions` 套件~~ | ✅ 拍板「不裝」（2026-05-16）—— 無使用訊號；skill 加 DORMANT 註記 | — |
| ~~**P4**~~ | ~~品質檢查入口~~ | ✅ 拍板（2026-05-16）—— 內迴圈 `/fix`；PR 前 `/code-quality` + `code-reviewer`；CI 走 `make check` + `make test`。詳見 `SKILLS_POLICY.md` §5 | — |

> **進度**：P1、P2、P3、P4 全部拍板完成 (2026-05-16)。

---

## 7. 建議執行順序

```
第 1 波（解鎖 + 零風險）✅ 完成 (2026-05-16)
  ├─ P1  對齊 pyrefly                ✅ DONE（含 F3/F4/F5 型別部分）
  ├─ P2  拍板 htmx「永不引入」       ✅ DONE
  ├─ F1  卸除 uv plugin              ✅ DONE
  ├─ F2  清 README 幽靈名單          ✅ DONE
  ├─ F3  修 code-quality             ✅ DONE
  ├─ F4  修 systematic-debugging     ✅ DONE
  ├─ F5  修本地 code-reviewer agent  ✅ DONE
  ├─ F6  Django skills htmx 註記     ✅ DONE
  └─ H1  建立 celery-patterns        ✅ DONE

第 2 波（補洞）✅ 完成 (2026-05-16)
  └─ H2  建立 storage-s3            ✅ DONE

第 3 波（深度 + 政策）✅ 完成 (2026-05-16)
  ├─ H3  建立 opentelemetry-patterns ✅ DONE
  ├─ C1  寫 python-engineering 啟用政策 ✅ DONE（SKILLS_POLICY.md）
  ├─ P3  決定 django-extensions 套件 ✅ DONE（不裝，DORMANT）
  └─ P4  品質檢查鏈入口             ✅ DONE（寫入 SKILLS_POLICY.md §5）
```

---

## 8. 一頁速覽

**招募 3 個** ✅：`celery-patterns`、`storage-s3`、`opentelemetry-patterns`

**資遣 2 項** ✅：卸 `uv` plugin、清 README 幽靈名單

**整頓 4 個** ✅（修假訊號）：`code-quality`、`systematic-debugging`、本地 `code-reviewer`、3 個 Django skills 的 htmx 段

**待決 4 案** ✅：P1（pyrefly）、P2（htmx 不引入）、P3（django-extensions 不裝）、P4（品質檢查鏈）。全部拍板。

**政策** ✅：新建 `.claude/SKILLS_POLICY.md` 列管 python-engineering plugin。

**不動**：9 個本地 skill 主體、2 個本地 agent、`python-engineering` plugin（留著用 8 個）、
`caveman`（使用者偏好）、`nuxt-skills`（屬 jen-lab，非本專案）

---

*所有任務 (P1–P4、F1–F6、H1–H3、C1) 於 2026-05-16 完成。*
*配套文件：`SKILLS_RESEARCH.md`（研究與評分依據）、`.claude/SKILLS_POLICY.md`（plugin 啟用政策）。*
