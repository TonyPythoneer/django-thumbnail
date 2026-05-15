# SKILLS_RESEARCH.md — Skills 盤點、比較與採用建議

> **文件目的**：盤點本機所有可用的 Claude Code skills / agents，針對 `django-thumbnail`
> 這個 Django + Celery 專案，判斷哪些「有實務價值且非常實用」，哪些是雜訊。
>
> **撰寫視角**：本文以四個角色聯合審查 —— **CTO**(風險、一致性、可信度)、
> **Engineering Manager**(流程、開發迴圈、CI 閘門)、**Principal Engineer**(設計、架構、正確性)、
> **QA**(測試、覆蓋率、邊界案例)。每個結論都標註是哪個角色在說話。
>
> **評估基準日**：2026-05-14　**評估分支**：`refactor/simply`
>
> **狀態**：草稿 — 等待 review。本文只做研究與建議，**未變更任何程式碼或設定**。

---

## 0. 執行摘要（CTO 視角）

一句話：**專案自己的 9 個本地 skills 是主力，`python-engineering` 外掛挑 8 個來補，
其餘約 60 個 skills 對本專案是雜訊或直接有害，不要開。**

| 分層 | 數量 | 說明 |
|---|---|---|
| 🟢 採用（核心） | 12 | 每天開發迴圈會用到，契合度高 |
| 🟡 情境採用 | 9 | 特定任務才開（重構、發版前 QA、補測試） |
| 🔴 不採用 | ~60 | 技術棧不符（CLI/TUI/打包/Nuxt）、或依賴未安裝的外掛、或對 532 行的小專案過度設計 |

**三個必須先處理的風險**（細節見 §6）：

1. **型別檢查器精神分裂** —— 專案有 `pyrightconfig.json`(pyright)，但 `python-engineering`
   全系列預設 `ty`。兩邊指令打架。而且 pyright 根本沒裝進 `uv`、CI 也沒跑。**先決定一個。**
2. **`celery-patterns` skill 不存在但到處被引用** —— 這是個 Celery worker 專案，核心 skill
   卻是空的。`django-models`、`systematic-debugging`、`code-reviewer` 三處的 Integration 段都指向它。
3. **文件在說謊** —— `CLAUDE.md` 指向不存在的 `tasks/THUMBNAIL_WORKER.md`、寫錯分支名、
   寫錯 phase；`.claude/skills/README.md` 列了 16 個 skills 但磁碟上只有 9 個。
   skills 還沒用，入口文件就先誤導人。

---

## 1. 評估基準 —— 專案實況

判斷一個 skill 有沒有用，得先釘死「拿來對照的專案長什麼樣」。

### 1.1 技術棧與規模

| 項目 | 實況 |
|---|---|
| 框架 | Django 6.0（**Web 專案，不是 CLI**） |
| 背景工作 | Celery 5.6 + Redis broker，`@shared_task` |
| 儲存 | `boto3` → MinIO（S3 相容），`InternalS3` / `PublicS3` singleton |
| 觀測性 | OpenTelemetry → Jaeger，`telemetry.py` |
| 前端 | `django-bootstrap5` + 純 JS fetch；**沒有 htmx、沒有 DRF**，view 回 `JsonResponse` |
| Python | 3.14 |
| 測試 | `pytest` + `pytest-django` + `factory-boy` + `pytest-xdist` + `pytest-cov` |
| 靜態檢查 | `ruff`（lint/format）。`pyrightconfig.json` 存在但 **pyright 未列入依賴、CI 未跑** |
| 套件管理 | `uv` |
| 核心程式碼量 | `images/` app 約 **532 行**（views 200 / models 157 / tasks 91 / utils 74 / forms 10） |

### 1.2 目前進行中的工作

- 分支 `refactor/simply`，主旨：**為效能與行數精簡而重構，但不犧牲可讀性**。
- `tasks/refinement/` 有一份 11 個檔案的重構清單（00–10），已用 CTO / Solution Architect / QA
  三視角審過。本文的 skill 建議會直接對應到這份清單的任務編號。

### 1.3 已確認的環境落差（會影響 skill 契合度）

- ❌ **未安裝** `django-extensions` —— 但有一個 `django-extensions` skill。
- ❌ **未安裝** `htmx`、`django-debug-toolbar` —— 但多個 skill 在教 HTMX / Debug Toolbar。
- ❌ **沒有** `.pre-commit-config.yaml`、沒有 `[tool.ruff]` 設定區段。
- ❌ CI 只跑 `ruff check` + `pytest`；沒有 `ruff format --check`、沒有型別檢查、沒有覆蓋率閘門。
- ❌ `pyright` 已設定但未實際接上工具鏈。

