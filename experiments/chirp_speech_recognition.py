import os
from google.cloud import speech_v2
from google.api_core.client_options import ClientOptions

def transcribe_audio_chirp(audio_file_path: str, project_id: str, location: str = "europe-west1") -> None:
    """
    Transcribes audio using the Google Cloud Speech-to-Text V2 'Chirp' model.
    """
    # Initialize the client with the specific regional endpoint if necessary
    # For V2, utilizing the regional endpoint is often required.
    client_options = ClientOptions(api_endpoint=f"{location}-speech.googleapis.com")
    client = speech_v2.SpeechClient(client_options=client_options)

    # The content of the audio file to transcribe
    try:
        with open(audio_file_path, "rb") as f:
            audio_content = f.read()
    except FileNotFoundError:
        print(f"Error: Audio file not found at {audio_file_path}")
        return

    # Build the recognition config for Chirp
    config = speech_v2.RecognitionConfig(
        auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
        language_codes=["en-US"],
        model="chirp", # Or "chirp_2"
        features=speech_v2.RecognitionFeatures(
            enable_word_time_offsets=True,
        ),
    )

    parent = f"projects/{project_id}/locations/{location}"
    print(f"Using parent: {parent}")

    request = speech_v2.RecognizeRequest(
        recognizer=f"{parent}/recognizers/_", # Wildcard recognizer
        config=config,
        content=audio_content,
    )

    try:
        print("Sending request to Speech-to-Text V2 API (Chirp)...")
        response = client.recognize(request=request)
        
        for result in response.results:
            print("-" * 20)
            print(f"Transcript: {result.alternatives[0].transcript}")
            print(f"Confidence: {result.alternatives[0].confidence}")

    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        # Print clearer auth message if that's the issue
        if "DefaultCredentialsError" in str(e):
            print("Check your GOOGLE_APPLICATION_CREDENTIALS.")

if __name__ == "__main__":
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("VERTEXAI_PROJECT")
    
    if not project_id:
        print("Error: GOOGLE_CLOUD_PROJECT or VERTEXAI_PROJECT not set.")
    else:
        audio_path = "experiments/test_audio.wav" 
        if not os.path.exists(audio_path):
            with open(audio_path, "wb") as f:
                f.write(b"RIFF....WAVEfmt ....data....")
        
        transcribe_audio_chirp(audio_path, project_id)