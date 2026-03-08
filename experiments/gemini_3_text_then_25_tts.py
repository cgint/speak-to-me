"""Gemini 3 (text) -> Gemini 2.5 TTS (GenerateContent AUDIO) -> WAV (+ optional self-verification).

Why this exists
- Gemini 3.x models on the public Gemini API currently support **text output only**.
- Gemini 2.5 TTS preview models support **audio output** via `response_modalities=["AUDIO"]`.

So if you want a "Gemini 3 brain" but still want GenerateContent-based TTS,
this script does a 2-step pipeline:
  1) Use a Gemini 3 model to produce the text to speak.
  2) Use a Gemini 2.5 *-preview-tts model to synthesize audio from that text.

Output details
- The TTS model returns raw PCM16 (commonly mime_type
  `audio/L16;codec=pcm;rate=24000`). This script wraps it in a WAV container.

Verification (optional)
- As a sanity check, the script can transcribe the resulting WAV using a Gemini 3.1 model
  that supports audio *input* (text output), and print the transcript.

Examples
  uv run experiments/gemini_3_text_then_25_tts.py \
    -p "In one sentence, tell me a fun fact about octopuses." \
    -o out.wav \
    --verify

Requires:
- GEMINI_API_KEY (or GOOGLE_API_KEY) in env.
"""

from __future__ import annotations

import argparse
import os
import re
import wave
from dataclasses import dataclass
from typing import Iterable

from google import genai
from google.genai import types


DEFAULT_TEXT_MODEL = "gemini-3-flash-preview"
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VERIFY_MODEL = "gemini-3.1-flash-lite-preview"
DEFAULT_VOICE = "Puck"
DEFAULT_OUT = "gemini_3_text_then_25_tts.wav"


def _get_api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _iter_parts(response: object) -> Iterable[types.Part]:
    if not hasattr(response, "candidates"):
        return []

    parts: list[types.Part] = []
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            parts.append(part)
    return parts


def _extract_text(response: object) -> str:
    # The SDK often provides response.text
    t = getattr(response, "text", None)
    if isinstance(t, str) and t.strip():
        return t

    # Fall back to concatenating text parts.
    chunks: list[str] = []
    for part in _iter_parts(response):
        txt = getattr(part, "text", None)
        if isinstance(txt, str) and txt:
            chunks.append(txt)

    text = "".join(chunks).strip()
    if not text:
        raise RuntimeError("No text found in response")
    return text


def _extract_audio_bytes(response: object) -> tuple[bytes | None, str | None]:
    # Some shapes expose response.audio.data
    audio_obj = getattr(response, "audio", None)
    if audio_obj is not None:
        data = getattr(audio_obj, "data", None)
        mime = getattr(audio_obj, "mime_type", None)
        if data:
            return data, mime

    # Otherwise inline_data in parts
    for part in _iter_parts(response):
        inline = getattr(part, "inline_data", None)
        if not inline:
            continue
        mime_type = getattr(inline, "mime_type", None)
        data = getattr(inline, "data", None)
        if mime_type and isinstance(mime_type, str) and mime_type.startswith("audio") and data:
            return data, mime_type

    return None, None


@dataclass(frozen=True)
class PcmFormat:
    sample_rate_hz: int
    channels: int = 1
    sample_width_bytes: int = 2  # PCM16


def _parse_pcm_format_from_mime(mime_type: str | None, *, default_rate: int = 24000) -> PcmFormat:
    # Example: audio/L16;codec=pcm;rate=24000
    if not mime_type:
        return PcmFormat(sample_rate_hz=default_rate)

    m = re.search(r"rate=(\d+)", mime_type)
    if m:
        return PcmFormat(sample_rate_hz=int(m.group(1)))

    return PcmFormat(sample_rate_hz=default_rate)


def _write_wav_pcm16(path: str, pcm16: bytes, fmt: PcmFormat) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(fmt.channels)
        wf.setsampwidth(fmt.sample_width_bytes)
        wf.setframerate(fmt.sample_rate_hz)
        wf.writeframes(pcm16)