---

## 2. 可用 Skills 全盤清單

| 來源 | 數量 | 對本專案的整體價值 |
|---|---|---|
| **專案本地** `.claude/skills/` | 9 skills | ★★★★★ 為這個 codebase 量身寫的，主力 |
| **專案本地** `.claude/agents/` | 2 agents（`code-reviewer`、`github-workflow`） | ★★★★☆ Django 感知的審查者 + Git 流程 |
| **`python-engineering`** 外掛 | ~42 skills + 6 agents | ★★★☆☆ 深度高，但偏 CLI/打包；要篩 |
| **`caveman`** 外掛 | 5 skills | ★★☆☆☆ 溝通風格工具，與程式品質無關 |
| **`nuxt-skills`** 外掛 | ~20 skills | ☆☆☆☆☆ Vue/Nuxt 前端，技術棧完全不符，全部跳過 |
| **使用者/內建** | ~12 skills（`simplify`、`fix`、`review`、`security-review`、`init`…） | ★★★☆☆ 幾個與重構分支高度相關 |

> 註：`.claude/skills/README.md` 宣稱有 16 個 skills，但磁碟上只有 9 個。缺的 7 個
> （`onboard`、`ticket`、`pr-review`、`pr-summary`、`worktree-commit-merge`、`htmx-patterns`、
> **`celery-patterns`**）要嘛被刪了沒更新 README，要嘛從未建立。見 §6.6、§7。

---

## 3. 評分標準

每個 skill 用兩個軸 + 一個結論：

- **Fit（契合度 1–5）**：跟「§1 專案實況」對得上嗎？技術棧、規模、現階段工作。
- **Quality（品質 1–5）**：skill 本身寫得好不好？具體、有原則、可執行。
- **Verdict**：🟢 採用　/　🟡 情境採用　/　🔴 不採用

一個 skill 可以「品質很高但契合度很低」（例：`typer` 寫得很好，但本專案沒有 CLI）——
這種就是 🔴。**契合度優先於品質。**

---

## 4. 詳細比較與判斷

### 4.1 🟢 Tier 1 — 採用（核心開發迴圈）

| Skill / Agent | 來源 | Fit | Quality | 一句話理由 |
|---|---|:--:|:--:|---|
| `django-models` | 本地 | 5 | 5 | Fat models、QuerySet 組合、N+1 —— 正中 `Image`/`ImageTask` 設計與 refinement #05 |
| `pytest-django-patterns` | 本地 | 5 | 5 | 完全對應現有測試棧（pytest-django + factory-boy + xdist） |
| `systematic-debugging` | 本地 | 5 | 4 | Django 化的「先找根因再修」四階段，紀律價值高 |
| `docs-sync` | 本地 | 5 | 4 | 此刻就需要：CLAUDE.md / README 全在漂移（refinement #01） |
| `code-quality` | 本地 | 4 | 3 | 跑專案實際的檢查；但指令含 pyright，需與 §6.1 一起校正 |
| `django-forms` | 本地 | 4 | 4 | `images/forms.py` 雖小，上傳表單驗證仍走這套 |
| `django-templates` | 本地 | 3 | 4 | 3 個 bootstrap 頁面用得到；HTMX partial 段落對本專案無效（沒裝 htmx） |
| `skill-creator` | 本地 | 4 | 4 | 拿來補 §7 的缺口 skill（尤其 `celery-patterns`） |
| `code-reviewer`（agent） | 本地 | 5 | 4 | Django 感知、看 `git diff`、opus 模型 —— 本專案正確的審查者 |
| `github-workflow`（agent） | 本地 | 4 | 4 | 專案有 commit 慣例（`refactor(otel): …`），交給它一致性高 |
| `simplify` | 內建 | 5 | 4 | 字面上就是 `refactor/simply` 分支的工作：審查變更、找重用、修問題 |
| `fix` | 本地指令 | 4 | 4 | 改檔後的快速內迴圈（ruff check + format + 型別檢查）；型別檢查器需對齊 §6.1 |

**逐項 Pros / Cons：**

