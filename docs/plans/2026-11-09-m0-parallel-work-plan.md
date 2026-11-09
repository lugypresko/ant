# M0 Parallel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** לבנות M0 של מפעל הקוד באמצעות Taskcell כבסיס, תוך חלוקה למשימות אטומיות שמספר סוכנים יכולים לבצע במקביל ללא עריכה מתנגשת.

**Architecture:** המאגר הוא Integration Repository דק. Taskcell נשמר כתלות חיצונית מקובעת ולא מועתק במלואו; שכבות החוזים, ה־Gatekeeper המבודד, הראיות והניסוי נשארות בבעלות `ant`. קוד המפעל נכתב ב־TypeScript, ו־Golden Repository ובדיקות הקבלה נכתבים ב־Python.

**Tech Stack:** Node.js 22, TypeScript 5, pnpm, Vitest, Taskcell pinned upstream, Docker/Firecracker adapter boundary, Python 3.12, FastAPI, SQLAlchemy 2, Alembic, SQLite, pytest, Ruff, JSON Schema, GitHub Actions.

---

## 1. כללי עבודה מחייבים

### 1.1 בעלות על קבצים

לכל Work Package יש רשימת `Owned paths`. רק הסוכן שמונה למשימה רשאי לשנות אותם. סוכן לא משנה קובץ משותף גם אם השינוי קטן.

הקבצים הבאים בבעלות בלעדית של Integration Owner:

- `package.json`
- `pnpm-lock.yaml`
- `pnpm-workspace.yaml`
- `tsconfig.base.json`
- `.github/workflows/**`
- `docs/plans/2026-11-09-m0-parallel-work-plan.md`
- `integration/status.json`
- כל קובץ תחת `integration/decisions/`
- `integration/requests/` למעט קובץ הבקשה היחיד ששמו זהה ל־Work Package של הסוכן

אם סוכן צריך שינוי בקובץ משותף, הוא רשאי ליצור רק את קובץ הבקשה השייך למשימה שלו:

```text
integration/requests/<work-package-id>.json
```

לדוגמה, WP-120 רשאי ליצור רק `integration/requests/WP-120.json`. ה־Integration Owner בודק ומיישם את הבקשה. אין לסוכן הרשאה לערוך קובץ בקשה של משימה אחרת או את קובץ היעד המשותף.

### 1.2 ענפים ו־worktrees

כל משימה עובדת בענף וב־worktree נפרדים:

```text
branch:    work/<work-package-id>-<short-name>
worktree:  .worktrees/<work-package-id>-<short-name>
```

כל סוכן מתחיל מה־SHA שמופיע בעמודת `Base` בטבלת הגלים. אין לבצע merge של ענף סוכן לענף סוכן אחר. רק Integration Owner מבצע cherry-pick לענף `integration/m0`.

### 1.3 חוזי handoff

כל משימה מסתיימת בקובץ:

```text
handoffs/<work-package-id>.json
```

הקובץ כולל:

```json
{
  "work_package": "WP-000",
  "base_sha": "git-sha",
  "result_sha": "git-sha",
  "owned_paths": [],
  "contracts_consumed": [],
  "contracts_produced": [],
  "commands_run": [],
  "tests": [],
  "known_gaps": [],
  "shared_file_requests": []
}
```

סוכן אינו מסמן משימה כשלמה ללא commit יחיד או סדרת commits נקייה, בדיקות ירוקות ו־handoff תקין.

### 1.4 חוזים קפואים

הנתיבים הבאים מוקפאים לאחר Gate 0:

- `contracts/product/**`
- `contracts/http/**`
- `contracts/security/**`
- `contracts/budget/**`
- `contracts/repository/**`
- `contracts/evidence/**`

שינוי בהם דורש ADR חדש תחת `integration/decisions/`, העלאת `contract_version`, ו־revalidation של כל Work Package שתלוי בגרסה הישנה.

### 1.5 Definition of Done לכל משימה

1. הסוכן שינה רק `Owned paths` שלו.
2. אין secrets, credentials או generated artifacts ב־Git.
3. הבדיקות הממוקדות עוברות.
4. lint/typecheck של החבילה עובר.
5. נוצר handoff manifest.
6. ה־commit message מתחיל ב־Work Package ID.
7. Integration Owner מצליח לבצע cherry-pick ללא conflict.

