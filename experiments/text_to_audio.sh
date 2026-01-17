#!/bin/bash

# Simple example to convert text to audio using Gemini API via curl
# Usage: ./text_to_audio.sh "Text to speak" output.wav

if [ -z "$GEMINI_API_KEY" ]; then
  echo "Error: GEMINI_API_KEY environment variable is not set."
  exit 1
fi

TEXT="${1:-Hello, this is a test of the Gemini Audio generation.}"
OUTPUT_FILE="${2:-output.wav}"

echo "Generating audio for: '$TEXT'"

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-native-audio-latest:generateContent?key=${GEMINI_API_KEY}" \
    -H 'Content-Type: application/json' \
    -d '{
      "contents": [{"parts":[{"text": "'$TEXT'"}]}],
      "generationConfig": {
        "responseMimeType": "audio/wav"
      }
    }' > response.json

# Extract the base64 audio data and decode it
# Note: The API returns the audio data as a base64 encoded string in the JSON response.
# We need to extract it (using grep/sed or jq if available) and decode it.

if command -v jq &> /dev/null; then
    cat response.json | jq -r '.candidates[0].content.parts[0].inlineData.data' | base64 -d > "$OUTPUT_FILE"
else
    # Fallback for systems without jq (less robust)
    grep -o '"data": "[^"max"' response.json | cut -d'"' -f4 | base64 -d > "$OUTPUT_FILE"
fi

echo "Audio saved to $OUTPUT_FILE"
# rm response.json