#### `django-models`（本地）
- **Pros**：把「業務邏輯放 model、view 保持輕薄」講透；QuerySet 即 manager 的模式直接適用
  `Image.objects.for_user()`；N+1、`select_related`/`prefetch_related`、`.exists()` 的鐵則正好命中
  refinement #05 的真實 N+1。
- **Cons**：偏通用 Django，沒有本專案特有的 `ImageTask` retry-history 語境（那是 domain 知識，
  得靠 `CLAUDE.md` §4 補）。
- **誰在用**：Principal Engineer 改 model、QA 驗 QuerySet 效能。

#### `pytest-django-patterns`（本地）
- **Pros**：TDD red-green-refactor、`@pytest.mark.django_db`、factory-boy、view/form/model/task
  各自「測什麼」的清單都齊；和 `pyproject.toml` 的測試設定一致。
- **Cons**：HTMX 測試段落（`HTTP_HX_REQUEST`）對本專案無效；範例的目錄結構（`tests/apps/...`）
  與本專案的 `images/tests/` 不同，需心裡換算。
- **誰在用**：QA 主力；refinement #08「強化測試」直接靠它。

#### `systematic-debugging`（本地）
- **Pros**：「NO FIXES WITHOUT ROOT CAUSE FIRST」是好紀律；先寫 failing test 重現、
  `CaptureQueriesContext` 數查詢、Celery `ALWAYS_EAGER` 都實用。
- **Cons**：教的 Django Debug Toolbar **沒裝**；HTMX 段落無效；checklist 寫 `uv run pyright` —— 見 §6.1。
- **誰在用**：所有人遇到 bug 時；QA 修 flaky test。

#### `docs-sync`（本地）
- **Pros**：簡單但**此刻最值錢**。CLAUDE.md 指向不存在的檔案、README 描述舊架構 —— 這 skill
  就是用來抓這種漂移。
- **Cons**：流程很陽春（grep git log）；「只報真的錯、不補沒寫的文件」這原則要守住。
- **誰在用**：CTO 要「門面不能說謊」；對應 refinement #01。

#### `code-quality`（本地）
- **Pros**：把專案該跑的檢查列成一條龍 + 人工 review checklist（N+1、idempotent task、
  factory 而非裸物件）。
- **Cons**：指令寫 `uv run pyright`，但 pyright 沒進依賴；checklist 也有 HTMX 項。**需要先修這個 skill。**
- **誰在用**：EM 當作 PR 前自檢清單。

#### `django-forms` / `django-templates`（本地）
- **Pros**：簡潔、原則正確（驗證放 form 不放 view；template 不放邏輯；用 URL name）。
- **Cons**：兩者都有 HTMX 段落 —— 本專案沒裝 htmx，那些段落請忽略。`django-templates` 契合度
  只有 3，因為前端很薄。
- **誰在用**：Principal Engineer 碰上傳表單 / 頁面時。

#### `skill-creator`（本地）
- **Pros**：本專案 skill 體系有缺口（§7），需要它來補；frontmatter 規格、description 寫法都講清楚。
- **Cons**：本身不產生專案價值，是「製造工具的工具」。
- **誰在用**：EM 決定補 `celery-patterns` 等缺口時。

#### `code-reviewer`（本地 agent）
- **Pros**：Django 專屬 checklist（HTTP method、status code、QuerySet 最佳化、Celery idempotent、
  CSRF）；跑 `git diff` 聚焦變更；用 opus。
- **Cons**：同樣寫 `uv run pyright`；提到 `request.htmx`（沒裝）。與 `python-engineering:code-reviewer`
  撞名，必須二選一 —— 見 §6.2。
- **誰在用**：QA / EM 在每個 PR 前；**本專案請用這個，不要用 python-engineering 版**。

#### `github-workflow`（本地 agent）
- **Pros**：commit / branch / PR 都照專案慣例走；近期 commit（`refactor(otel): …`）顯示有
  Conventional Commits 慣例，交給它最一致。
- **Cons**：記憶中有「不自動 commit、改完等核准」的偏好 —— 用這個 agent 時要守住這條。
- **誰在用**：所有人要產 commit / PR 時。

#### `simplify`（內建）
- **Pros**：字面對應 `refactor/simply` 分支 —— 審查變更程式、找重用/品質/效率問題並修正。
- **Cons**：通用，不懂 Django 慣例；要和 `django-models` 等搭配。
- **誰在用**：Principal Engineer 跑 refinement #03–#07 時。