## 2. מבנה היעד

```text
ant/
├── contracts/                 # חוזים קפואים ו־JSON Schemas
├── benchmark/
│   ├── template/              # Golden Python repository
│   ├── acceptance/            # בדיקות חיצוניות וקפואות
│   └── fixtures/
├── factory/
│   ├── taskcell-adapter/
│   ├── environment/
│   ├── gatekeeper/
│   ├── budget/
│   ├── evidence/
│   ├── controller/
│   ├── delivery/
│   └── strategies/
├── experiments/
├── integration/
│   ├── decisions/
│   ├── requests/
│   └── status.json
├── handoffs/
└── docs/
```

## 3. גלי ביצוע

| Wave | משימות מקביליות | Base | Integration gate |
|---|---|---|---|
| 0 | WP-000 בלבד | `main` | Bootstrap commit |
| 1 | WP-010, WP-011, WP-012, WP-013, WP-014, WP-015 | Bootstrap SHA | Gate 0 — contracts freeze |
| 2 | WP-100, WP-110, WP-120, WP-130, WP-140 | Gate 0 SHA | Component contract checks |
| 3 | WP-200, WP-210, WP-220, WP-230 | Wave 2 integration SHA | Gate 1 — isolated environment |
| 4 | WP-300, WP-310, WP-320 | Gate 1 SHA | Gate 2 — fake and real single-agent E2E |
| 5 | WP-400, WP-410 | Gate 2 SHA | Gate 3 — recoverable draft PR delivery |
| 6 | WP-500, WP-510, WP-520 | Gate 3 SHA | Gate 4 — paired experiment |

Integration Owner מפרסם SHA חדש לאחר כל Gate. משימות מהגל הבא אינן מתחילות לפני פרסום ה־SHA.

---

## 4. Wave 0 — Bootstrap

### WP-000: Workspace bootstrap

**Owner:** Integration Owner  
**Owned paths:** קובצי root המשותפים, `integration/**`, `handoffs/WP-000.json`

**Atomic steps:**

1. צור `integration/m0` מ־`main`.
2. כתוב בדיקה שנכשלת כאשר workspace packages אינם ניתנים לגילוי.
3. צור `package.json`,‏ `pnpm-workspace.yaml` ו־`tsconfig.base.json` מינימליים.
4. הוסף scripts: `typecheck`,‏ `lint`,‏ `test`,‏ `verify:contracts` ו־`verify:all`.
5. צור את תיקיות היעד עם `.gitkeep` רק כאשר נדרש.
6. צור `integration/status.json` עם כל ה־WP במצב `pending`.
7. הרץ `pnpm install --lockfile-only`.
8. הרץ `pnpm verify:all`; צפה למעבר של bootstrap checks בלבד.
9. כתוב `handoffs/WP-000.json`.
10. Commit: `WP-000 bootstrap parallel M0 workspace`.

**Exit:** Integration Owner מפרסם את Bootstrap SHA לכל סוכני Wave 1.

---

## 5. Wave 1 — Architecture Freeze

### WP-010: Product contract

**Owned paths:** `contracts/product/**`, `handoffs/WP-010.json`

**Atomic steps:**

1. כתוב schema test שנכשל ללא `product-contract.schema.json`.
2. הגדר `BusinessIntent`,‏ `AcceptanceCriterion`,‏ `CandidateCommit` ו־`DeliveryResult`.
3. קבע שהפלט המקומי הוא commit מאומת ושהפלט המרוחק הוא Draft PR בלבד.
4. הוסף fixture תקין ושישה fixtures לא תקינים.
5. הרץ רק את contract tests של החבילה.
6. כתוב handoff ו־commit: `WP-010 freeze product contract`.

### WP-011: HTTP benchmark contract

**Owned paths:** `contracts/http/**`, `handoffs/WP-011.json`

**Atomic steps:**

