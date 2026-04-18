# Sotti — Model & Prompt Reference

This document describes every model call made inside `src/agent_manager.py`.
It covers the role of each model, the exact system/user prompts they receive,
and every generation parameter that is configured.

---

## Models Overview

| Role | Config Key | Current Default |
|---|---|---|
| Orchestrator (OCR) | `ORCHESTRATOR_MODEL` | `gemini-3.1-flash-lite-preview` |
| Sub-Agent (Codegen) | `SUB_AGENT_MODEL` | `gemma-4-31b-it` |
| Primary API key | `GEMINI_API_KEY` | *(set in `.env`)* |
| Fallback API key | `GEMINI_API_KEY_FALLBACK` | *(optional, set in `.env`)* |

All values are read from the `.env` file via `src/config.py`.
Changing models only requires an update to `.env` — no code change needed.

---

## 1. Orchestrator Model (OCR / Question Extraction)

### Role
Reads one or more screenshot images of a coding exam portal and extracts a
structured `QuestionPack` JSON object containing the problem title, statement,
test cases, and stub code.

### API Call Location
`src/agent_manager.py` → `generate_and_verify_solution()` — first call.

### Generation Parameters

| Parameter | Value |
|---|---|
| `model` | `settings.orchestrator_model` (default: `gemini-2.5-flash-preview-04-17`) |
| `temperature` | `0.1` |
| `response_mime_type` | `application/json` |

### System Prompt

```
You are an advanced data extraction agent operating in a two-part workflow.
You will be provided with screenshots of a coding examination portal.
The screen is split into two panes: the Question (Left) and the Stub Code (Right).
Your task is to extract information from both panes and output a STRICT, valid JSON object.

### Part 1: Question Extraction (Intelligent Mode)
Read the left pane. Extract the title, the core problem statement, and all visible
test cases (Inputs and Expected Outputs).

### Part 2: Stub Code Extraction (Strict OCR Mode)
Read the right pane. You are now functioning as a dumb, literal OCR engine.
CRITICAL RULES FOR STUB CODE:
- Transcribe the code EXACTLY character-for-character as it appears in the image.
- DO NOT fix missing semicolons, syntax errors, or typos.
- DO NOT format or indent the code differently than the image.
- DO NOT remove or answer the placeholder comments
  (e.g., "// Write your solution here" or "// Define constructor here").
- DO NOT complete the code. Only output what is visible on the screen.

### EXAMPLE JSON OUTPUT FORMAT:
{
  "title": "Inheritance - Doctor and Surgeon",
  "question": "A hospital management system maintains records of doctors...",
  "test_cases": [{"input": "...", "expected_output": "..."}],
  "stub_code": "class Doctor {\n    private String name;\n// Define constructor here\n}\n\nclass Surgeon extends Doctor {\n// Define constructor here\n}"
}
```

### User Message (injected at call time)
```
Extract the question pack from the screenshot(s) above.
Return ONLY the JSON object — no markdown fences, no extra text.
```
User message is appended after all screenshot images in the `contents` list.

### Expected Output (JSON)

```json
{
  "title": "",
  "question": "",
  "test_cases": [{ "input": "", "expected_output": "" }],
  "stub_code": ""
}
```

### Fallback Behaviour
If the orchestrator call fails (any exception):
1. Retry the same prompt using the **Sub-Agent model** (`settings.sub_agent_model`).
2. If the failure is HTTP `429` or `503`, the call is automatically re-routed through
   the **fallback API key** (`settings.gemini_api_key_fallback`) before raising.

---

## 2. Sub-Agent Model (Code Generation)

### Role
Receives the structured `QuestionPack` JSON and produces a complete, compilable
Java solution. The output has two parts:
- `block` — minimal code to type into the exam portal's placeholder.
- `full_file` — a complete Java file used for local verification.

### API Call Location
`src/agent_manager.py` → `generate_and_verify_solution()` — retry loop
(up to `_MAX_RETRIES = 3` attempts).

### Generation Parameters

| Parameter | Value |
|---|---|
| `model` | `settings.sub_agent_model` (default: `gemma-4-31b-it`) |
| `temperature` | `0.2` |
| `response_mime_type` | `application/json` |

### System Prompt

```
You are a Java expert. You will be given a coding question pack (JSON) that contains
the problem title, problem statement, test cases, and stub code from an exam portal.

Your task is to produce a complete, correct Java solution.

Output STRICT JSON with EXACTLY two keys:
  "block"     — ONLY the minimal code required to be typed into the portal's
placeholder (no surrounding class/method shell unless the placeholder is a whole class).
  "full_file" — The complete, compilable Java file including all necessary imports
and the block injected into the stub code, so it can be compiled and run locally
with `java Solution.java`. The class must be named Solution.

Rules:
- Return ONLY the JSON object. No markdown fences. No extra text.
- The full_file MUST compile cleanly with standard javac / java (Java 11+).
- Use a public class named Solution as the top-level class.
```

### User Message — Attempt 1
```
Here is the question pack (JSON):
<question_pack JSON here>

Solve it. Return ONLY the strict JSON with 'block' and 'full_file' keys.
```

### User Message — Retry Attempts (2 and 3)
Sent when local Java verification fails. The previous model response and this
correction prompt are appended to a running `history` list so the model can
see its own error.

```
Your previous solution failed to compile/run.
Here is the compiler error:

<stderr from local java execution>

Fix ONLY the error. Return ONLY the strict JSON with 'block' and 'full_file' keys.
```

### Expected Output (JSON)

```json
{
  "block": "// minimal code to type into portal",
  "full_file": "public class Solution { ... }"
}
```

### Retry Logic

| Step | Action |
|---|---|
| Max attempts | `3` (`_MAX_RETRIES = 3`) |
| On JSON parse error | Append raw response + correction to history, continue |
| On verification failure | Append error output + correction to history, continue |
| On all attempts failing | Return best-effort `block` with a `WARNING:` hint |
| On success | Save `block` + `stub_code` to `APP_STATE` and `./data/state.json` |

### Conversation History
The sub-agent call maintains a multi-turn `history: list[types.Content]` across
retry attempts. Each round appends:
- `role: "model"` — the raw JSON response from the previous attempt.
- `role: "user"` — the compiler error message as a correction prompt.

This simulates a multi-turn conversation so the model can learn from its own mistakes.

---

## 3. Rate Limit & Key Fallback

If any API call (orchestrator or sub-agent) receives an HTTP `429` or `503` error,
`_generate_with_fallback()` automatically:

1. Logs a warning.
2. Initialises a second `genai.Client` using `settings.gemini_api_key_fallback`.
3. Retries the exact same call with the fallback client.
4. If no fallback key is configured, logs and re-raises the original error.

Configure in `.env`:
```env
GEMINI_API_KEY=your_primary_key_here
GEMINI_API_KEY_FALLBACK=your_secondary_key_here
```

---

## 4. Output Routing

After verification:

| Destination | Content |
|---|---|
| `APP_STATE["current"]` | Latest verified `block` string (in-memory) |
| `./data/state.json` | `current` + full `solved_questions` map (persisted) |
| WebSocket broadcast (`type: "solution"`) | `block` + `hint` string to frontend |
| WebSocket broadcast (`type: "status"`) | Live status string to UI ticker |

The `hint` string displayed on the UI is built by `_build_hint()`:
```
✓ Verified locally | <title> | <N> test cases
```
Or on failure:
```
WARNING: Failed local verification — <first 200 chars of stderr>
```
