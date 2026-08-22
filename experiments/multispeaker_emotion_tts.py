"""Generate the official tired-versus-excited two-speaker TTS example as a WAV file.

Run:
    uv run experiments/multispeaker_emotion_tts.py

Requires GEMINI_API_KEY or GOOGLE_API_KEY. The result is raw PCM16 audio wrapped in
an ordinary 24 kHz mono WAV container, ready to audition in any audio player.

Source: https://ai.google.dev/gemini-api/docs/speech-generation#voice-options
"""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
from typing import Any
import wave

from google import genai


MODEL = "gemini-3.1-flash-tts-preview"
DEFAULT_OUTPUT = "multispeaker_emotion_tts.wav"
PROMPT = """Make Speaker1 sound tired and bored, and Speaker2 sound excited and happy:

Speaker1: So... what's on the agenda today?
Speaker2: You're never going to guess!
"""
SPEECH_CONFIG = {
    "speech_config": [
        {"speaker": "Speaker1", "voice": "Enceladus"},
        {"speaker": "Speaker2", "voice": "Puck"},
    ]
}


def _api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Error: GEMINI_API_KEY or GOOGLE_API_KEY must be set.")
    return api_key


def _write_pcm16_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(pcm)


def synthesize_to_wav(*, client: Any, output_wav: Path) -> None:
    """Request multi-speaker TTS and write its base64 PCM16 response as WAV."""
    interaction = client.interactions.create(
        model=MODEL,
        input=PROMPT,
        response_format={"type": "audio"},
        generation_config=SPEECH_CONFIG,
    )
    encoded_audio = interaction.output_audio.data
    if not isinstance(encoded_audio, str) or not encoded_audio:
        raise RuntimeError("Gemini returned no base64 audio data.")

    pcm = base64.b64decode(encoded_audio, validate=True)
    _write_pcm16_wav(output_wav, pcm)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the official tired Speaker1 / excited Speaker2 Gemini TTS example."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"WAV output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    client = genai.Client(api_key=_api_key())
    synthesize_to_wav(client=client, output_wav=args.output)
    print(f"Wrote WAV: {args.output}")
    print("Speaker1: Enceladus (breathy); Speaker2: Puck (upbeat).")


if __name__ == "__main__":
    main()