1. כתוב tests שנכשלים עבור request/response schemas חסרים.
2. הגדר create-order ו־get-order schemas.
3. קבע `Idempotency-Key`: אורך, תווים, canonical payload hash והתנהגות conflict.
4. קבע status codes וגוף שגיאה אחיד.
5. קבע את מבחן המקביליות: 8 בקשות, WAL,‏ busy timeout של 5 שניות ו־retry כולל עד 5 שניות.
6. הרץ schema tests.
7. כתוב handoff ו־commit: `WP-011 freeze order HTTP contract`.

### WP-012: Security and tool policy

**Owned paths:** `contracts/security/**`, `handoffs/WP-012.json`

**Atomic steps:**

1. כתוב policy tests שנכשלים כאשר capability חסרה בעלים.
2. הגדר execution ו־verification profiles נפרדים.
3. הגדר protected paths, filesystem roots, process limits ו־tool capabilities.
4. הגדר deny rules ל־DNS, direct IP, redirects, IPv6, metadata ו־private networks.
5. הגדר secret routing ו־redaction contract.
6. הרץ policy tests.
7. כתוב handoff ו־commit: `WP-012 freeze security and tool policy`.

### WP-013: Budget and cancellation contract

**Owned paths:** `contracts/budget/**`, `handoffs/WP-013.json`

**Atomic steps:**

1. כתוב tests שנכשלים עבור reservation שלילי או operation ללא reservation.
2. הגדר reserve, reconcile, release, exhaust ו־late usage events.
3. קבע שלושה ניסיונות בסך הכול ו־wall-clock deadline אחד למשימה.
4. קבע מה נספר בעלות: agent, repair, integration, verification ו־delivery.
5. קבע termination ו־credential revocation לאחר cancel/exhaustion.
6. הרץ contract tests.
7. כתוב handoff ו־commit: `WP-013 freeze budget and cancellation contract`.

### WP-014: Repository lifecycle contract

**Owned paths:** `contracts/repository/**`, `handoffs/WP-014.json`

**Atomic steps:**

1. כתוב lifecycle tests לכשל אחרי create, push ו־PR.
2. הגדר idempotency key של delivery.
3. הגדר private repository,‏ `main`, feature branch ו־Draft PR.
4. הגדר reconciliation וכ quarantine של remote conflict.
5. חסום merge, deploy, force-push ו־workflow modification.
6. הרץ contract tests.
7. כתוב handoff ו־commit: `WP-014 freeze repository lifecycle`.

### WP-015: Evidence contract

**Owned paths:** `contracts/evidence/**`, `handoffs/WP-015.json`

**Atomic steps:**

1. כתוב tests שנכשלים כאשר mandatory gate או hash חסר.
2. הגדר Trial, Attempt, GateResult, BudgetEvent, CleanupResult ו־DeliveryRecord schemas.
3. הגדר append-only journal ו־terminal manifest יחיד.
4. הגדר measured, estimated, reserved ו־late-reported costs.
5. הוסף fixtures ל־pass, fail, cancel, timeout ו־recovery.
6. הרץ schema tests.
7. כתוב handoff ו־commit: `WP-015 freeze evidence contract`.

### Gate 0 integration

**Integration Owner בלבד:**

1. Cherry-pick WP-010 עד WP-015 לפי מספר.
2. ודא שלא קיימת חפיפה בנתיבים.
3. הרץ `pnpm verify:contracts`.
4. צור `integration/decisions/ADR-0001-contract-freeze.md` עם hashes.
5. עדכן `integration/status.json`.
6. Commit: `GATE-0 freeze M0 contracts`.

---

## 6. Wave 2 — רכיבים בלתי תלויים

### WP-100: Golden Python template

**Consumes:** WP-010, WP-011  
**Owned paths:** `benchmark/template/**`, `handoffs/WP-100.json`

1. כתוב bootstrap test שנכשל כאשר template חסר.
2. צור FastAPI health endpoint, SQLAlchemy base ו־Alembic initial migration שאינם כוללים orders.
3. הוסף pytest ו־Ruff configuration בתוך template בלבד.
4. הוסף GitHub CI template אך אל תשנה root workflow.
5. בדוק upgrade, downgrade, Ruff ו־pytest על העתק זמני.
6. כתוב handoff ו־commit: `WP-100 add golden Python template`.

### WP-110: Frozen acceptance bundle