#### `fix`（本地指令）
- **Pros**：只對「改過的檔案」跑 `ruff check` + `ruff format --check` + 型別檢查，快速內迴圈。
- **Cons**：預設跑 `ty check`，與專案的 pyright 不一致 —— 見 §6.1。
- **誰在用**：所有人每次存檔後。

---

### 4.2 🟡 Tier 2 — 情境採用（特定任務才開）

| Skill / Agent | 來源 | Fit | Quality | 何時開 |
|---|---|:--:|:--:|---|
| `python3-web` | python-engineering | 4 | 4 | refinement #04「views slim」—— route/domain/data 分層、Django async 陷阱 |
| `comprehensive-test-review` | python-engineering | 4 | 4 | refinement #08 / #10 —— 發版前的測試套件稽核 |
| `python-pytest-architect`（agent） | python-engineering | 4 | 4 | 需要有人「先寫失敗測試」時（refinement #08） |
| `modernpython` | python-engineering | 4 | 4 | Py3.14 專案 + 精簡分支 —— match-case / walrus / StrEnum，但忽略其 Typer/Rich 半部 |
| `python3-core` | python-engineering | 4 | 4 | 想要一份「函式 <50 行、不用 Any、展開縮寫」的通用基準時 |
| `python3-typing` | python-engineering | 3 | 4 | 強化 view 的 JSON-body 解析、S3 邊界型別時（refinement #04） |
| `python3-testing` | python-engineering | 3 | 4 | 需要覆蓋率目標、fixture 階層、property-based test 深度時（補 `pytest-django-patterns`） |
| `security-review` | 內建 | 4 | – | 發版前 / 合併前對分支做安全檢查（owner isolation、上傳處理） |
| `init` | 內建 | 4 | – | refinement #01 重寫 `CLAUDE.md` 時 |

**重點說明：**

- **`python3-web`**：對 Django 的著墨是「陷阱表」（`aget()` vs 阻塞、CORS、ORM 別當 API schema），
  本體偏 FastAPI/Pydantic。把它當「分層紀律的 checklist」用 —— refinement #04 要把 view 裡複製
  三次的 JSON 解析抽掉、把手刻 dict 換成 `Image.to_dict()`，這 skill 的「route handler 不含業務
  邏輯」正好是那條原則。
- **`comprehensive-test-review`**：checklist 驅動（80% line/branch、AAA、pytest-mock、隔離性、
  flaky 偵測），輸出按 HIGH/MEDIUM/LOW 分級。QA 在 refinement #10「驗收閘門」用。
- **`python-pytest-architect`（agent）**：強制型別註記、pytest-mock、AAA、80% 覆蓋。適合
  refinement #08「`latest_task` / retry history 這條 domain invariant 沒測」的補洞工作。
- **`modernpython`**：有 PEP 出處，對「精簡但不犧牲可讀性」的分支目標有用。**但近半篇在講
  Typer/Rich**，那部分對本專案無效。
- **`python3-core` / `python3-typing` / `python3-testing`**：`python-engineering` 的地基三件。
  品質好、原則正確，但都會把你導向 `ty`、`prek`、`src/` 佈局 —— 與本專案有摩擦。當「參考標準」
  讀，不要照抄指令。
- **`security-review`**：本專案有「owner isolation」鐵則、有檔案上傳 —— 這是真實攻擊面，
  合併前值得跑。
- **`init`**：`CLAUDE.md` 已過期，重寫時可用；但本專案 `CLAUDE.md` 結構已客製化，init 產的是
  通用骨架，需手動融合。

---

### 4.3 🔴 Tier 3 — 不採用（附原因，避免日後重新評估）

