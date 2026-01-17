# Speak to Me: Gemini & Google Cloud Speech Experiments

Welcome to **Speak to Me**, an experimental playground for building and testing advanced voice and multimodal interactions using Google's latest AI technologies.

## 🎯 Goal
The objective of this project is to explore the frontier of interactive, stateful, and multimodal "back-and-forth" communication. We aim to move beyond simple text interfaces toward natural speech interactions where the AI can hear, reason, and speak back—while ensuring that these multimodal exchanges are captured and stored programmatically for persistent history and analysis.

## 🧪 Experiments & Capabilities
This repository contains a series of focused experiments investigating different components of the multimodal stack:

*   **Speech-to-Text V2 (Chirp):** High-precision transcription using Google's Universal Speech Model (USM). See `experiments/chirp_speech_recognition.py`.
*   **Gemini Live API:** Real-time, low-latency WebSocket interactions that allow for streaming audio back-and-forth. **Verified working** for generating native Gemini audio. See `experiments/gemini_live_audio.py`.
*   **Standard Text-to-Speech:** Utilizing Google Cloud TTS (Standard/Neural2) as a high-quality, reliable fallback for speech generation. See `experiments/standard_tts.py`.
*   **Audio Capture:** Implementing logic to buffer and save raw audio streams (e.g., PCM from Live API) into standard formats like WAV for persistent storage.

## 🏗️ Technical Stack
*   **Python 3.13** (managed by [uv](https://github.com/astral-sh/uv))
*   **Google Gen AI SDK** (`google-genai`)
*   **Google Cloud Client Libraries** (`google-cloud-speech`, `google-cloud-texttospeech`)

## 🚦 Current Status
We are currently in the active investigation phase:
*   ✅ **Transcription:** STT V2 Chirp models are integrated and functional.
*   ✅ **Native Audio (Live):** The Gemini Live API (WebSockets) is working and successfully generates native audio responses from text prompts.
*   ✅ **Reliable Speech:** Standard Google Cloud TTS is used for consistent audio generation.
*   ❌ **Native Audio (REST):** Direct `audio/wav` generation via `generateContent` (REST API) is currently **unavailable/blocked** on public preview endpoints.

## 🚀 Getting Started
1.  **Clone the repository.**
2.  **Install dependencies:**
    ```bash
    uv sync
    ```
3.  **Set up environment variables:**
    *   `GEMINI_API_KEY`: Your Google AI Studio API key.
    *   `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google Cloud Service Account JSON for Speech/TTS APIs.
4.  **Run an experiment:**
    ```bash
    uv run experiments/standard_tts.py
    ```

---
*This is an experimental repository. If you've stumbled upon this, feel free to explore the `experiments/` and `docs/` folders to see our findings and code samples.*
