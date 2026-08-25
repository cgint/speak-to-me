import asyncio
import os
import wave
import argparse
import sys
from pathlib import Path
from typing import Sequence

from google import genai
from google.genai import types

from experiments.gemini_3_text_then_25_tts import (
    DEFAULT_TTS_MODEL,
    _client_for_api_version,
    synthesize_tts_to_wav,
)

# Configuration
# Use the API key from environment
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = "gemini-3.1-flash-live-preview" # Live API audio-capable replacement model
OUTPUT_FILENAME = "gemini_live_output.wav"
DEFAULT_VOICE = "Puck"
# Google Gemini TTS Voice options, verified 2026-08-22:
# https://ai.google.dev/gemini-api/docs/speech-generation#voice-options
VOICE_CATALOG: tuple[tuple[str, str], ...] = (
    ("Zephyr", "Bright"),
    ("Puck", "Upbeat"),
    ("Charon", "Informative"),
    ("Kore", "Firm"),
    ("Fenrir", "Excitable"),
    ("Leda", "Youthful"),
    ("Orus", "Firm"),
    ("Aoede", "Breezy"),
    ("Callirrhoe", "Easy-going"),
    ("Autonoe", "Bright"),
    ("Enceladus", "Breathy"),
    ("Iapetus", "Clear"),
    ("Umbriel", "Easy-going"),
    ("Algieba", "Smooth"),
    ("Despina", "Smooth"),
    ("Erinome", "Clear"),
    ("Algenib", "Gravelly"),
    ("Rasalgethi", "Informative"),
    ("Laomedeia", "Upbeat"),
    ("Achernar", "Soft"),
    ("Alnilam", "Firm"),
    ("Schedar", "Even"),
    ("Gacrux", "Mature"),
    ("Pulcherrima", "Forward"),
    ("Achird", "Friendly"),
    ("Zubenelgenubi", "Casual"),
    ("Vindemiatrix", "Gentle"),
    ("Sadachbia", "Lively"),
    ("Sadaltager", "Knowledgeable"),
    ("Sulafat", "Warm"),
)

async def play_audio_queue(queue: "asyncio.Queue[bytes | None]") -> None:
    """
    Consumes audio chunks from the queue and plays them using sounddevice.
    Run this as a background task.
    """
    try:
        import sounddevice as sd # type: ignore
        import numpy as np
    except ImportError:
        print("Error: sounddevice and numpy are required for audio playback.")
        print("Please install them with: pip install sounddevice numpy")
        return

    # Gemini Native Audio is typically 24kHz, 1 channel, 16-bit PCM
    try:
        with sd.OutputStream(samplerate=24000, channels=1, dtype='int16') as stream:
            while True:
                data = await queue.get()
                if data is None: # Sentinel value to stop
                    queue.task_done()
                    break
                
                # Convert raw bytes to numpy array
                array = np.frombuffer(data, dtype=np.int16)
                
                # stream.write is blocking, so run it in a thread to avoid blocking the event loop
                await asyncio.to_thread(stream.write, array)
                
                queue.task_done()
    except Exception as e:
        print(f"\nError in audio playback: {e}")

async def live_audio_session(play_audio: bool = False, save_audio: bool = True, model_id: str = MODEL_ID, voice_name: str = DEFAULT_VOICE, text_to_speak_as_is: str = "I am pretty sure this will work.") -> None:
    if not API_KEY:
        print("Error: GEMINI_API_KEY not set.")
        return

    client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})

    # Configure the session
    config = types.LiveConnectConfig(
        system_instruction="You are a specialized Text-to-Speech (TTS) engine. Your ONLY job is to speak the text the user provides exactly as written. Do not reply to the text. Do not greet the user. Do not answer questions. Just read the text out loud.",
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        )
    )

    print(f"Connecting to Live API with model {model_id} using voice '{voice_name}'...")
    
    # Store audio chunks for saving
    audio_chunks: list[bytes] = []
    
    # Setup playback queue if requested
    playback_queue: "asyncio.Queue[bytes | None] | None" = None
    playback_task: "asyncio.Task[None] | None" = None
    
    if play_audio:
        playback_queue = asyncio.Queue()
        playback_task = asyncio.create_task(play_audio_queue(playback_queue))
        print("Audio playback enabled (streaming).")
    
    if not save_audio:
        print("Audio saving disabled.")

    async with client.aio.live.connect(model=model_id, config=config) as session:
        print("Connected. Sending text prompt...")
        
        # Send a text message to trigger speech
        await session.send_realtime_input(text=text_to_speak_as_is)

        print(f"Listening for response to: '{text_to_speak_as_is}'")
        
        try:
            async for response in session.receive():
                if response.server_content:
                    if response.server_content.model_turn:
                        parts = response.server_content.model_turn.parts
                        if parts:
                            for part in parts:
                                if part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("audio"):
                                    if part.inline_data.data:
                                        chunk = part.inline_data.data
                                        if save_audio:
                                            audio_chunks.append(chunk)
                                        
                                        # Stream to player
                                        if playback_queue:
                                            playback_queue.put_nowait(chunk)
                                            
                                        print(".", end="", flush=True)
                    
                    if response.server_content.turn_complete:
                        print("\nTurn complete.")
                        break
        except Exception as e:
            print(f"\nError during receive: {e}")

    # Signal playback to finish
    if playback_queue and playback_task:
        print("\nWaiting for audio playback to finish...")
        await playback_queue.put(None)
        await playback_task

    # Save audio
    if save_audio and audio_chunks:
        print(f"\nSaving {len(audio_chunks)} chunks to {OUTPUT_FILENAME}...")
        
        with wave.open(OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            for chunk in audio_chunks:
                wf.writeframes(chunk)
        print("Done.")
    elif not save_audio:
        print("\nDone (Not saved).")
    else:
        print("\nNo audio received.")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Text-to-speech using Gemini Live API. Speaks the given text or file contents aloud.",
        epilog="Examples:\n  speak -s -t 'Hello world'     # Speak text, play only (no file saved)\n  speak -s -f notes.txt       # Speak file contents\n  speak -v Charon -t 'Hi'    # Use voice 'Charon'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--interactive", action="store_true", help="Play audio in real-time while generating (streaming playback)")
    parser.add_argument("-s", "--speak-only", action="store_true", help="Play audio only; do not save to a file")
    parser.add_argument("-o", "--old", action="store_true", help="Use older model gemini-2.0-flash-exp instead of default")
    parser.add_argument(
        "-v",
        "--voice",
        type=str,
        default=DEFAULT_VOICE,
        help=f"Voice: {', '.join(name for name, _ in VOICE_CATALOG)}",
    )
    parser.add_argument("-t", "--text", type=str, default="I am pretty sure this will work.", help="Text to speak (ignored if -f is used)")
    parser.add_argument("-f", "--file", type=str, help="Read text from this file and speak its contents")
    args = parser.parse_args()

    selected_model = "gemini-2.0-flash-exp" if args.old else MODEL_ID

    text_to_speak_as_is = args.text
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as handle:
                text_to_speak_as_is = handle.read()
        except Exception as exc:
            print(f"Error: failed to read file '{args.file}': {exc}")
            raise SystemExit(1)

    # Logic:
    # -s implies interactive playback ON, saving OFF.
    # -i implies interactive playback ON, saving ON (default).
    # Default is interactive playback OFF, saving ON.

    play = args.interactive or args.speak_only
    save = not args.speak_only

    asyncio.run(
        live_audio_session(
            play_audio=play,
            save_audio=save,
            model_id=selected_model,
            voice_name=args.voice,
            text_to_speak_as_is=text_to_speak_as_is,
        )
    )