**Consumes:** WP-011, WP-015  
**Owned paths:** `benchmark/acceptance/**`, `benchmark/fixtures/**`, `handoffs/WP-110.json`

1. כתוב integrity test למיפוי REQ-1 עד REQ-7.
2. כתוב black-box tests ל־create/get/idempotency/conflict.
3. כתוב concurrency tests לפי החוזה הקפוא.
4. כתוב migration upgrade/downgrade tests.
5. ארוז bundle דטרמיניסטי וחשב SHA-256.
6. ודא שה־bundle נכשל מול template ללא feature.
7. כתוב handoff ו־commit: `WP-110 add frozen order acceptance bundle`.

### WP-120: Taskcell upstream and fake adapter

**Consumes:** WP-012, WP-013, WP-015  
**Owned paths:** `factory/taskcell-adapter/**`, `third_party/taskcell.lock`, `third_party/NOTICE.taskcell`, `handoffs/WP-120.json`

1. קבע revision של Taskcell ורישיון MIT בקובצי provenance.
2. כתוב adapter contract test עם fake process.
3. ממש `start`,‏ `cancel`,‏ `result`,‏ `usage`,‏ `trace` ו־`candidate` interfaces.
4. מַפּה Taskcell run artifacts לחוזה evidence בלי להריץ Agent אמיתי.
5. בדוק timeout, cancel, missing commit ו־malformed usage.
6. כתוב extension-gap report בתוך החבילה.
7. כתוב handoff ו־commit: `WP-120 add pinned Taskcell fake adapter`.

### WP-130: Evidence journal

**Consumes:** WP-015  
**Owned paths:** `factory/evidence/**`, `handoffs/WP-130.json`

1. כתוב tests ל־append, duplicate event, hash chain ו־atomic terminal promotion.
2. ממש append-only JSONL journal.
3. ממש redaction ו־content hashing.
4. ממש rebuild של manifest לאחר restart.
5. הזרק crash לפני ואחרי terminal promotion.
6. כתוב handoff ו־commit: `WP-130 add recovery-safe evidence journal`.

### WP-140: Environment image definitions

**Consumes:** WP-012  
**Owned paths:** `factory/environment/**`, `handoffs/WP-140.json`

1. כתוב tests שמוודאים ש־execution ו־verification profiles שונים.
2. צור image definitions עם גרסאות runtime נעולות.
3. צור readiness probe ו־image metadata schema.
4. אסור להכניס credentials ל־image layers.
5. בדוק reproducible labels ו־digest capture עם inert fixtures.
6. כתוב handoff ו־commit: `WP-140 add environment image profiles`.

---

## 7. Wave 3 — בידוד ואכיפה

### WP-200: Independent Gatekeeper

**Consumes:** WP-100, WP-110, WP-140  
**Owned paths:** `factory/gatekeeper/**`, `handoffs/WP-200.json`

1. כתוב fail-closed tests עבור gate חסר, skipped, timeout ו־empty suite.
2. ממש verification sandbox adapter שאינו משתף session עם Agent.
3. mount את acceptance bundle כ־read-only ובדוק hash לפני הרצה.
4. הרץ protected-path, Alembic, Ruff, repository pytest ו־acceptance gates בנפרד.
5. החזר רק typed results, exit codes, durations, hashes ו־redacted logs.
6. בדוק suite/evidence tampering.
7. כתוב handoff ו־commit: `WP-200 add isolated independent Gatekeeper`.

### WP-210: Budget ledger

**Consumes:** WP-013, WP-015  
**Owned paths:** `factory/budget/**`, `handoffs/WP-210.json`

1. כתוב reservation race tests.
2. ממש atomic reserve/reconcile/release.
3. חסום operation ללא יתרה.
4. בדוק late usage לאחר terminal state.
5. בדוק cancellation ו־deadline.
6. כתוב handoff ו־commit: `WP-210 add hard budget ledger`.

### WP-220: Workspace and recovery

**Consumes:** WP-014, WP-015, WP-130  
**Owned paths:** `factory/controller/src/workspace/**`, `factory/controller/test/workspace/**`, `handoffs/WP-220.json`