| 類別 | Skills | 不用的原因 |
|---|---|---|
| **CLI / TUI** | `typer`、`typer-and-rich`、`python3-cli`、`textual`、`designing-ui-for-cli`、`python-cross-platform-smoothing`、`shebangpython`、`python-cli-architect`(agent)、`python-cli-design-spec`(agent) | 本專案是 Django Web app，**沒有任何 CLI/TUI**。這些 skill 品質很高但契合度 1。 |
| **打包 / 發布** | `python3-packaging`、`hatchling`、`python3-publish-release-pipeline`、`pypi-readme-creator`、`mkdocs`、`toml-python` | 不是要發佈到 PyPI 的套件，是個應用程式。 |
| **資料工程** | `python3-data` | 沒有 pandas / polars / dataframe。 |
| **受限環境** | `python3-stdlib-only` | 不是 airgapped，正常用 `uv`。 |
| **非同步** | `async-python-patterns` | Celery 不是 asyncio；Django view 是同步的。契合度低。 |
| **重型重構工作流** | `stinkysnake`、`snakepolish` | 對 532 行的小專案是過度設計；`tasks/refinement/` 那份客製清單已經把這件事做得更貼。 |
| **編排 / SAM** | `orchestrate`、`orchestrating-python-development`、`create-feature-task`、`python3-add-feature`、`specialist-skill-routing` | SAM track 依賴未安裝的 `dh:` 外掛與 MCP 工具；Direct track 又把實作導去 CLI architect。對本專案是壞掉的或不適用的。 |
| **型別檢查器** | `ty` | 專案用 **pyright**（`pyrightconfig.json`）。除非刻意遷移（見 §6.1），否則此 skill 不適用。 |
| **重複的工作流** | `debug`、`lint`、`cleanup`、`review` | 與本地的 `systematic-debugging` / `code-quality` / `simplify` / 本地 `code-reviewer` 功能重疊，且預設 `prek`+`ty`。本地版契合度更高。 |
| **測試架構** | `python3-test-design` | 為大型測試套件做金字塔規劃 —— 對本專案規模過重。 |
| **其他外掛** | `python-engineering:code-reviewer`(agent)、`adversarial-solution-design`(agent 部分情況) | 見 §6.2 / §6.7。 |
| **Nuxt 全系列** | `nuxt-skills:*`（~20 個） | Vue/Nuxt 前端框架，技術棧完全不符。 |
| **溝通風格** | `caveman:*`（5 個） | 與程式品質無關的輸出風格工具；目前 session 有開，但不影響專案。 |
| **harness 雜項** | `loop`、`schedule`、`keybindings-help`、`statusline-setup`、`claude-api`、`fewer-permission-prompts`、`update-config` | 環境/操作層工具，非專案品質工具。`update-config`/`fewer-permission-prompts` 偶爾有運維價值，但不進開發迴圈。 |

> **`adversarial-solution-design`(agent)** 放在灰色地帶：實作前先挑戰方案、列 2–3 個替代解、
> 設計行為驗證計畫 —— 紀律很好。但對 532 行專案、又有現成 refinement 清單的情況，多數任務
> 用不到這層。**列為「大改動才開」的情境工具**，不進 Tier 2 常用清單。

---

## 5. 四角色分析

同一份清單，四個角色在意的點不同。以下是各自的取捨。

### 5.1 CTO —— 風險、一致性、可信度、成本

- **最大隱憂是「工具精神分裂」**：pyright vs ty、兩個 code-reviewer、四個品質檢查入口
  （`code-quality` / `lint` / `fix` / `review`）。skills 越多，彼此打架的機率越高，新人越混亂。
  **結論：寧可少而一致。本地 9 個 + python-engineering 精選 8 個就夠。**
- **門面要先修**：`CLAUDE.md` 和 `.claude/skills/README.md` 都在說謊。skill 體系的可信度從
  入口文件開始崩。先跑 `docs-sync`，對應 refinement #01。
- **外掛依賴是供應鏈風險**：`python-engineering:code-reviewer` 依賴 `dh:`、`holistic-linting`
  外掛，`orchestrate` 依賴 SAM MCP 工具 —— 這些沒裝。採用依賴外部外掛的 skill = 把專案品質
  綁在你不控制的東西上。**優先用本地 skills。**
- **成本**：skills 不是免費的，每個都佔 context、都要維護。~60 個 Tier 3 應該明確標記不用，
  避免每次都重新評估。

### 5.2 Engineering Manager —— 開發迴圈、流程、CI 閘門

- **內迴圈**（每次存檔）：`fix` → 快。
- **改一個功能**：`django-models` / `django-forms` → 寫碼，`pytest-django-patterns` → 測試，
  `simplify` → 收斂。
- **PR 前**：本地 `code-reviewer`(agent) + `code-quality`。
- **合併 / 發版前**：`comprehensive-test-review` + `security-review` + `docs-sync`。
- **CI 缺口很明顯**（refinement #09）：目前 CI 只有 `ruff check` + `pytest`。應補
  `ruff format --check`、型別檢查、覆蓋率閘門。`pre-commit` skill 可參考，但**本專案目前沒有
  `.pre-commit-config.yaml`** —— 要嘛建一份，要嘛把閘門直接寫進 GitHub Actions。EM 要先決定。
