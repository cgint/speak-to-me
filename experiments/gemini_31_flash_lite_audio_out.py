"""Gemini 3.1 Flash Lite: Text -> Audio output (separate experiment).

This script is intentionally standalone from the other experiments.
It probes whether the model `gemini-3.1-flash-lite-preview` supports:
- text input
- audio output via `response_modalities=["AUDIO"]`

Depending on model/endpoint availability, this may return an error (e.g.
unsupported modality) or may return audio bytes (inline_data or response.audio).

Usage examples:
  uv run experiments/gemini_31_flash_lite_audio_out.py -t "Hello" -o out.wav
  uv run experiments/gemini_31_flash_lite_audio_out.py -f speak_me.txt

Notes:
- Requires GEMINI_API_KEY.
- If the returned mime type is not `audio/wav`, the output file may not be a WAV.
"""

from __future__ import annotations

import argparse
import os
from typing import Iterable

from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
DEFAULT_OUTPUT = "gemini_31_flash_lite_output.wav"


def _iter_parts(response: object) -> Iterable[types.Part]:
    """Best-effort iteration over parts across candidates."""
    if not hasattr(response, "candidates"):
        return []

    parts: list[types.Part] = []
    # google-genai response types are dynamic-ish; keep this defensive.
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            parts.append(part)
    return parts


def _extract_audio_bytes(response: object) -> tuple[bytes | None, str | None]:
    """Extract (audio_bytes, mime_type) from a generate_content response."""

    # Some SDK responses may surface a top-level `response.audio.data`.
    audio_obj = getattr(response, "audio", None)
    if audio_obj is not None:
        data = getattr(audio_obj, "data", None)
        mime = getattr(audio_obj, "mime_type", None)
        if data:
            return data, mime

    # Otherwise, scan parts for inline_data with audio/* mime.
    for part in _iter_parts(response):
        inline = getattr(part, "inline_data", None)
        if not inline:
            continue
        mime_type = getattr(inline, "mime_type", None)
        data = getattr(inline, "data", None)
        if mime_type and isinstance(mime_type, str) and mime_type.startswith("audio") and data:
            return data, mime_type

    return None, None


def generate_audio(
    *,
    text: str,
    output_file: str,
    model: str,
    voice: str,
    api_version: str,
    method: str,
) -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Error: GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key, http_options={"api_version": api_version})

    # We keep this configurable because different endpoints have historically had
    # different feature gating.
    cfg_kwargs: dict[str, object] = {
        "speech_config": types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        )
    }

    # method:
    # - modalities: response_modalities=["AUDIO"]
    # - mime:       response_mime_type="audio/wav"
    # - both:       try both together (may be rejected)
    if method in ("modalities", "both"):
        cfg_kwargs["response_modalities"] = ["AUDIO"]
    if method in ("mime", "both"):
        cfg_kwargs["response_mime_type"] = "audio/wav"

    print(
        "Requesting audio from Gemini...\n"
        f"  model: {model}\n"
        f"  api_version: {api_version}\n"
        f"  method: {method}\n"
        f"  voice: {voice}\n"
        f"  output: {output_file}\n"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(**cfg_kwargs),
        )
    except Exception as e:
        # This is the most common outcome when the model doesn't support audio output.
        print("ERROR: generate_content failed.")
        print(str(e))
        raise

    audio_bytes, mime_type = _extract_audio_bytes(response)
    if not audio_bytes:
        print("No audio bytes found in response.")
        # Helpful breadcrumbs for debugging without dumping huge objects.
        if hasattr(response, "candidates"):
            print(f"Response had {len(getattr(response, 'candidates') or [])} candidate(s).")
        raise SystemExit(2)

    with open(output_file, "wb") as f:
        f.write(audio_bytes)

    if mime_type:
        print(f"Saved audio to {output_file} (mime_type={mime_type}).")
    else:
        print(f"Saved audio to {output_file} (mime_type unknown).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Text to audio using gemini-3.1-flash-lite-preview (audio output modality probe)."
    )

    src = parser.add_mutually_exclusive_group(required=False)
    src.add_argument("-t", "--text", type=str, help="Text to speak")
    src.add_argument("-f", "--file", type=str, help="Read text from file")

    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT, help="Output file")
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, help="Gemini model id")
    parser.add_argument(
        "-v",
        "--voice",
        type=str,
        default="Puck",
        help="Prebuilt voice name (e.g. Puck, Charon, Fenrir, Kore, Aoede, Leda, Orus, Zephyr)",
    )
    parser.add_argument(
        "--api-version",
        type=str,
        default=os.environ.get("GEMINI_API_VERSION", "v1beta"),
        help="API version for google-genai client (default: env GEMINI_API_VERSION or v1beta)",
    )
    parser.add_argument(
        "--method",
        choices=["modalities", "mime", "both"],
        default="modalities",
        help="How to request audio output.",
    )

    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as handle:
                text = handle.read()
        except Exception as exc:
            raise SystemExit(f"Error: failed to read file '{args.file}': {exc}")
    elif args.text:
        text = args.text
    else:
        text = "Hello. This is a Gemini 3.1 Flash Lite audio output test."

    generate_audio(
        text=text,
        output_file=args.output,
        model=args.model,
        voice=args.voice,
        api_version=args.api_version,
        method=args.method,
    )


if __name__ == "__main__":
    main()
