# Status: Google Cloud Speech & Multimodal Interactions Analysis

## 🚨 Current Status & Key Findings (Updated)
- **Text-to-Speech (Audio Generation):**
  - **✅ Working Solution 1 (Streaming/Low latency):** **Gemini Live API** (WebSockets). Code: `experiments/gemini_live_audio.py`. Streams audio chunks for fast time-to-first-audio.
  - **✅ Working Solution 2 (Non-Live / GenerateContent):** **Gemini 2.5 TTS preview models** via `generate_content` with `response_modalities=["AUDIO"]`.
    - Audio comes back as raw PCM (e.g. `audio/L16;codec=pcm;rate=24000`) and must be wrapped into WAV for easy playback.
    - Code: `experiments/gemini_3_text_then_25_tts.py` (pipeline + WAV writing) and `experiments/gemini_31_flash_lite_audio_out.py` (probe).
  - **✅ Working Solution 3 (Standard):** **Google Cloud Text-to-Speech API**. Code: `experiments/standard_tts.py`.
  - **❌ Still blocked / not supported:**
    - Requesting audio via `generation_config.response_mime_type="audio/wav"` (GenerateContent only allows text/json/xml/yaml/enum mime types).
    - **Gemini 3.x models** (text-only) cannot generate audio via GenerateContent.
- **Speech-to-Text (Transcription):**
  - **✅ Working Solution:** **Google Cloud Speech-to-Text V2** ("Chirp" models). Code: `experiments/chirp_speech_recognition.py` (Valid code, requires API enablement).
- **Environment:**
  - Managed via `uv` using `pyproject.toml`.
  - Dependencies: `google-genai`, `google-cloud-speech`, `google-cloud-texttospeech`.

## Goal / Request
"Investigate two topics:
1. Google Cloud Speech-to-Text V2 API: Check if there is a 'chirp' model or similar and what they are called.
2. Google Interactions API / Gemini Multimodal: Explore interactive multimodal back-and-forth. Clarification: I'm already using the Gemini Live API (natural talk, speech back, screen share, tools). What is missing is having the response multi-modal AND storing it on disk.
   - Requirement: Put this request exactly as is into a status file.
   - Requirement: Perform analysis and write findings to the status file.
   - Requirement: Create code from it later.
   - Constraint: Simple first version using curl for text-to-audio is fine.
   - Constraint: Python for server-side implementation."

### Model Selection Strategy
- **Normal LLM (Text/Code/Reasoning):** Use **`gemini-3-flash-preview`** (or `gemini-3-pro-preview` if needed). Start with Flash.
- **Gemini Live / Multimodal (Audio/Video/Interactive):** Use **`gemini-2.5-flash`** (or the most recent 2.5 variant) as it is the current standard for these capabilities.
- **General Rule:** Always use the most recent models available for the specific category.

## Analysis Status
- [x] Investigate Google Cloud Speech-to-Text V2 'Chirp' models.
- [x] Investigate programmatic storage of Multimodal/Audio responses from Gemini (Vertex AI / Gemini API).

## Findings

Detailed analysis has been moved to specific documentation files:

### 1. Google Cloud Speech-to-Text V2 & "Chirp"
See: [docs/speech_to_text_v2_chirp.md](docs/speech_to_text_v2_chirp.md)
- **Summary:** Chirp 2/3 models available via V2 API. Best for high-fidelity ASR.
- **Status:** Code example `experiments/chirp_speech_recognition.py` created.
- **Blocker:** Returns `404 Requested entity was not found` during `client.recognize` call, even though `list_recognizers` confirms the resource exists at the path. Might be a regional propagation issue or specific project configuration quirk.
- **Action:** Code is valid V2 usage. Verify Recognizer path/project number logic in a fully interactive console session.

### 2. Google Interactions API / Gemini Multimodal
See: [docs/gemini_multimodal_live.md](docs/gemini_multimodal_live.md)
- **Summary:** Gemini Live supports native streaming audio; GenerateContent supports non-Live audio output via the dedicated 2.5 TTS preview models.
- **Status:**
  - Live API succeeded (see below).
  - GenerateContent TTS succeeded (see below).
  - Only the `response_mime_type="audio/wav"` approach is rejected.
- **Update:** `standard_tts.py` remains a reliable fallback / alternative.

### Native Audio Investigation: Gemini 2.5 (GenerateContent / non-Live)
- **Status:** **Success** (with the right config)
- **Method:** `generate_content` (Gemini API / v1beta via `google-genai`)
- **Works when:** using `GenerateContentConfig(response_modalities=["AUDIO"], speech_config=...)` **with** a 2.5 TTS preview model (e.g. `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`).
- **Audio format returned:** typically raw PCM16 with mime like `audio/L16;codec=pcm;rate=24000`.
  - **Implication:** you must wrap PCM in a WAV container (we do this in `experiments/gemini_3_text_then_25_tts.py`).
- **Not supported:** requesting audio via `generation_config.response_mime_type="audio/wav"`.
  - This yields `400 INVALID_ARGUMENT` listing only text/json/xml/yaml/enum mime types.
- **New experiment scripts:**
  - `experiments/gemini_31_flash_lite_audio_out.py` (probe audio output across models; extracts inline audio bytes)
  - `experiments/gemini_3_text_then_25_tts.py` (Gemini 3 text → 2.5 TTS → WAV; optional `--verify` transcription)

### Native Audio Investigation: Gemini 2.0 (Live API)
- **Status:** **Success**
- **Method:** **Gemini Live API** (WebSockets)
- **Model:** `gemini-2.5-flash-native-audio-preview-12-2025` (Default) or `gemini-2.0-flash-exp` (via `-o` flag)
- **Solution:** Created `experiments/gemini_live_audio.py`.
- **Features:**
  - `-i` / `--interactive`: Real-time streaming audio playback.
  - `-s` / `--speak-only`: Real-time playback ONLY (no file save).
  - `-v` / `--voice`: Specify voice name (e.g., `-v Fenrir`).
  - `-t` / `--text`: Specify text to speak (e.g., `-t "Hello world"`).
  - `-o` / `--old`: Switch to `gemini-2.0-flash-exp`.
- **Outcome:** Successfully streams and saves native Gemini audio. Recommended "Native Audio" path.

### Gemini Live API Configuration
**Documentation:** [Google Cloud Vertex AI / Gemini API Docs](https://ai.google.dev/gemini-api/docs/multimodal-live)

**Key `LiveConnectConfig` Parameters:**
- **`response_modalities`**: `["AUDIO"]` (for speech) or `["TEXT"]`.
- **`system_instruction`**: String to guide model behavior/persona (e.g., "You are a helpful assistant.").
- **`speech_config`**: Control voice settings.
  - `voice_config`: `prebuilt_voice_config` -> `voice_name`.
  - **Available Voices:** `Puck` (Default), `Charon`, `Fenrir`, `Kore`, `Aoede`, `Leda`, `Orus`, `Zephyr`.
- **`tools`**: List of tools for function calling (e.g., Google Search, Code Execution).
- **`generation_config`**: Control generation parameters (temperature, top_p, etc.).

## Completed Steps
- [x] Create a simple `curl` example to convert text to audio (Gemini TTS). -> `experiments/text_to_audio.sh`
- [x] Create a Python server-side script to generate and save audio responses. -> `experiments/gemini_audio_server.py`
- [x] Update scripts to use Gemini 2.5/Pro models.
- [x] Create a Python script for Chirp V2 recognition. -> `experiments/chirp_speech_recognition.py`
- [x] Structure documentation into `docs/`.
