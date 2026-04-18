# Product Requirements Document (PRD)

## Product Name

**Sotti** — screenshot-based coding assistant for extracting problems and generating minimal Java snippets.

## Summary

Lightweight web app + local daemon that turns screenshot batches into structured problems and outputs short, typeable code blocks. Optimized for speed, mobile viewing, and failure resilience.

## Problem

Users juggle multi-page screenshots (question, tests, stub). Need fast way to:

* bundle screenshots
* extract required code block
* generate minimal snippet
* iterate with debug feedback
* survive model failures

## Goals

* Convert screenshots → Question Pack
* Extract title, problem, tests, stub
* Output only required code block (UI)
* Verify Java locally using full-file execution
* Streamlined single-workspace UI
* Reliable retry + fallback

## Non-Goals

* No exam/portal automation
* No browser control/evasion
* Java-only focus (v1)

## Users

* Students solving coding problems
* Devs debugging snippets

## Flow

1. Capture screenshots
2. Watcher groups into pack
3. Agent extracts context
4. Sub-agent generates full-file code internally
5. Local verifier runs `java`
6. Extract only required block for UI
7. Retry if needed (max cap)
8. Show/store result

## Architecture

### Local Watcher

* Monitor folder
* Batch images
* Settle delay
* Queue packs

### Agent Manager

* Parse images
* Build Question Pack
* Control retries + fallback
* Summarize failures

### Sub-Agent

* Generate **full valid Java file** for execution
* Also mark required editable blocks
* Follow strict format for block extraction
* Iterate on verifier feedback

### Local Verifier

* Write full file to tmp
* Run `java`
* Capture errors
* Return concise feedback

### Web UI

* Show extracted block only
* Real-time status ticker

## Functional Requirements

### Intake

* Watch folder
* Batch images
* Delay before send

### Question Pack

* title, problem, tests
* input/output
* stub code

### Output (Dual Mode)

* Internal: full Java file (for execution)
* External/UI: block-level code only
* Include optional hint

### Verification

* Run full file locally
* Feed errors back

### Retry

* Max 3 attempts
* Reset agent on failure

### Fallback

* Use backup model on failure
* Never hard stop

## UI

### Layout

* Edge-to-edge
* Large monospace
* High contrast

### Layout

* Single-workspace focus
* Code block center-stage
* PIP-safe bounding box (top-left)
* Status ticker (bottom-left)

### Navigation (V2)

* Gestures/Swipe for history

## Tech

### Stack (Configurable)

* Backend: Python 3.11+ (FastAPI + uv)
* File watching: `watchdog`
* Frontend: Vanilla HTML/CSS/JS (single file)
* Java runner: subprocess calling system `java`
* Storage: In-memory state (Phase 6)
* IPC: REST + WebSockets

### Model Layer (Google AI Studio)

* Powered by Google Gemini SDK
* User can configure:

  * Orchestrator model (e.g., Gemini 2.5 Flash)
  * Code generation model (e.g., Gemma 2)
  * Error fallback / Sub-agent model
* All model names must be env/config driven

### Backend

* Watcher + pack builder
* Agent routing
* Java runner (full file)
* Block extractor

### Data

**Pack**

```json
{ "title":"","question":"","tests":[],"stub_code":"" }
```

**Answer**

```json
{
  "short_name":"",
  "blocks":[{"name":"","code":""}],
  "full_file":"",
  "hint":""
}
```

## Prompt Strategy (Critical)

### Split-Brain Approach

Two modes in one prompt:

* Intelligent mode → question parsing
* Strict OCR mode → stub extraction

### OCR Isolation

* Wrap stub in `<strict_ocr_zone>`
* Treat as raw text, not code

### Hard Constraints

* No fixing syntax
* No adding/removing chars
* No completing code
* Preserve placeholders exactly

### Required JSON Output

```json
{
  "title": "",
  "question": "",
  "test_cases": [{"input":"","expected_output":""}],
  "stub_code": ""
}
```

### Role Enforcement

* Model must switch behavior between sections
* OCR mode = literal transcription only

## Models

* Primary: image + orchestration
* Secondary: code generation (full file)
* Fallback: reliability

## Metrics

* Time to answer
* First-pass success rate
* Retry count

## Risks

* Bad OCR
* Wrong batching
* Hallucinated code
* Block extraction mismatch
* Weak verification loops

## MVP

* watcher
* pack builder
* agent pipeline
* full-file Java verify
* block extraction
* UI (single-workspace + ticker)

## Phase 2

* gestures
* better parsing
* improved debugging

## Open Questions

* settle time?
* min images?
* verify every attempt?
* best way to map blocks reliably?

## Conclusion

Feasible. Hard parts: image parsing, batching, full-file correctness + precise block extraction. Start small.
