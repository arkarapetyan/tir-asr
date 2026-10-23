# TESTS.md

**Project:** tir-asr · **Date:** 2026-10-23
**Rules:** RULES.md R5 (test-driven development) and D-006 (test runs).

Each test comes from a requirement in the brief (F, K, D in `PLAN.md` §1) or from a module contract in `ARCHITECTURE.md`.
Aren reviews each test before Claude writes it.

Test levels:

- **unit:** no model and no audio device. CI runs them.
- **model:** loads a real model. Aren runs them on the laptop.
- **sim:** the program captures from virtual audio devices. Aren runs them on the laptop.
- **live:** real devices and real people. Aren does the checklist in §4.

Status values: DESIGNED, APPROVED, WRITTEN (it fails), PASSES.

---

## 1. How to run the tests (D-006)

Claude gives the exact commands for each run. Each run writes its result into `test-results/`. Claude reads that file.
`test-results/` is in `.gitignore`.

## 2. Test list

### 2.1 Setup (C0)

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-SETUP-01 | D-007: the package installs with uv and imports. | `uv sync --locked`, then `import tir_asr` | The import works. The installed version is `0.1.0`. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |

Note: T-SETUP-01 checks the setup only, not a module. Claude wrote it together with the setup, before Aren's review. Aren chose not to review the setup tests ("I wont check the setup tests", 2026-10-23).

## 3. QA questions

We add a question here when we find it during the work (tip T4).

| ID | Question | Source | Answer / test ID |
|---|---|---|---|
| | | | |

## 4. Live checklist (manual)

Only the checks that a sim test cannot do. (C7)

| ID | Check | Expected result | Result |
|---|---|---|---|
| | | | |
