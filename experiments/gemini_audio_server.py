import os
from google import genai
from google.genai import types

def generate_audio(text: str, output_file: str = "gemini_native_output_aistudio.wav") -> None:
    """
    Generates audio from text using Gemini API (AI Studio) with a specific model.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return

    print("Initializing AI Studio Client (Non-Vertex)...")
    client = genai.Client(api_key=api_key)

    # The specific model from the snippet
    model_name = "gemini-2.5-flash-native-audio-preview-12-2025"

    print(f"Generating audio for: '{text}' using model {model_name}...")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                response_mime_type="audio/wav",
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck"))
                )
            )
        )
        
        # Check for audio data
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                audio_data = part.inline_data.data
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                print(f"Audio saved to {output_file}")
            else:
                 print("No inline data found in response part.")
        else:
            print("No content returned in response.")

    except Exception as e:
        print(f"An error occurred: {e}")
        if hasattr(e, 'message'):
             print(f"Error message: {e.message}")

if __name__ == "__main__":
    text_input = "Hello! This is a test of the specific 12-2025 preview model."
    generate_audio(text_input, "gemini_native_output.wav")