- **流程上不要引入 SAM/orchestrate**：那套需要的外掛沒裝，硬上只會卡住。本專案規模用
  「Direct track」心智 + 本地 skills 就夠。

### 5.3 Principal Engineer —— 設計、架構、正確性

- **核心設計工具**：`django-models`（QuerySet 組合、fat model）+ `python3-web`（route/domain/data
  分層）—— 這兩個直接支援 refinement #03（storage module 抽出）、#04（views slim）、#05（N+1）。
- **型別**：`python3-typing` 的「邊界驗證」觀念適用 —— view 的 JSON-body 解析、S3 client 邊界
  都是 raw data 進入點。但**先解決 pyright vs ty**，否則型別建議無處落地。
- **現代化**：`modernpython` 對 Py3.14 有用（match-case、StrEnum、`e.add_note()`），契合精簡分支
  的目標。注意只取 typing/語法部分。
- **不要過度抽象**：refinement #00 的 guardrail 寫得很清楚 ——「沒有為了以後的新抽象」。
  這代表 `stinkysnake`、`python3-test-design` 這類「大架構」skill 對 532 行專案是反效果。
  Principal Engineer 的判斷：**skill 是參考，不是必須照做的儀式。**

### 5.4 QA —— 測試、覆蓋率、邊界、閘門

- **寫測試**：`pytest-django-patterns`（怎麼寫 Django 測試）。
- **稽核測試**：`comprehensive-test-review`（80% line/branch、AAA、pytest-mock、flaky 偵測）。
- **補洞**：`python-pytest-architect`(agent) —— refinement #08 點名的「`latest_task` retry-history
  沒測、沒有 HTML view 測試、retry 耗盡路徑沒測」。
- **測試失敗時的心態**：`python-engineering` 有 `test-failure-mindset` / `analyze-test-failures`，
  核心是「雙假設：可能是 code 錯，也可能是 test 錯，別自動改 test 遷就 code」。這觀念好，
  但本地的 `systematic-debugging` 已含「先寫失敗測試重現」，QA 可把雙假設當補充心法，
  不必特地開那兩個 skill。
- **覆蓋率閘門**：`pytest-cov` 裝了但沒閘門（refinement #09）。QA 要推動 `--cov-fail-under`。
- **QA 的紅線**：`code-quality` 和本地 `code-reviewer` 的 checklist 裡有 HTMX 項目 —— 本專案
  沒 htmx，這些是**假訊號**，會讓 review 失焦。需修掉（見 §6.6）。

---

## 6. 衝突與風險（採用前必須拍板）

### 6.1 型別檢查器：pyright vs ty 🔴 高

- **現況**：專案根目錄有 `pyrightconfig.json`（指定 Django stubs、Py3.14），但 `pyright`
  **不在** `pyproject.toml` 依賴、CI **沒跑**型別檢查。
- **衝突**：`python-engineering` 全系列（`python3-core`、`fix`、`debug`、`lint`…）預設 `ty`；
  本地 skills（`code-quality`、`systematic-debugging`）與本地 `code-reviewer` 預設 `pyright`。
- **`standards-for-python-development` 自己的規則**：「既有專案若已用某檢查器，**不要強迫遷移**」。
  本專案訊號指向 pyright。
- **建議**：二擇一並貫徹 ——
  - **(A) 留 pyright**：把 `pyright` 加進 dev 依賴、接進 CI；忽略 python-engineering 的 ty 指令。
  - **(B) 轉 ty**：刪/停用 `pyrightconfig.json`，把本地三個 skill 的指令改成 `ty`。
  - 不論哪個，**不要兩個都跑**。

### 6.2 兩個 `code-reviewer` agent 🟠 中

| | 本地 `code-reviewer` | `python-engineering:code-reviewer` |
|---|---|---|
| 取向 | Django 專屬（view/QuerySet/Celery/CSRF） | 通用 Python、typed-boundary |
| 模型 | opus | sonnet |
| 依賴 | 無外部外掛 | 需 `dh:`、`holistic-linting` 外掛 + SAM |
| 產出 | 直接回審查意見 | 寫 SAM task 檔到 `~/.dh/...` |
- **建議**：**本專案用本地版**。python-engineering 版需要沒安裝的外掛、且會去寫 SAM 計畫檔，
  在這裡是壞的。

### 6.3 兩套 debugging 工作流 🟡 低

