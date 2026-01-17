import os
from google import genai
from google.genai import types

def generate_audio_native(text: str, output_file: str = "gemini_native_output.wav") -> None:
    """
    Generates audio from text using Gemini API native audio modality.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return

    client = genai.Client(api_key=api_key)

    # Try specific model names found in search
    model_name = "gemini-2.5-flash-preview-tts"

    print(f"Generating audio for: '{text}' using model {model_name} with response_modalities=['AUDIO']...")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck"))
                )
            )
        )
        
        # In the new SDK, response.audio might be available directly as per search result
        audio_data: bytes | None = None
        if hasattr(response, 'audio') and response.audio and response.audio.data:
             print("Audio data found in response.audio")
             audio_data = response.audio.data
        elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            # Fallback to checking parts
            part = response.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                print("Audio data found in inline_data")
                audio_data = part.inline_data.data
            else:
                print("No inline data found.")
                return
        else:
            print("No content returned.")
            return

        if audio_data:
            # Save
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"Audio saved to {output_file}")
        else:
            print("Failed to retrieve audio data.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Print full error details if possible
        if hasattr(e, 'message'):
            print(f"Error message: {e.message}")



if __name__ == "__main__":
    text_input = "Hello! This is a test of the native Gemini audio modality parameter."
    generate_audio_native(text_input)
