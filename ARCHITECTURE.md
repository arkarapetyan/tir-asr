# ARCHITECTURE.md

**Project:** tir-asr · **Version:** 0.0 (template) · **Date:** 2026-10-23
**Status:** TEMPLATE. Chat C2 writes the first real version (RULES.md R13).

---

## 1. Overview

(C2) One paragraph and one diagram: the path from the audio devices to the terminal lines.

## 2. Modules and contracts

Each module has one contract. Each contract gives the inputs, the outputs, the errors, and the limits.

| Module | Input | Output | Errors (fail loudly, R10) | Limits |
|---|---|---|---|---|
| `audio` | (C2, C4) | | | |
| `segment` | (C2) | | | |
| `asr` | (C2) | | | |
| `mt` | (C2) | | | |
| `speakers` | (C5) | | | |
| `output` | (C2) | | | |

## 3. Data types

(C2) The data types that go between the modules, with their fields and units.

## 4. Data flow, threads, and queues

(C2) Which thread does what. Which queues connect the threads. What happens when a queue is full.

## 5. Configuration

(C2) The command-line flags and the configuration values.

## 6. Parameters

Only Aren adds a parameter (RULES.md R10). The startup log shows each parameter.

| Name | Value | Unit | Reason | Approved by Aren (date) |
|---|---|---|---|---|
| | | | | |

## 7. Error behaviour

(C2) For each error: the module, the message, and what the program does (stop or show).

## 8. Change log

| Version | Date | Change |
|---|---|---|
| 0.0 | 2026-10-23 | Template. |