def _transcribe_wav(client: genai.Client, *, model: str, wav_path: str) -> str:
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    # Provide the audio as inline data + a transcription instruction.
    # (This is purely for verification and doesn't need to be perfect.)
    resp = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(inline_data=types.Blob(mime_type="audio/wav", data=wav_bytes)),
                    types.Part(text="Transcribe this audio exactly. Output plain text only."),
                ],
            )
        ],
        config=types.GenerateContentConfig(temperature=0),
    )

    return _extract_text(resp)


def main() -> None:
    p = argparse.ArgumentParser(description="Gemini 3 text -> Gemini 2.5 TTS (GenerateContent) -> WAV")

    p.add_argument("-p", "--prompt", required=True, help="Prompt for Gemini 3 to generate the text that will be spoken")
    p.add_argument("-o", "--output", default=DEFAULT_OUT, help="Output WAV path")

    p.add_argument("--text-model", default=DEFAULT_TEXT_MODEL, help=f"Model for text generation (default: {DEFAULT_TEXT_MODEL})")
    p.add_argument("--tts-model", default=DEFAULT_TTS_MODEL, help=f"Model for TTS (default: {DEFAULT_TTS_MODEL})")
    p.add_argument("--voice", default=DEFAULT_VOICE, help=f"Prebuilt voice name (default: {DEFAULT_VOICE})")

    p.add_argument(
        "--api-version",
        default=os.environ.get("GEMINI_API_VERSION", "v1beta"),
        help="API version for google-genai client (default: env GEMINI_API_VERSION or v1beta)",
    )

    p.add_argument(
        "--max-chars",
        type=int,
        default=800,
        help="Safety limit: truncate spoken text to this many characters (default: 800). Set 0 to disable.",
    )

    p.add_argument("--verify", action="store_true", help="After writing WAV, transcribe it with a Gemini model and print transcript")
    p.add_argument("--verify-model", default=DEFAULT_VERIFY_MODEL, help=f"Model used to transcribe the WAV (default: {DEFAULT_VERIFY_MODEL})")

    args = p.parse_args()

    api_key = _get_api_key()
    if not api_key:
        raise SystemExit("Error: GEMINI_API_KEY or GOOGLE_API_KEY must be set")

    client = genai.Client(api_key=api_key, http_options={"api_version": args.api_version})

    # Step 1: Generate text with Gemini 3
    print("Step 1/2: generating text...")
    text_resp = client.models.generate_content(
        model=args.text_model,
        contents=args.prompt,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You will produce the exact text that will be spoken by a TTS engine. "
                "Return plain text only. Keep it concise. Avoid markdown, lists, JSON, or code blocks."
            ),
            temperature=0.4,
        ),
    )
    text_to_speak = _extract_text(text_resp).strip()

    if args.max_chars and len(text_to_speak) > args.max_chars:
        text_to_speak = text_to_speak[: args.max_chars].rstrip() + "…"

    print("Text to speak:")
    print(text_to_speak)
    print()

    # Step 2: Synthesize speech with Gemini 2.5 TTS preview
    print("Step 2/2: synthesizing audio...")

    # Empirical behavior: the TTS preview model sometimes errors if given only the transcript
    # (complaining it "tried to generate text"). A small wrapper prompt nudges it into TTS mode.
    # We keep the wrapper *minimal* to reduce the risk of it being spoken.
    tts_input = f"Transcript:\n{text_to_speak}"

    tts_resp = client.models.generate_content(
        model=args.tts_model,
        contents=tts_input,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=args.voice)
                )
            ),
        ),
    )

    audio_bytes, mime_type = _extract_audio_bytes(tts_resp)
    if not audio_bytes:
        raise SystemExit("No audio bytes found in TTS response")

    fmt = _parse_pcm_format_from_mime(mime_type)
    _write_wav_pcm16(args.output, audio_bytes, fmt)

    print(f"Wrote WAV: {args.output}")
    if mime_type:
        print(f"TTS mime_type: {mime_type}")
    print(f"Assumed PCM format: {fmt.sample_rate_hz} Hz, {fmt.channels}ch, 16-bit")

    if args.verify:
        print() 
        print("Verification: transcribing generated WAV...")
        transcript = _transcribe_wav(client, model=args.verify_model, wav_path=args.output)
        print("Transcript:")
        print(transcript)


if __name__ == "__main__":
    main()