`systematic-debugging`（本地，Django 化）vs `debug`（python-engineering，通用 6 階段）。
- **建議**：本地 `systematic-debugging` 為主。`debug` 的「雙假設、最小重現」當補充心法即可。

### 6.4 測試指引三處重疊 🟡 低（其實是分層，不算衝突）

- `pytest-django-patterns` = 怎麼**寫** Django 測試（日常）。
- `python3-testing` = 覆蓋率目標、fixture 階層、property-based（深度補充）。
- `comprehensive-test-review` = **稽核**既有測試套件（發版前）。
- **建議**：照上面分工用，不要在同一個任務同時開三個。

### 6.5 四個品質檢查入口 🟠 中

`code-quality`(本地) / `lint`(pe) / `fix`(本地指令) / `review`(pe) 功能重疊。
- **建議**：定一條鏈 —— 內迴圈 `fix`、PR 前 `code-quality` + 本地 `code-reviewer`。
  `lint` / `review` 不開（預設 prek/ty，且重複）。

### 6.6 文件與 skill metadata 漂移 🔴 高

- `CLAUDE.md`：指向不存在的 `tasks/THUMBNAIL_WORKER.md`；寫 `ty/thumbnail-worker-setup`
  分支（實際 `refactor/simply`）；寫 Phase 4（實際是 refinement 計畫）。
- `.claude/skills/README.md`：列 16 個 skills，磁碟只有 9 個。
- 多個 skill 教 HTMX / `django-extensions` / Debug Toolbar —— **這三個套件都沒裝**。
- **建議**：先跑 `docs-sync`（refinement #01）；修 `code-quality`、`systematic-debugging`、
  本地 `code-reviewer` 裡的 HTMX/pyright 假訊號；更新 README 反映真實的 9 個 skills。

### 6.7 `python-engineering` 假設與本專案不符 🟡 低

- 假設 `src/` 佈局、root 層 `tests/`；本專案是 Django app 佈局（`images/tests/`）。
- 假設 `prek`、`ty`、`tomlkit`、`pydantic` 等；本專案多數沒有。
- **建議**：python-engineering skills 一律當「**原則參考**」讀，**不要照抄指令**。

---

## 7. 缺口 —— 應該存在但沒有的 Skill

這是本研究**最有實務價值**的一段：與其引入不合的外部 skill，不如用 `skill-creator`
補本專案真正缺的。

| 缺口 | 嚴重度 | 理由 |
|---|:--:|---|
| **`celery-patterns`** | 🔴 高 | 這是個 Celery worker 專案。`django-models`、`systematic-debugging`、本地 `code-reviewer` 的 Integration 段**都引用它**，但檔案不存在。應涵蓋：`@shared_task` 慣例、retry/exponential backoff、idempotency（CLAUDE.md §5.8 鐵則）、傳 ID 不傳 instance、`ImageTask` 狀態流轉、`ALWAYS_EAGER` 測試。 |
| **`storage-s3` / `minio-patterns`** | 🟠 中 | 專案有 `InternalS3`/`PublicS3` singleton、MinIO、`boto3`；refinement #03 整個任務在講 storage module。沒有 skill 涵蓋 S3 client 建構、bucket 管理、`django-storages` 設定。 |
| **`opentelemetry-patterns`** | 🟡 低 | 專案有 `telemetry.py`、OTel 三個 instrumentor；記憶裡有「用 `span.set_attributes(dict)` 不要重複呼叫」「web 與 Celery worker 的 telemetry 要分開」等明確偏好。值得固化成 skill。 |
| `htmx-patterns` | ⚪ N/A | README 列了它，但**專案沒裝 htmx**。除非未來引入，否則**不要建**——並從 README 移除。 |

---

## 8. 建議行動方案

> 全部都是建議；本文未動任何程式碼/設定。請 review 後再決定執行。

### 即刻（清理門面，零風險）
1. **跑 `docs-sync`**，修 `CLAUDE.md`（壞掉的 task 檔路徑、分支名、phase）與
   `.claude/skills/README.md`（16 → 實際 9）。對應 refinement #01。
2. **拍板 §6.1**：pyright 或 ty 二擇一。
3. **修假訊號**：把 `code-quality`、`systematic-debugging`、本地 `code-reviewer` 裡的
   HTMX 段落與 `django-extensions` 假設拿掉或標註（這三個套件都沒裝）。

