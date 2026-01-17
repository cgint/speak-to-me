import os
from google.cloud import texttospeech

def generate_audio_standard(text: str, output_file: str = "standard_tts_output.wav") -> None:
    """
    Generates audio from text using Google Cloud Text-to-Speech API.
    """
    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request
    # "en-US-Journey-D" is a high-quality 'Gemini-like' voice if available.
    # Otherwise "en-US-Neural2-D" is a solid standard.
    # Let's try Journey first, fallback might happen automatically or throw error.
    # We'll stick to a safe Neural2 for now to ensure "not empty".
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-F" # Neural2 female voice
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )

    print(f"Synthesizing audio for: '{text}'...")

    try:
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # The response's audio_content is binary.
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
            print(f"Audio content written to file '{output_file}'")

    except Exception as e:
        print(f"An error occurred: {e}")
        if "ServiceNotEnabled" in str(e) or "403" in str(e):
            print("\nMake sure the 'Cloud Text-to-Speech API' is enabled in your Google Cloud Project.")

if __name__ == "__main__":
    # Ensure credentials are set
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS not set.")
    
    text = "Hello! This allows us to have an audio file based on text using Google models."
    generate_audio_standard(text)