1. כתוב tests ליצירת trial directory ו־feature branch ייחודיים.
2. ממש resolved-path confinement.
3. ממש candidate commit capture.
4. הזרק crash אחרי commit ואחרי GateResult.
5. בצע reconcile ל־terminal manifest יחיד.
6. כתוב handoff ו־commit: `WP-220 add isolated recoverable workspaces`.

### WP-230: Environment isolation proof

**Consumes:** WP-012, WP-140, WP-200  
**Owned paths:** `factory/environment-tests/**`, `handoffs/WP-230.json`

1. כתוב host-file escape ו־process-tree tests.
2. כתוב DNS, direct IP, redirect, IPv6, metadata ו־private-network tests.
3. בדוק secret absence בסביבה, logs, artifacts ו־child process.
4. בדוק timeout, cancel ו־cleanup.
5. בדוק שאין ל־verification profile GitHub credential או evidence write access.
6. הפק Gate 1 evidence bundle.
7. כתוב handoff ו־commit: `WP-230 prove execution and verification isolation`.

---

## 8. Wave 4 — Single-Agent E2E

### WP-300: Deterministic controller

**Consumes:** WP-120, WP-130, WP-200, WP-210, WP-220  
**Owned paths:** `factory/controller/src/runtime/**`, `factory/controller/test/runtime/**`, `handoffs/WP-300.json`

1. כתוב state-transition tests.
2. ממש `CREATED → RUNNING → VERIFYING → terminal`.
3. חבר fake Taskcell adapter, budget, Gatekeeper ו־evidence.
4. הוסף עד שני repair attempts אחרי initial attempt.
5. ודא שאין operation לאחר cancel/exhaustion.
6. הרץ fake E2E של fail-once/pass-once.
7. כתוב handoff ו־commit: `WP-300 orchestrate bounded single-agent trials`.

### WP-310: Taskcell controlled smoke spike

**Consumes:** Gate 1, WP-120, WP-300  
**Owned paths:** `experiments/taskcell-smoke/**`, `handoffs/WP-310.json`

1. קבע smoke repository ו־acceptance hash.
2. הרץ תחילה fake adapter בלבד.
3. לאחר אישור Gate 1 בלבד, הרץ Taskcell אמיתי בסביבה המבודדת.
4. מדוד success, time, cost, intervention ו־adapter surface.
5. אל תיצור GitHub resource.
6. כתוב adoption verdict ו־handoff.
7. Commit: `WP-310 evaluate controlled Taskcell smoke path`.

### WP-320: Single-agent baseline report

**Consumes:** WP-300, WP-310  
**Owned paths:** `experiments/single-agent/**`, `handoffs/WP-320.json`

1. קבע template, image, model, budget ו־acceptance hashes.
2. הרץ לפחות שלושה trials טריים.
3. שמור product failures ככישלונות.
4. חשב accepted rate, elapsed time, cost, repair ו־intervention.
5. הפק Gate 2 report.
6. כתוב handoff ו־commit: `WP-320 establish single-agent baseline`.

---

## 9. Wave 5 — GitHub delivery

### WP-400: Idempotent GitHub adapter

**Consumes:** WP-014, WP-015  
**Owned paths:** `factory/delivery/**`, `handoffs/WP-400.json`

1. כתוב fake API tests ל־repository/create/push/PR.
2. ממש private repository בלבד.
3. ממש `main` מה־template ו־feature branch מה־candidate.
4. ממש Draft PR בלבד.
5. בדוק retries לאחר כל partial failure.
6. חסום merge, deploy, force-push ו־workflow mutation.
7. כתוב handoff ו־commit: `WP-400 add idempotent GitHub draft delivery`.

### WP-410: Delivery recovery trial

**Consumes:** Gate 2, WP-400  
**Owned paths:** `experiments/delivery/**`, `handoffs/WP-410.json`

1. הרץ fake partial-failure matrix.
2. אמת שאין duplicate repository, branch או PR.
3. לאחר אישור מפעיל, צור repository פרטי disposable אחד.
4. אמת CI ו־candidate SHA.
5. הפק Gate 3 report.
6. כתוב handoff ו־commit: `WP-410 verify recoverable GitHub delivery`.