### 短期（補核心缺口）
4. **用 `skill-creator` 建 `celery-patterns`** —— 最高優先，核心 domain 卻空著。
5. 決定品質檢查鏈（§6.5）：內迴圈 `fix`、PR 前 `code-quality` + 本地 `code-reviewer`；
   其餘重複入口不開。
6. CI 補閘門（refinement #09）：`ruff format --check`、型別檢查、`--cov-fail-under`。

### 中期（深度補強）
7. 建 `storage-s3` skill（配合 refinement #03 一起做最省事）。
8. 把 OTel 的既有偏好固化成 `opentelemetry-patterns` skill。
9. 重構期間，把 `python3-web` / `modernpython` / `python3-typing` 當**參考標準**
   搭配 refinement #03–#07 使用 —— 讀原則，不抄指令。

---

## 9. 附錄 —— 完整對照表

### 9.1 🟢 採用（12）
`django-models`、`pytest-django-patterns`、`systematic-debugging`、`docs-sync`、
`code-quality`、`django-forms`、`django-templates`、`skill-creator`、
`code-reviewer`(本地 agent)、`github-workflow`(本地 agent)、`simplify`、`fix`

### 9.2 🟡 情境採用（9）
`python3-web`、`comprehensive-test-review`、`python-pytest-architect`(agent)、
`modernpython`、`python3-core`、`python3-typing`、`python3-testing`、
`security-review`、`init`
（外加 `adversarial-solution-design`(agent)、`test-failure-mindset`、`analyze-test-failures`
　—— 僅大改動 / 特殊情況才開）

### 9.3 🔴 不採用（摘要，完整原因見 §4.3）
- python-engineering CLI/TUI 全家：`typer`、`typer-and-rich`、`python3-cli`、`textual`、
  `designing-ui-for-cli`、`python-cross-platform-smoothing`、`shebangpython`、
  `python-cli-architect`、`python-cli-design-spec`
- 打包/發布：`python3-packaging`、`hatchling`、`python3-publish-release-pipeline`、
  `pypi-readme-creator`、`mkdocs`、`toml-python`
- 其他 python-engineering：`python3-data`、`python3-stdlib-only`、`async-python-patterns`、
  `stinkysnake`、`snakepolish`、`orchestrate`、`orchestrating-python-development`、
  `create-feature-task`、`python3-add-feature`、`specialist-skill-routing`、`ty`、
  `debug`、`lint`、`cleanup`、`review`、`python3-test-design`、`uv`、
  `python-engineering:code-reviewer`、`semantic-code-search`
- `nuxt-skills:*`（~20）、`caveman:*`（5）
- harness 雜項：`loop`、`schedule`、`keybindings-help`、`statusline-setup`、`claude-api`、
  `fewer-permission-prompts`、`update-config`、`find-skills`

### 9.4 評分快速索引

| Skill | Fit | Quality | Verdict |
|---|:--:|:--:|:--:|
| django-models | 5 | 5 | 🟢 |
| pytest-django-patterns | 5 | 5 | 🟢 |
| systematic-debugging | 5 | 4 | 🟢 |
| docs-sync | 5 | 4 | 🟢 |
| simplify | 5 | 4 | 🟢 |
| code-reviewer（本地） | 5 | 4 | 🟢 |
| code-quality | 4 | 3 | 🟢 |
| django-forms | 4 | 4 | 🟢 |
| skill-creator | 4 | 4 | 🟢 |
| github-workflow（本地） | 4 | 4 | 🟢 |
| fix | 4 | 4 | 🟢 |
| django-templates | 3 | 4 | 🟢 |
| python3-web | 4 | 4 | 🟡 |
| comprehensive-test-review | 4 | 4 | 🟡 |
| python-pytest-architect | 4 | 4 | 🟡 |
| modernpython | 4 | 4 | 🟡 |
| python3-core | 4 | 4 | 🟡 |
| security-review | 4 | – | 🟡 |
| init | 4 | – | 🟡 |
| python3-typing | 3 | 4 | 🟡 |
| python3-testing | 3 | 4 | 🟡 |
| adversarial-solution-design | 3 | 4 | 🟡 |
| python-engineering:code-reviewer | 1 | 4 | 🔴 |
| ty | 1 | 4 | 🔴 |
| typer / textual / python3-cli … | 1 | 4–5 | 🔴 |
| nuxt-skills:* | 0 | – | 🔴 |

---

*本文由 CTO / Engineering Manager / Principal Engineer / QA 四視角聯合審查產出。*
*所有建議僅供 review；尚未對 codebase 或設定做任何變更。*
