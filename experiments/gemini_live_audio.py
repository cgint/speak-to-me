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

async def play_audio_queue(queue: asyncio.Queue) -> None:
    """
    Consumes audio chunks from the queue and plays them using sounddevice.
    Run this as a background task.
    """
    try:
        import sounddevice as sd
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

async def live_audio_session(play_audio: bool = False) -> None:
    if not API_KEY:
        print("Error: GEMINI_API_KEY not set.")
        return

    client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})

    # Configure the session
    config = types.LiveConnectConfig(
        system_instruction="Read the user's text out loud exactly as is in natural speech. No greetings. No intro.",
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        )
    )

    print(f"Connecting to Live API with model {MODEL_ID}...")
    
    # Store audio chunks for saving
    audio_chunks: list[bytes] = []
    
    # Setup playback queue if requested
    playback_queue: asyncio.Queue | None = None
    playback_task: asyncio.Task | None = None
    
    if play_audio:
        playback_queue = asyncio.Queue()
        playback_task = asyncio.create_task(play_audio_queue(playback_queue))
        print("Audio playback enabled (streaming).")

    async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
        print("Connected. Sending text prompt...")
        
        # Send a text message to trigger speech
        await session.send_realtime_input(text="I am pretty sure this will work.")

        print("Listening for response...")
        
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
    if audio_chunks:
        print(f"\nSaving {len(audio_chunks)} chunks to {OUTPUT_FILENAME}...")
        
        with wave.open(OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            for chunk in audio_chunks:
                wf.writeframes(chunk)
        print("Done.")
    else:
        print("\nNo audio received.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini Live Audio Experiment")
    parser.add_argument("-i", "--interactive", action="store_true", help="Play audio stream in real-time")
    args = parser.parse_args()
    
    asyncio.run(live_audio_session(play_audio=args.interactive))