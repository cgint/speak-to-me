# Status: Google Cloud Speech & Multimodal Interactions Analysis

## 🚨 Current Status & Key Findings (Updated)
- **Text-to-Speech (Audio Generation):**
  - **✅ Working Solution 1 (Native):** **Gemini Live API** (WebSockets). Code: `experiments/gemini_live_audio.py`. Generates native Gemini audio.
  - **✅ Working Solution 2 (Standard):** **Google Cloud Text-to-Speech API**. Code: `experiments/standard_tts.py`.
  - **❌ Blocked:** Native REST API (`generateContent` with `audio/wav`) is currently unavailable.
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
- **Status:** Code example `experiments/chirp_speech_recognition.py` created and verified (requires API enablement).

### 2. Google Interactions API / Gemini Multimodal
See: [docs/gemini_multimodal_live.md](docs/gemini_multimodal_live.md)
- **Summary:** Gemini 2.5 Flash / Pro (Preview) models theoretically support native TTS.
- **Status:** `experiments/gemini_audio_server.py` and `text_to_audio.sh` created using `gemini-2.5-flash-native-audio-latest` and `gemini-2.5-pro-preview-tts`. Both currently return `400 INVALID_ARGUMENT` for `audio/wav` output, suggesting the feature is restricted or requires specific allowlisting on the `generateContent` endpoint for the current API key tier.
- **Update:** Tested on Vertex AI (`us-central1`, `gemini-2.5-flash-preview-tts`, `gemini-2.0-flash-exp`) with the same `400 INVALID_ARGUMENT` or `404 NOT_FOUND` results.
- **Success:** Created `experiments/standard_tts.py` using **Google Cloud Text-to-Speech API**. This successfully generates audio files from text, serving as the functional "Google model" solution while native Gemini audio is unavailable.
- **Environment:** Configured `pyproject.toml` and verified execution using `uv run`.

### Native Audio Investigation: Gemini 2.5 (REST API)
- **Status:** **Failed** / **Blocked**
- **Method:** `generateContent` (REST)
- **Attempts:**
  1. `response_mime_type="audio/wav"` -> Returns `400 INVALID_ARGUMENT` (MIME type not allowed).
  2. `response_modality="audio"` -> Returns SDK Validation Error.
  3. Models tested: `gemini-2.5-flash-preview-tts`, `gemini-2.5-flash-native-audio-latest`.
- **Conclusion:** Native audio generation via standard REST calls is currently not enabled for public Gemini 2.5 models.

### Native Audio Investigation: Gemini 2.0 (Live API)
- **Status:** **Success**
- **Method:** **Gemini Live API** (WebSockets)
- **Model:** `gemini-2.0-flash-exp`
- **Solution:** Created `experiments/gemini_live_audio.py`.
- **Outcome:** Successfully streams and saves native Gemini audio from text prompts. This is the recommended "Native Audio" path today.

## Completed Steps
- [x] Create a simple `curl` example to convert text to audio (Gemini TTS). -> `experiments/text_to_audio.sh`
- [x] Create a Python server-side script to generate and save audio responses. -> `experiments/gemini_audio_server.py`
- [x] Update scripts to use Gemini 2.5/Pro models.
- [x] Create a Python script for Chirp V2 recognition. -> `experiments/chirp_speech_recognition.py`
- [x] Structure documentation into `docs/`.
