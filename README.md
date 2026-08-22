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
*   ✅ **Native Audio (GenerateContent / non-Live):** Gemini 2.5 TTS preview models can return audio via `generate_content` when using `response_modalities=["AUDIO"]`.
*   ❌ **Still blocked:** requesting audio via `response_mime_type="audio/wav"` (GenerateContent only allows text/json/xml/yaml/enum mime types).

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
5.  **Try Native Audio (Gemini Live):**
    ```bash
    # Run with default settings (saves to file)
    uv run experiments/gemini_live_audio.py

    # Run with interactive playback (hear it while it saves)
    uv run experiments/gemini_live_audio.py -i

    # Speak only (hear it, do not save to file)
    uv run experiments/gemini_live_audio.py -s

    # Speak with a specific voice (e.g., Fenrir)
    uv run experiments/gemini_live_audio.py -s -v Fenrir

    # Speak specific text
    uv run experiments/gemini_live_audio.py -s -t "Hello, I am Gemini."

    # Use the older Gemini 2.0 Flash Exp model
    uv run experiments/gemini_live_audio.py -i -o
    ```

## 🗣️ CLI Shortcuts
For convenience, this project defines several shortcuts in `pyproject.toml` to quickly use the Text-to-Speech capabilities. You can run these using `uv run`.

### Direct speech

#### `speaks` (Speak text or a file)
Speaks text or a text file with Live streaming playback by default. Use `--voice` to select a voice, `--wav` to write a WAV file, and `--list-voices` to inspect the supported voice catalog without an API request.
```bash
uv run speaks "Hello, I can speak this text immediately."
uv run speaks --voice Fenrir "Hello with a selected voice."
uv run speaks --wav out.wav --voice Kore path/to/my_text.txt
uv run speaks --list-voices
```

#### `speakf` (Speak File)
Reads and speaks the contents of a text file (streaming playback).
```bash
uv run speakf path/to/my_text.txt
```

#### `speakme` (Speak Default File)
Speaks the contents of the `speak_me.txt` file located in the current directory.
```bash
uv run speakme
```

### GenerateContent (non-Live) -> WAV

#### `speakwav` (Text -> WAV)
Synthesizes a WAV file from text using the Gemini 2.5 TTS preview model.
```bash
uv run speakwav -t "Hello from GenerateContent TTS" -o out.wav
```

#### `speakwavf` (File -> WAV)
Synthesizes a WAV file from a text file.
```bash
uv run speakwavf -f path/to/my_text.txt -o out.wav
```

#### `speakwav3` (Prompt -> Gemini 3 text -> WAV)
Uses Gemini 3 to generate the transcript text, then synthesizes a WAV using Gemini 2.5 TTS.
```bash
uv run speakwav3 -p "Say hello in one sentence" -o out.wav
```

---
*This is an experimental repository. If you've stumbled upon this, feel free to explore the `experiments/` and `docs/` folders to see our findings and code samples.*