---

## 10. Wave 6 — Multi-Agent experiment

### WP-500: Shared feature contract and invalidation

**Consumes:** Gate 3, WP-011  
**Owned paths:** `factory/strategies/shared-contract/**`, `handoffs/WP-500.json`

1. הגדר versioned HTTP/data/migration/error contract.
2. כתוב invalidation tests.
3. קשר כל artifact ל־contract version.
4. פסול artifact ישן לאחר שינוי חוזה.
5. כתוב handoff ו־commit: `WP-500 add versioned worker contract`.

### WP-510: Multi-agent strategy

**Consumes:** WP-300, WP-500  
**Owned paths:** `factory/strategies/multi-agent/**`, `handoffs/WP-510.json`

1. כתוב tests לענפי persistence ו־API נפרדים.
2. כתוב integration-session tests.
3. חסום overlapping paths ו־mixed base/contract versions.
4. ממש deterministic cherry-pick/integration result.
5. חשב את כל workers וה־integration מול תקציב משותף.
6. הרץ את אותו Gatekeeper של Single-Agent.
7. כתוב handoff ו־commit: `WP-510 add contract-frozen multi-agent strategy`.

### WP-520: Paired experiment

**Consumes:** WP-320, WP-510  
**Owned paths:** `experiments/paired/**`, `handoffs/WP-520.json`

1. קבע מראש thresholds, stopping rules ו־invalid-run policy.
2. קבע שני benchmark variants.
3. צור לוח של 10 pairs עם סדר מאוזן.
4. הרץ כל arm על repository טרי מאותו template SHA.
5. אל תשמיט product failures.
6. פרסם accepted rate, paired elapsed difference, cost, intervention ו־conflicts.
7. הפק Gate 4 Go/No-Go.
8. כתוב handoff ו־commit: `WP-520 complete paired factory experiment`.

---

## 11. פרוטוקול Integration Owner

לכל Work Package שהושלם:

1. אמת שהענף מבוסס על ה־Base SHA הנכון.
2. הרץ `git diff --name-only <base>..<result>`.
3. השווה את הרשימה ל־`Owned paths`; דחה חריגה.
4. אמת את `handoffs/<WP>.json` מול schema.
5. Cherry-pick לענף `integration/m0`.
6. הרץ את הבדיקות הממוקדות של החבילה.
7. הרץ contract compatibility tests.
8. בסוף Wave הרץ `pnpm verify:all`.
9. עדכן `integration/status.json` ב־commit נפרד.
10. פרסם Integration SHA לגל הבא.

אם cherry-pick יוצר conflict, Integration Owner אינו פותר ידנית בתוך קוד של סוכן. המשימה חוזרת לבעליה עם Base SHA החדש ועם רשימת הקונפליקטים.

## 12. הקצאה מומלצת לארבעה סוכנים

| Agent | Wave 1 | Wave 2 | Wave 3 | Wave 4+ |
|---|---|---|---|---|
| A — Integration Owner | WP-000 + Gate 0 | Integration | Integration + Gate 1 | כל ה־Gates |
| B — Contracts/Benchmark | WP-010, WP-011 | WP-100 | WP-200 | WP-320, WP-520 |
| C — Security/Runtime | WP-012, WP-013 | WP-140 | WP-210, WP-230 | WP-300, WP-510 |
| D — Evidence/Adapters | WP-014, WP-015 | WP-120, WP-130 | WP-220 | WP-310, WP-400, WP-410, WP-500 |

בכל גל יש לבצע הקצאה מחדש רק לאחר שה־Integration SHA פורסם. אין להחזיק משימה מהגל הבא בזמן שהגל הנוכחי עדיין עובר אינטגרציה.

## 13. תנאי עצירה

- Agent אמיתי אסור לפני Gate 1.
- GitHub mutation אסורה לפני Gate 2 ואישור מפעיל.
- Multi-Agent אסור לפני Gate 3.
- כל P0 isolation failure עוצר את הגל.
- חריגה מתקציב עוצרת paid operations מיד.
- שינוי בחוזה קפוא מבטל artifacts תלויים עד revalidation.
- בדיקה חסרה או skipped היא כישלון, לא pass.

