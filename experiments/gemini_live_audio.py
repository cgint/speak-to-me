import asyncio
import os
import wave
import argparse
import sys
from google import genai
from google.genai import types

# Configuration
# Use the API key from environment
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025" # Live API supports this model
OUTPUT_FILENAME = "gemini_live_output.wav"

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

async def live_audio_session(play_audio: bool = False, save_audio: bool = True, model_id: str = MODEL_ID, voice_name: str = "Puck", text_to_speak_as_is: str = "I am pretty sure this will work.") -> None:
    if not API_KEY:
        print("Error: GEMINI_API_KEY not set.")
        return

    client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})

    # Configure the session
    config = types.LiveConnectConfig(
        system_instruction="Read the user's text out loud exactly as is in natural speech. No greetings. No intro.",
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
    parser = argparse.ArgumentParser(description="Gemini Live Audio Experiment")
    parser.add_argument("-i", "--interactive", action="store_true", help="Play audio stream in real-time")
    parser.add_argument("-s", "--speak-only", action="store_true", help="Speak exclusively without saving to file")
    parser.add_argument("-o", "--old", action="store_true", help="Use old model (gemini-2.0-flash-exp)")
    parser.add_argument("-v", "--voice", type=str, default="Puck", help="Voice name (e.g., Puck, Charon, Fenrir, Kore, Aoede, Leda, Orus, Zephyr)")
    parser.add_argument("-t", "--text", type=str, default="I am pretty sure this will work.", help="Text to speak")
    parser.add_argument("-f", "--file", type=str, help="Path to a text file whose contents will be spoken")
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


def speak_only_main() -> None:
    sys.argv = [sys.argv[0], "-s", "-t", *sys.argv[1:]]
    main()


def speak_file_main() -> None:
    sys.argv = [sys.argv[0], "-s", "-f", *sys.argv[1:]]
    main()


def speak_file_speak_me() -> None:
    sys.argv = [sys.argv[0], "-s", "-f", "speak_me.txt", *sys.argv[1:]]
    main()


if __name__ == "__main__":
    main()