def _speak_only_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Speak text or a text file using Gemini, with optional WAV output.",
        epilog=(
            "Use --list-voices to print the documented Gemini prebuilt voice catalogue.\n"
            "Source: https://ai.google.dev/gemini-api/docs/speech-generation#voice-options"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="*", help="Text to speak, or one existing text-file path")
    parser.add_argument("-v", "--voice", default=DEFAULT_VOICE, help=f"Voice name (default: {DEFAULT_VOICE})")
    parser.add_argument("--wav", metavar="OUT.wav", help="Write a WAV file instead of Live playback")
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Print the documented Gemini prebuilt voice catalogue as a table",
    )
    return parser


def _format_voice_catalog() -> str:
    voice_width = max(len("Voice"), *(len(name) for name, _ in VOICE_CATALOG))
    characteristic_width = max(len("Characteristic"), *(len(value) for _, value in VOICE_CATALOG))
    header = f"{'Voice':<{voice_width}}  {'Characteristic':<{characteristic_width}}"
    separator = f"{'-' * voice_width}  {'-' * characteristic_width}"
    rows = [
        f"{name:<{voice_width}}  {characteristic:<{characteristic_width}}"
        for name, characteristic in VOICE_CATALOG
    ]
    return "\n".join([header, separator, *rows])


def _resolve_speaks_input(parts: Sequence[str], parser: argparse.ArgumentParser) -> str:
    if len(parts) == 1:
        candidate = Path(parts[0])
        # Guard: only attempt stat() if the string is plausibly a file path.
        # A long text string (>255 chars or containing newlines) is not a path,
        # so skip stat() entirely and fall through to the text-join path.
        if len(parts[0]) <= 255 and "\n" not in parts[0]:
            try:
                if candidate.is_file():
                    return candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                parser.error(f"failed to read file '{candidate}': {exc}")
    return " ".join(parts)


def speak_only_main(argv: Sequence[str] | None = None) -> None:
    """Entry point for `speaks`: Live playback by default, or direct WAV output."""
    parser = _speak_only_parser()
    args = parser.parse_args(argv)

    if args.list_voices:
        if args.input or args.wav:
            parser.error("--list-voices cannot be combined with input or --wav")
        print(_format_voice_catalog())
        return

    if not args.input:
        parser.error("provide text or a file path")

    text = _resolve_speaks_input(args.input, parser)
    if args.wav:
        api_version = os.environ.get("GEMINI_API_VERSION", "v1beta")
        synthesize_tts_to_wav(
            client=_client_for_api_version(api_version),
            tts_model=DEFAULT_TTS_MODEL,
            voice=args.voice,
            text_to_speak=text,
            output_wav=args.wav,
        )
        return

    asyncio.run(
        live_audio_session(
            play_audio=True,
            save_audio=False,
            voice_name=args.voice,
            text_to_speak_as_is=text,
        )
    )


def speak_file_main() -> None:
    sys.argv = [sys.argv[0], "-s", "-f", *sys.argv[1:]]
    main()


def speak_file_speak_me() -> None:
    sys.argv = [sys.argv[0], "-s", "-f", "speak_me.txt", *sys.argv[1:]]
    main()


if __name__ == "__main__":
    main()