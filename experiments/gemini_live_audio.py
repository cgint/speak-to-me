import asyncio
import os
import wave
from google import genai
from google.genai import types

# Configuration
# Use the API key from environment
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = "gemini-2.0-flash-exp" # Live API supports this model
OUTPUT_FILENAME = "gemini_live_output.wav"

async def live_audio_session() -> None:
    if not API_KEY:
        print("Error: GEMINI_API_KEY not set.")
        return

    client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})

    # Configure the session
    # We want audio output.
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"], # type: ignore # MyPy expects list[Modality] but string "AUDIO" is accepted by SDK
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        )
    )

    print(f"Connecting to Live API with model {MODEL_ID}...")
    
    # Store audio chunks
    audio_chunks: list[bytes] = []
    
    async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
        print("Connected. Sending text prompt...")
        
        # Send a text message to trigger speech
        await session.send(input="Hello!", end_of_turn=False)
        await session.send(input="Please speak the following text i give you so I can save it to a file.", end_of_turn=False)
        await session.send(input="\"I am sure this will work.\"", end_of_turn=True)

        print("Listening for response...")
        
        try:
            async for response in session.receive():
                # Check for audio data in the response
                # The structure depends on the SDK version, but usually it's server_content -> model_turn -> parts -> inline_data
                # Or specific audio chunk types.
                
                # In google-genai SDK 1.x, response might be a LiveServerContent or similar.
                # Let's inspect what we get or handle the standard 'data' field.
                
                # Based on typical Live API responses:
                if response.server_content:
                    if response.server_content.model_turn:
                        parts = response.server_content.model_turn.parts
                        if parts:
                            for part in parts:
                                if part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("audio"):
                                    if part.inline_data.data:
                                        audio_chunks.append(part.inline_data.data)
                                        print(".", end="", flush=True)
                    
                    if response.server_content.turn_complete:
                        print("\nTurn complete.")
                        break
        except Exception as e:
            print(f"\nError during receive: {e}")

    # Save audio
    if audio_chunks:
        print(f"\nSaving {len(audio_chunks)} chunks to {OUTPUT_FILENAME}...")
        
        # Live API typically returns PCM 24kHz Mono 16-bit little endian
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
    asyncio.run(live_audio_session())
