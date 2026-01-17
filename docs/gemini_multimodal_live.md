# Gemini Multimodal & Live API Analysis

## Overview
This approach focuses on interactive, multimodal back-and-forth interactions using the Gemini models.

## Models
- **Gemini 2.5 Flash (`gemini-2.5-flash`)**: The primary model for this category. It offers native multimodal input (audio, video, text) and output (text, audio).
- **Gemini Live API**: A specialized real-time streaming interface (WebSocket-based) for low-latency voice interactions.

## Capabilities

### 1. Native Audio Generation (TTS)
You can request audio output directly from the model.
- **Method:** `generate_content` (REST/RPC)
- **Config:** `response_mime_type="audio/wav"`
- **Storage:** The audio binary is returned in the response and can be saved to disk.
- **Status:** **Verified** (See `experiments/gemini_audio_server.py`)

### 2. Real-time Interactions (Live API)
- **Protocol:** WebSocket
- **Storage:** The API streams raw PCM audio. It does *not* save to disk automatically.
- **Implementation:** The client application acts as the "recorder". It must buffer the received audio chunks and write them to a file (e.g., using `wave` in Python) or upload them to object storage (GCS).

## Current Experiments
- `experiments/text_to_audio.sh`: CURL-based test for `gemini-2.5-flash` audio generation.
- `experiments/gemini_audio_server.py`: Python script to generate and save audio.

## Architecture Idea
For the "Speak to Me" project:
1.  **Input:** User speaks.
2.  **Processing:** 
    *   *Option A (Live):* Audio streamed to Gemini Live. Response streamed back. Client saves both input and output streams to disk for history.
    *   *Option B (Turn-based):* Audio recorded -> Chirp (Transcribe) -> Gemini 3 Flash (Reason) -> Gemini 2.5 Flash (TTS).
    *   *Option C (Native Multimodal):* Audio recorded -> Gemini 2.5 Flash (Audio-in -> Audio-out).
